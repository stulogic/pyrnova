"""HTTP host for the Pyrnova customer-facing product and the internal Operator Console (M22-F).

Access model (see ``docs/specs/M22F_MINIMAL_ACCESS_ONBOARDING.md`` and :mod:`pyrnova.access`):

* **Authentication.** A request presents ``Authorization: Bearer <credential>``; :func:`access.authenticate`
  turns it into an :class:`~pyrnova.access.AuthContext` (the authenticated actor + its authorized tenant).
  The customer NEVER comes from a request parameter or a frontend dropdown when an authenticated actor can
  determine it — a forged ``?customer=`` cannot widen scope (a mismatch is a hard 403, §14).
* **Fail-closed posture.** ``require_auth`` is forced ON whenever the server is bound non-locally (§16) or
  ``PYRNOVA_REQUIRE_AUTH`` is set or any credential has been provisioned. Only a purely local dev checkout
  with no credentials runs permissively (the historical behavior) — an explicit, safe-by-default dev
  posture that can never activate silently for remote access (§30).
* **Operator separation.** The internal Operator Console (all-customer listing, snapshot, fan-out, briefs,
  opportunity adjudication, and the ``/console`` assets) is exposed ONLY on a local bind (§11/§16). Bound
  remotely, those surfaces return 404 and, if reached, require an operator-role credential — a customer
  can never see another tenant or an unrestricted operator surface.
* **Defense in depth.** When auth is enforced, the shared console's ``access_check`` is bound to the
  per-request actor (:func:`access.request_access_check`), so even a route that forgot to scope a read
  fails closed rather than leaking across tenants.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import access
from .config import load_config
from .ops import OperatorConsole
from .state import StateStore

WEB_ROOT = Path(__file__).with_name("ops_web")
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

# Route access levels.
LEVEL_PUBLIC = "public"        # customer app shell + login assets; served without a credential
LEVEL_CUSTOMER = "customer"    # tenant-scoped data; effective customer derived from the actor
LEVEL_GLOBAL = "global"        # global intelligence; any authenticated actor (not anonymous when enforced)
LEVEL_OPERATOR = "operator"    # internal operator surface; operator-role credential + local bind only


class Unauthorized(Exception):
    """No valid authentication was presented (→ 401)."""


class Forbidden(Exception):
    """Authenticated, but not authorized for the requested customer/resource (→ 403)."""


class NotExposed(Exception):
    """The requested surface is not exposed on this binding (→ 404), e.g. operator routes bound remotely."""


class AccessPolicy:
    """The server's static access posture, decided once at startup from host + env + credential state."""

    def __init__(self, *, host: str, require_auth: bool, expose_operator: bool):
        self.host = host
        self.require_auth = require_auth
        self.expose_operator = expose_operator

    @classmethod
    def decide(cls, host: str, store: StateStore, *, force_require_auth: bool = False) -> "AccessPolicy":
        is_local = host in _LOCAL_HOSTS
        env_flag = os.environ.get("PYRNOVA_REQUIRE_AUTH", "").strip().lower() in {"1", "true", "yes", "on"}
        # Interlock: a non-local bind ALWAYS enforces auth; it can never be turned off remotely (§16/§30).
        require_auth = (not is_local) or force_require_auth or env_flag or access.has_credentials(store)
        return cls(host=host, require_auth=require_auth, expose_operator=is_local)


def _seed_demo_customers(demo_dir: Path, store: StateStore) -> None:
    """Seed demo customers into persisted state via the example seeder (loaded by file path).

    The demo identities live in ``examples/`` — never hard-coded into the ``pyrnova`` runtime package —
    so this loads the example module by path only at startup wiring time (M22-B doctrine, D-056)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pyrnova_demo_seed_customers", demo_dir / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)


def make_handler(console: OperatorConsole, policy: AccessPolicy | None = None,
                 auth_store: StateStore | None = None):
    # Default to the permissive local-dev posture (no auth, operator surface exposed) so a handler can be
    # constructed for local development and tests without provisioning credentials. A remote/enforced
    # deployment always passes an explicit policy + auth store from main().
    if policy is None:
        policy = AccessPolicy(host="127.0.0.1", require_auth=False, expose_operator=True)
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ValueError("request too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def _download(self, filename: str, text: str):
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _asset(self, name: str, content_type: str):
            path = WEB_ROOT / name
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        # --- authentication + authorization -----------------------------------------------------

        def _bearer(self) -> str:
            header = self.headers.get("Authorization", "")
            if header.startswith("Bearer "):
                return header[len("Bearer "):].strip()
            return ""

        def _context(self):
            if auth_store is None:
                return None
            return access.authenticate(auth_store, self._bearer())

        def _require(self, level: str, requested_customer: str | None = None) -> str | None:
            """Enforce access for a route; return the EFFECTIVE customer id (or None for non-customer routes).

            Raises Unauthorized/Forbidden/NotExposed which the request wrapper maps to 401/403/404.
            """
            ctx = access.current_context()
            if level == LEVEL_OPERATOR and not policy.expose_operator:
                raise NotExposed("operator surface is not exposed on this binding")
            if not policy.require_auth:
                # Local dev, no credentials provisioned: permissive (historical behavior). The effective
                # customer is whatever the request asked for (the localhost operator's own choice).
                return requested_customer
            if ctx is None:
                raise Unauthorized("authentication required")
            if level == LEVEL_OPERATOR:
                if not ctx.is_operator:
                    raise Forbidden("access denied")
                return requested_customer
            if level == LEVEL_CUSTOMER:
                if ctx.is_operator:
                    if not requested_customer:
                        raise Forbidden("a customer must be specified")
                    return requested_customer
                if requested_customer and requested_customer != ctx.customer_id:
                    raise Forbidden("access denied")
                return ctx.customer_id
            # LEVEL_GLOBAL: any authenticated actor.
            return requested_customer

        def _me(self):
            """``/api/me``: the current actor's identity + the tenant posture the frontend renders from."""
            ctx = access.current_context()
            out: dict = {"require_auth": policy.require_auth, "authenticated": ctx is not None,
                         "actor": None, "customer": None, "customers": None}
            if ctx is not None:
                out["actor"] = {"role": ctx.role, "actor_label": ctx.actor_label}
                if ctx.is_operator:
                    out["customers"] = console.customers()  # operator may switch (internal)
                else:
                    out["customer"] = console.customer_identity(ctx.customer_id)
            elif not policy.require_auth:
                # Local dev without credentials: expose the list so the dev dropdown keeps working
                # (localhost-only convenience — never reachable in an auth-enforced/remote posture).
                out["customers"] = console.customers()
            return self._json(200, out)

        # --- request dispatch -------------------------------------------------------------------

        def _dispatch(self, handler):
            access.set_request_context(self._context())
            try:
                return handler()
            except Unauthorized as exc:
                return self._json(401, {"error": str(exc)})
            except (Forbidden, PermissionError) as exc:
                # The message echoes only the requester's OWN supplied/authorized customer id (never another
                # tenant's data), so it is safe and keeps the authorization boundary debuggable (§15/§38).
                return self._json(403, {"error": str(exc)})
            except NotExposed:
                return self._json(404, {"error": "not found"})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            finally:
                access.clear_request_context()

        def do_GET(self):
            self._dispatch(self._do_get)

        def do_POST(self):
            self._dispatch(self._do_post)

        def _do_get(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            path = parsed.path

            if path == "/api/me":
                return self._me()

            # --- operator (internal) surfaces ---------------------------------------------------
            if path == "/api/snapshot":
                self._require(LEVEL_OPERATOR)
                return self._json(200, console.snapshot(query.get("target", [None])[0]))

            # --- customer / global data ---------------------------------------------------------
            if path == "/api/customers":
                # §13: never an unrestricted tenant listing for an ordinary customer. Operator (or local
                # dev) sees all; a customer sees only itself.
                ctx = access.current_context()
                if policy.require_auth and ctx is not None and not ctx.is_operator:
                    ident = console.customer_identity(ctx.customer_id)
                    return self._json(200, {"customers": [ident] if ident else []})
                self._require(LEVEL_OPERATOR)
                return self._json(200, {"customers": console.customers()})

            if path.startswith("/api/customers/"):
                parts = path.split("/")  # ['', 'api', 'customers', '<id>', ...]
                cid = unquote(parts[3]) if len(parts) > 3 else ""
                cid = self._require(LEVEL_CUSTOMER, cid)
                as_of = query.get("as_of", [None])[0]
                if len(parts) == 5 and parts[4] == "watchlist":
                    return self._json(200, {"customer_id": cid,
                                            "watchlist": console.list_customer_watches(cid, as_of=as_of)})
                if len(parts) == 4:
                    return self._json(200, console.get_customer_profile(cid, as_of=as_of))
                return self._json(404, {"error": "not found"})

            if path == "/api/search":
                self._require(LEVEL_GLOBAL)
                return self._json(200, console.search(
                    query.get("q", [""])[0], as_of=query.get("as_of", [None])[0]))

            if path == "/api/company":
                ref = query.get("ref", [None])[0]
                if not ref:
                    return self._json(400, {"error": "ref is required"})
                customer = self._customer_overlay(query.get("customer", [None])[0])
                return self._json(200, console.company_intelligence(
                    ref, as_of=query.get("as_of", [None])[0], customer=customer))

            if path == "/api/program":
                key = query.get("key", [None])[0]
                if not key:
                    return self._json(400, {"error": "key is required"})
                customer = self._customer_overlay(query.get("customer", [None])[0])
                return self._json(200, console.program_intelligence(
                    key, as_of=query.get("as_of", [None])[0], customer=customer))

            if path == "/api/material-changes":
                cid = self._require(LEVEL_CUSTOMER, query.get("customer", [None])[0])
                return self._json(200, console.material_changes(
                    cid, as_of=query.get("as_of", [None])[0],
                    disposition=query.get("disposition", [None])[0]))

            if path.startswith("/api/material-changes/") and path.endswith("/review-history"):
                change_id = unquote(path.split("/")[3])
                cid = self._require(LEVEL_CUSTOMER, query.get("customer", [None])[0])
                return self._json(200, console.customer_review_history(
                    cid, change_id, as_of=query.get("as_of", [None])[0]))

            if path.startswith("/api/material-changes/") and path.endswith("/versions"):
                change_id = unquote(path.split("/")[3])
                cid = self._require(LEVEL_CUSTOMER, query.get("customer", [None])[0])
                return self._json(200, console.customer_material_change_versions(cid, change_id))

            # --- B3: customer product surface (Lens / Opportunities / Decision / Evidence / Brief) -----
            as_of = query.get("as_of", [None])[0]
            if path == "/api/lens":  # B3.1
                cid = self._require(LEVEL_CUSTOMER, query.get("customer", [None])[0])
                return self._json(200, console.customer_lens(cid, as_of=as_of))
            if path == "/api/opportunities":  # B3.3
                cid = self._require(LEVEL_CUSTOMER, query.get("customer", [None])[0])
                return self._json(200, console.customer_opportunities(cid, as_of=as_of))
            if path.startswith("/api/opportunities/"):
                parts = path.split("/")  # ['', 'api', 'opportunities', '<id>', ...]
                oid = unquote(parts[3]) if len(parts) > 3 else ""
                cid = self._require(LEVEL_CUSTOMER, query.get("customer", [None])[0])
                if len(parts) == 5 and parts[4] == "decision":  # B3.4
                    return self._json(200, console.opportunity_decision(cid, oid, as_of=as_of))
                if len(parts) == 6 and parts[4] == "evidence":  # B3.6
                    return self._json(200, console.opportunity_evidence(
                        cid, oid, unquote(parts[5]), as_of=as_of))
                if len(parts) == 5 and parts[4] == "brief":  # B3.10 authenticated brief download
                    brief = console.build_customer_brief(cid, oid, as_of=as_of)
                    if query.get("download", ["0"])[0] in ("1", "true", "yes"):
                        return self._download(brief["filename"], brief["body"])
                    return self._json(200, brief)
                if len(parts) == 5 and parts[4] == "deliveries":  # B3.11 delivery audit
                    return self._json(200, console.list_customer_deliveries(cid))
                return self._json(404, {"error": "not found"})

            return self._get_asset(path)

        def _customer_overlay(self, requested: str | None) -> str | None:
            """Resolve the authorized customer overlay for a global investigation page, or None.

            No overlay requested → global page for any authenticated actor. Overlay requested → it must be
            the actor's own tenant (or the operator's chosen customer); a mismatch is a 403 (§12/§35)."""
            if not requested:
                self._require(LEVEL_GLOBAL)
                return None
            return self._require(LEVEL_CUSTOMER, requested)

        def _get_asset(self, path: str):
            # Customer-facing app shell + login assets are PUBLIC (the data behind them is protected).
            customer_assets = {
                # B3.1: the Customer Lens is the customer-facing landing experience.
                "/": ("product.html", "text/html; charset=utf-8"),
                "/product.html": ("product.html", "text/html; charset=utf-8"),
                "/product.js": ("product.js", "text/javascript; charset=utf-8"),
                "/product.css": ("product.css", "text/css; charset=utf-8"),
                "/material.html": ("material.html", "text/html; charset=utf-8"),
                "/material.js": ("material.js", "text/javascript; charset=utf-8"),
                "/material.css": ("material.css", "text/css; charset=utf-8"),
                "/access.js": ("access.js", "text/javascript; charset=utf-8"),
                "/access.css": ("access.css", "text/css; charset=utf-8"),
                "/investigate": ("investigation.html", "text/html; charset=utf-8"),
                "/search": ("investigation.html", "text/html; charset=utf-8"),
                "/company": ("investigation.html", "text/html; charset=utf-8"),
                "/program": ("investigation.html", "text/html; charset=utf-8"),
                "/investigation.html": ("investigation.html", "text/html; charset=utf-8"),
                "/investigation.js": ("investigation.js", "text/javascript; charset=utf-8"),
                "/investigation.css": ("investigation.css", "text/css; charset=utf-8"),
            }
            # Operator console assets — internal surface, local bind only (§11/§16).
            operator_assets = {
                "/console": ("index.html", "text/html; charset=utf-8"),
                "/index.html": ("index.html", "text/html; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            }
            if path in customer_assets:
                name, content_type = customer_assets[path]
                return self._asset(name, content_type)
            if path in operator_assets:
                if not policy.expose_operator:
                    return self._json(404, {"error": "not found"})
                name, content_type = operator_assets[path]
                return self._asset(name, content_type)
            return self._json(404, {"error": "not found"})

        def _do_post(self):
            parsed = urlparse(self.path)
            path = parsed.path
            payload = self._body()

            # --- operator (internal) surfaces ---------------------------------------------------
            if path.startswith("/api/opportunities/") and path.endswith("/review"):
                self._require(LEVEL_OPERATOR)
                opportunity_id = unquote(path.split("/")[3])
                return self._json(200, console.adjudicate(opportunity_id, **payload))
            if path.startswith("/api/opportunities/") and path.endswith("/outcome"):
                self._require(LEVEL_OPERATOR)
                opportunity_id = unquote(path.split("/")[3])
                return self._json(200, console.record_outcome(opportunity_id, **payload))
            if path == "/api/briefs":
                self._require(LEVEL_OPERATOR)
                return self._json(200, console.export_signal_brief(payload.get("target", "")))
            if path == "/api/fanout":
                self._require(LEVEL_OPERATOR)
                return self._json(200, console.fan_out(
                    customer_ids=payload.get("customers"), as_of=payload.get("as_of")))
            if path == "/api/customers":
                self._require(LEVEL_OPERATOR)  # customer creation is operator-assisted onboarding (§18)
                return self._json(200, console.create_customer(**payload))

            # --- customer-scoped surfaces -------------------------------------------------------
            if path.startswith("/api/customers/"):
                parts = path.split("/")  # ['', 'api', 'customers', '<id>', 'watchlist', ...]
                cid = self._require(LEVEL_CUSTOMER, unquote(parts[3]) if len(parts) > 3 else "")
                if len(parts) == 5 and parts[4] == "watchlist":
                    return self._json(200, console.add_customer_watch(cid, **payload))
                if len(parts) == 7 and parts[4] == "watchlist" and parts[6] == "retire":
                    return self._json(200, console.retire_customer_watch(cid, unquote(parts[5])))
                return self._json(404, {"error": "not found"})

            if path.startswith("/api/material-changes/") and path.endswith("/review"):
                change_id = unquote(path.split("/")[3])
                cid = self._require(LEVEL_CUSTOMER, payload.pop("customer", None))
                # The authenticated actor id is the audit actor, never a client-supplied value (§53).
                ctx = access.current_context()
                if ctx is not None:
                    payload["actor"] = ctx.actor_label or ctx.credential_id
                return self._json(200, console.record_customer_review(cid, change_id, **payload))

            # --- B3: customer disposition (Decision Memory) + brief delivery --------------------------
            if path.startswith("/api/opportunities/") and path.endswith("/disposition"):  # B3.8
                oid = unquote(path.split("/")[3])
                cid = self._require(LEVEL_CUSTOMER, payload.pop("customer", None))
                return self._json(200, console.record_opportunity_disposition(cid, oid, **payload))

            if path.startswith("/api/opportunities/") and path.endswith("/deliver"):  # B3.11
                oid = unquote(path.split("/")[3])
                cid = self._require(LEVEL_CUSTOMER, payload.pop("customer", None))
                recipients = payload.get("recipients") or []
                return self._json(200, console.deliver_customer_brief(cid, oid, recipients=recipients))

            # Operator-provisioned recipient authorization for a tenant (onboarding, §18).
            if path.startswith("/api/customers/") and path.endswith("/delivery-recipients"):
                cid = unquote(path.split("/")[3])
                self._require(LEVEL_OPERATOR)
                return self._json(200, console.authorize_delivery_recipient(cid, payload.get("email", "")))

            return self._json(404, {"error": "not found"})

        def log_message(self, format, *args):
            return  # never log request lines (they could carry identifiers); and never log secrets (§30)

    return Handler


def _build_console(cfg, state_store: StateStore, policy: AccessPolicy) -> OperatorConsole:
    demo_dir = Path("examples/material_changes_demo")
    mc_store = state_store
    if not (Path(cfg.state_dir) / "threats.jsonl").exists() and (demo_dir / "state" / "threats.jsonl").exists():
        mc_store = StateStore(demo_dir / "state")
    from . import customers as _cust
    if not _cust.list_customers(state_store) and (demo_dir / "seed_customers.py").exists():
        _seed_demo_customers(demo_dir, state_store)
    # Defense in depth: bind the console's authorization seam to the per-request actor when auth is
    # enforced; leave it permissive (historical) only in local dev with no credentials.
    check = access.request_access_check if policy.require_auth else None
    from .customer_delivery import CustomerDeliveryStore
    delivery_store = CustomerDeliveryStore(Path(cfg.state_dir) / "deliveries")
    return OperatorConsole(
        state_store, Path("examples/profiles"), cfg.out_dir,
        mc_store=mc_store, contexts_dir=demo_dir, customer_store=state_store,
        cmc_store=state_store, access_check=check, delivery_store=delivery_store)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pyrnova product + Operator Console host")
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address; a non-local host enables controlled remote access and FORCES "
                             "authentication + hides the operator console (§16)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--require-auth", action="store_true",
                        help="force authentication on even for a local bind")
    args = parser.parse_args(argv)

    cfg = load_config()
    state_store = StateStore(cfg.state_dir)
    policy = AccessPolicy.decide(args.host, state_store, force_require_auth=args.require_auth)
    console = _build_console(cfg, state_store, policy)
    try:
        report = console.fan_out()
        print(f"Material Change fan-out: {report['inserted']} inserted, {report['updated']} updated, "
              f"{report['duplicates_suppressed']} unchanged across {report['customers']} customer(s)")
    except ValueError:
        pass

    server = ThreadingHTTPServer((args.host, args.port), make_handler(console, policy, state_store))
    posture = "AUTH REQUIRED" if policy.require_auth else "local dev (no auth)"
    op = "operator console exposed" if policy.expose_operator else "operator console hidden (remote bind)"
    print(f"Pyrnova: http://{args.host}:{args.port}  [{posture}; {op}]")
    if policy.require_auth and not access.has_credentials(state_store):
        print("  WARNING: auth is required but no credentials are provisioned — "
              "create one with: pyrnova credential create --customer <id>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
