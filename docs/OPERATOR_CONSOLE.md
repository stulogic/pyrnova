# Pyrnova Operator Console v0.1

The Operator Console is a local, internal analyst layer over Pyrnova's append-only state. It does not
run the engine or alter scoring. It shows persisted candidates by target, derived run activity,
explicitly observed/unobserved source state, evidence links, and the existing system disposition.

Analysts can record ACCEPT/WATCH/REJECT adjudications, assign PRIME/SUPPORT/TEAM/DEFEND posture, retain
notes and falsification, promote an accepted item to STRIKE through the existing review functions,
export a Signal Brief through the existing renderer, and record a small outcome label. All writes are
append-only JSONL under `PYRNOVA_STATE_DIR` (default `var/state`); exports go to `PYRNOVA_OUT_DIR`
(default `out`). Real customer data and output remain gitignored.

## Launch

From the repository root, using the existing environment:

```bash
python -m pyrnova.ops_server
```

Open `http://127.0.0.1:8765`. Run Capture Radar first if the selected target has no persisted
candidates.

## Access (M22-F)

The internal **Operator Console** (`/console`, snapshot, fan-out, briefs, opportunity adjudication,
all-customer listing/creation) is exposed **only on a local bind**; bound to a non-local host it returns
404 and requires an operator-role credential. The customer-facing **Material Changes** product supports
controlled remote access under real authentication:

- **Auth posture.** `AccessPolicy` forces authentication ON whenever the server binds to a non-local host,
  `PYRNOVA_REQUIRE_AUTH` is set, or any credential has been provisioned. A purely local checkout with no
  credentials stays permissive (dev). It can never fall back to permissive for remote access.
- **Credentials.** `pyrnova credential create --customer <id>` prints a bearer token **once** (only a
  salted one-way hash is stored — the secret is never recoverable, never logged, never in a URL).
  `credential list` shows metadata only; `credential revoke <credential_id>` fails auth immediately.
- **Tenant isolation.** A customer credential scopes access to exactly one tenant, server-enforced; a
  forged `?customer=` is a hard 403; a customer cannot enumerate tenants (`/api/customers` returns only
  itself; `/api/me` shows the org). See `docs/specs/M22F_MINIMAL_ACCESS_ONBOARDING.md` (D-061).

This is the smallest serious access model for a controlled design customer, **not** enterprise IAM — SSO,
SAML, SCIM, MFA, RBAC, and production TLS are deferred (D-048); production edge/TLS is assumed in front of
the app. No claim of enterprise-grade / zero-trust / SOC 2 / production-hardened is made.

### Onboarding (seed-free)

```
pyrnova customer create --id <slug> --name "<Org>" [--entity-ref co_x --agency "…"]
pyrnova watch add <customer> <ref> --type ENTITY|PROGRAM|CONTRACT|AGENCY [--resolve]
pyrnova credential create --customer <customer>
pyrnova customer show <customer>
```

`--resolve` uses deterministic M22-D search: EXACT is added; PROBABLE needs `--accept-probable`; AMBIGUOUS
is never silently chosen; UNRESOLVED is never fabricated (`--allow-unresolved --type …` records it
honestly). No seed/Python/JSONL editing is required to onboard a customer.

## Boundaries

- Source health means only “an observation is/is not persisted”; it is not a live availability claim.
- Run status is reconstructed from persisted opportunity `run_id` values, not a job scheduler.
- Outcomes are operator-entered labels and are not verified pipeline ground truth.
- Export includes current persisted STRIKE items; it does not rerun or rescore them.
- Recovered reports may be imported only with explicit origin/freshness labels and unavailable scores;
  they remain pending review rather than being presented as fresh or promoted automatically.
- No portal, billing, CRM, Postgres, graph, mobile, realtime, broad analytics, or agents are included.
