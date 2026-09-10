"""Company / program investigation read model + deterministic entity search (M22-D).

M22-A/B/C answered *what materially changed for this customer*. M22-D answers the next question a
customer asks the moment a Material Change matters: **what is the company or program behind it, what
does Pyrnova know, which relationships and evidence support that view, and what remains unknown?** — and
lets a user reach that page by searching the Pyrnova intelligence estate deterministically.

This is a single read-projection + identity layer. It reuses the EXISTING canonical identity (entity
refs, source-native identifiers, program keys) and the EXISTING intelligence streams; it never creates a
second entity-resolution system, never fabricates identifiers, and never runs a runtime LLM (§6/§9/§10).

Doctrine honored (see ``docs/specs/M22D_INVESTIGATION_SEARCH.md``, D-058, extending D-055/D-056/D-057):

* **Canonical identity reused (§10).** Entities are the canonical refs already in the intelligence graph
  (``co_*`` / ``co_uei_*``); programs are the source-native program/contract keys (PIIDs). Identifiers
  (UEI/CAGE/CIK/LEI/recipient id) are read from structured provenance ONLY — a bare, ambiguous evidence
  token is never used to manufacture identity.
* **Deterministic search (§6/§7/§9).** Exact identifiers resolve by dictionary lookup — never an LLM.
  Name/alias search is deterministic scored matching with EXACT / PROBABLE / AMBIGUOUS / UNRESOLVED
  resolution surfaced honestly; two same-named entities are shown as two, never silently merged.
* **Reversible resolution (§11).** A search query is not evidence of identity: search reads the estate
  and classifies a match; it never writes a merge or mutates canonical identity.
* **Global vs customer boundary (§12).** Company/program pages are GLOBAL intelligence. An optional,
  separately-keyed ``customer_context`` block is added only for an authorized customer and never folds a
  customer's private relevance into global truth.
* **Temporal truth (§19).** The estate and every page section are reconstructed point-in-time: an entity,
  relationship, event, or outcome that was not knowable at ``as_of`` does not appear historically, and
  relationship validity (``valid_from``/``valid_to``) is respected.
* **UNKNOWN is a feature (§17).** Sparse intelligence is stated honestly ("no UEI stored", "ownership
  unresolved") rather than hidden or filled with inference. Evidence is referenced, never copied (§18).

Self-contained: imports only from :mod:`pyrnova.material_changes` (the shared change normalizers, so the
page view and the Material Changes feed never diverge). No imports from scoring/fit/replay/ai.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from .material_changes import _opportunity_change, _threat_change, _visible

# --- entity/program kinds ----------------------------------------------------------------------
KIND_COMPANY = "COMPANY"
KIND_PROGRAM = "PROGRAM"

# --- search resolution states (§11) ------------------------------------------------------------
RESOLUTION_EXACT = "EXACT"            # a single unambiguous match (identifier or exact name)
RESOLUTION_PROBABLE = "PROBABLE"      # scored partial name match(es), best first
RESOLUTION_AMBIGUOUS = "AMBIGUOUS"    # several equally-valid matches — surfaced, never merged
RESOLUTION_UNRESOLVED = "UNRESOLVED"  # nothing matched (a first-class, honest answer)

# --- match bases (customer-inspectable, functional labels — D-041) -----------------------------
MATCH_ENTITY_ID = "PYRNOVA_ENTITY_ID"
MATCH_PROGRAM_ID = "CONTRACT_OR_PROGRAM_ID"
MATCH_UEI = "UEI"
MATCH_CAGE = "CAGE"
MATCH_CIK = "CIK"
MATCH_LEI = "LEI"
MATCH_NAME_EXACT = "NAME_EXACT"
MATCH_ALIAS_EXACT = "ALIAS_EXACT"
MATCH_NAME_PARTIAL = "NAME_PARTIAL"

# Identifier shapes used ONLY to classify a query for exact lookup (never to fabricate identity).
_UEI_RE = re.compile(r"^[A-Z0-9]{12}$")
_CAGE_RE = re.compile(r"^[A-Z0-9]{5}$")
_CIK_RE = re.compile(r"^\d{4,10}$")
_LEI_RE = re.compile(r"^[A-Z0-9]{20}$")
_ENTITY_REF_RE = re.compile(r"^co_[a-z0-9_]+$", re.IGNORECASE)
_ENTITY_REF_UEI_RE = re.compile(r"^co_uei_([A-Z0-9]{5,})$", re.IGNORECASE)
_PIID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{5,}$")

_COMPANY_SUFFIXES = {"inc", "incorporated", "llc", "l l c", "corp", "corporation", "co", "company",
                     "ltd", "limited", "lp", "llp", "plc"}
_NAME_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def _name_tokens(name: str) -> list[str]:
    """Lowercased significant tokens of a name, common company suffixes dropped (never for matching id)."""
    toks = [t for t in _NAME_SPLIT_RE.split((name or "").lower()) if t]
    while toks and toks[-1] in _COMPANY_SUFFIXES:
        toks.pop()
    return toks


def _norm_name(name: str) -> str:
    return " ".join(_name_tokens(name))


# ------------------------------------------------------------------ identifier extraction

_IDENT_TOKEN_RE = re.compile(r"^(uei|cik|cage|lei):(.+)$", re.IGNORECASE)


def _ident_from_tokens(evidence_ids: Iterable[str]) -> dict:
    """Identifiers carried by structured evidence tokens (``uei:``/``cik:``/``cage:``/``lei:``).

    Used ONLY for a record with a single unambiguous subject (a direct threat), so a token can be
    attributed with certainty. Multi-entity records (e.g. a propagated threat carrying BOTH a child and
    parent UEI) are never token-harvested — their identifiers come from structured hop provenance instead.
    """
    out: dict = {}
    for eid in (evidence_ids or []):
        m = _IDENT_TOKEN_RE.match(str(eid).strip())
        if m:
            out.setdefault(m.group(1).lower(), m.group(2).strip().upper())
    return out


def _ident_from_ref(ref: Optional[str]) -> dict:
    """Identifiers carried by the ref shape itself (``co_uei_<UEI>``). Never guesses."""
    if not ref:
        return {}
    m = _ENTITY_REF_UEI_RE.match(str(ref))
    if m:
        return {"uei": m.group(1).upper()}
    return {}


def _merge_ident(dst: dict, src: dict) -> None:
    """Merge identifiers WITHOUT overwriting a value already asserted (identity is not mutated silently)."""
    for k, v in (src or {}).items():
        if v and not dst.get(k):
            dst[k] = v


# ------------------------------------------------------------------ the estate (read projection)

class IntelligenceEstate:
    """A deterministic, point-in-time read projection of the canonical entity/program estate.

    Built from the existing global intelligence streams (``threats`` / ``propagated_threats`` /
    ``opportunities`` / ``relationships``). It is a computed read model — the same pattern as
    :func:`pyrnova.material_changes.build_material_changes` and the Operations Panel views — not a second
    persisted truth system. References back to authoritative records are preserved throughout (§13).
    """

    def __init__(self, as_of: Optional[str] = None):
        self.as_of = as_of
        self.entities: dict[str, dict] = {}     # ref -> entity record
        self.programs: dict[str, dict] = {}     # program_key -> program record
        self.edges: list[dict] = []             # typed relationship edges (deduped)
        # normalized change records grouped for read (kept so pages need no re-read of the streams)
        self.changes_by_entity: dict[str, list[dict]] = {}
        self.changes_by_program: dict[str, list[dict]] = {}
        self._edge_keys: set = set()
        self._ident_index: dict[tuple[str, str], list[tuple[str, str]]] = {}  # (kind,value)->[(objkind,key)]

    # -- entity / program upsert ---------------------------------------------------------------

    def _entity(self, ref: str, name: Optional[str] = None) -> dict:
        ref = str(ref)
        ent = self.entities.get(ref)
        if ent is None:
            ent = {"ref": ref, "kind": KIND_COMPANY, "canonical_name": name or ref,
                   "names": set(), "identifiers": {}, "parent_ref": None,
                   "subsidiary_refs": set(), "programs": set(), "first_seen_at": None}
            _merge_ident(ent["identifiers"], _ident_from_ref(ref))
            self.entities[ref] = ent
        if name:
            ent["names"].add(name)
        return ent

    def _program(self, key: str, name: Optional[str] = None, agency: Optional[str] = None) -> dict:
        key = str(key)
        prog = self.programs.get(key)
        if prog is None:
            prog = {"program_key": key, "kind": KIND_PROGRAM, "name": name or key,
                    "agency": agency, "companies": set(), "first_seen_at": None}
            self.programs[key] = prog
        if name and (prog["name"] == key or not prog["name"]):
            prog["name"] = name
        if agency and not prog["agency"]:
            prog["agency"] = agency
        return prog

    def _observe_at(self, ent_or_prog: dict, when: Optional[str]) -> None:
        if when and (ent_or_prog["first_seen_at"] is None or when < ent_or_prog["first_seen_at"]):
            ent_or_prog["first_seen_at"] = when

    def _add_edge(self, edge: dict) -> None:
        key = (edge.get("from_ref"), edge.get("to_ref"), edge.get("relation"), edge.get("valid_from"))
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append(edge)

    # -- lookups used by search / pages --------------------------------------------------------

    def _index_identifiers(self) -> None:
        """Build the exact-identifier lookup once the estate is fully populated."""
        self._ident_index.clear()
        for ref, ent in self.entities.items():
            self._ident_index.setdefault(("ref", ref.upper()), []).append((KIND_COMPANY, ref))
            for kind, value in (ent.get("identifiers") or {}).items():
                if value:
                    self._ident_index.setdefault((kind, str(value).upper()), []).append((KIND_COMPANY, ref))
        for key in self.programs:
            self._ident_index.setdefault(("program", key.upper()), []).append((KIND_PROGRAM, key))

    def resolve_identifier(self, value: str) -> list[tuple[str, str]]:
        """Return the object(s) an exact identifier resolves to (dictionary lookup — never an LLM)."""
        v = str(value or "").strip().upper()
        if not v:
            return []
        hits: list[tuple[str, str]] = []
        seen = set()
        for kind in ("ref", "uei", "cage", "cik", "lei", "program"):
            for obj in self._ident_index.get((kind, v), []):
                if obj not in seen:
                    seen.add(obj)
                    hits.append(obj)
        return hits


# ------------------------------------------------------------------ estate construction

def build_estate(
    *,
    threats: Iterable[dict] = (),
    propagated_threats: Iterable[dict] = (),
    opportunities: Iterable[dict] = (),
    relationships: Iterable[dict] = (),
    as_of: Optional[str] = None,
) -> IntelligenceEstate:
    """Assemble the point-in-time :class:`IntelligenceEstate` from the global intelligence streams.

    Only records knowable at ``as_of`` contribute, so an entity/program/relationship/event that could not
    yet be known does not appear historically (§19). Deterministic and side-effect free.
    """
    est = IntelligenceEstate(as_of=as_of)

    def _ingest_change(norm: dict) -> None:
        if not _visible(norm, as_of):
            return
        ref = norm.get("subject_ref")
        if not ref:
            return
        ent = est._entity(ref, norm.get("affected_entity"))
        est._observe_at(ent, norm.get("observed_at"))
        # A direct threat has exactly one subject, so its structured id tokens attribute unambiguously.
        if norm.get("_kind") == "threat":
            _merge_ident(ent["identifiers"], _ident_from_tokens(norm.get("evidence_ids")))
        est.changes_by_entity.setdefault(ref, []).append(norm)
        program = norm.get("affected_program")
        agency = norm.get("agency")
        if program:
            prog = est._program(program, name=norm.get("affected_program"), agency=agency)
            est._observe_at(prog, norm.get("observed_at"))
            prog["companies"].add(ref)
            ent["programs"].add(program)
            est.changes_by_program.setdefault(program, []).append(norm)
        # Relationship edges + the identifiers they authoritatively assert live on the propagation path.
        prop = norm.get("propagation") or {}
        for hop in (prop.get("path") or []):
            _ingest_edge(est, hop, as_of)

    for rec in threats:
        _ingest_change(_threat_change(rec, "threat"))
    for rec in propagated_threats:
        _ingest_change(_threat_change(rec, "propagated_threat"))
    for rec in opportunities:
        norm = _opportunity_change(rec)
        # An opportunity's subject is the customer id, not a canonical company node; only its program and
        # any edges are estate-relevant here. Skip the customer-as-entity to avoid inventing an entity.
        if not _visible(norm, as_of):
            continue
        program = norm.get("affected_program")
        if program:
            prog = est._program(program, agency=norm.get("agency"))
            est._observe_at(prog, norm.get("observed_at"))

    for rec in relationships or ():
        _ingest_stream_edge(est, rec, as_of)

    est._index_identifiers()
    return est


def _ingest_edge(est: IntelligenceEstate, hop: dict, as_of: Optional[str]) -> None:
    """Ingest one propagation-path hop as a typed relationship edge (temporal + provenance preserved)."""
    from_ref, to_ref = hop.get("from_ref"), hop.get("to_ref")
    if not from_ref or not to_ref:
        return
    available_at = hop.get("available_at")
    if as_of and available_at and str(available_at) > str(as_of):
        return  # relationship not yet knowable at the cutoff
    prov = hop.get("provenance") or {}
    frm = est._entity(from_ref)
    to = est._entity(to_ref)
    relation = hop.get("relation")
    # Structured identifiers a SUBSIDIARY_OF hop asserts about each endpoint (never a bare token guess).
    if relation == "SUBSIDIARY_OF":
        _merge_ident(frm["identifiers"], {"uei": (prov.get("child_uei") or "").upper() or None,
                                          "recipient_id": prov.get("child_recipient_id")})
        _merge_ident(to["identifiers"], {"uei": (prov.get("parent_uei") or "").upper() or None,
                                         "recipient_id": prov.get("parent_recipient_id")})
        frm["parent_ref"] = to_ref
        to["subsidiary_refs"].add(from_ref)
    est._add_edge({
        "relation": relation,
        "from_ref": from_ref, "to_ref": to_ref,
        "link_class": hop.get("link_class"), "join_method": hop.get("join_method"),
        "confidence": prov.get("confidence") if prov.get("confidence") is not None else hop.get("confidence"),
        "valid_from": hop.get("valid_from"), "valid_to": hop.get("valid_to"),
        "available_at": available_at, "evidence_ids": list(hop.get("evidence_ids") or []),
        "source_id": hop.get("source_id"), "provenance": prov, "depth": hop.get("depth"),
    })


def _ingest_stream_edge(est: IntelligenceEstate, rec: dict, as_of: Optional[str]) -> None:
    """Ingest a persisted ``relationships``-stream edge (M17 shape) if knowable at the cutoff."""
    from_ref = rec.get("from_ref") or rec.get("subject_id")
    to_ref = rec.get("to_ref") or rec.get("object_id")
    relation = rec.get("relation") or rec.get("predicate")
    if not from_ref or not to_ref:
        return
    available_at = rec.get("available_at") or rec.get("first_observed_at")
    if as_of and available_at and str(available_at) > str(as_of):
        return
    est._entity(from_ref, rec.get("from_name"))
    est._entity(to_ref, rec.get("to_name"))
    est._add_edge({
        "relation": relation, "from_ref": from_ref, "to_ref": to_ref,
        "link_class": rec.get("link_class"), "join_method": rec.get("join_method"),
        "confidence": rec.get("confidence"), "valid_from": rec.get("valid_from"),
        "valid_to": rec.get("valid_to"), "available_at": available_at,
        "evidence_ids": list(rec.get("evidence_ids") or []), "source_id": rec.get("source_id"),
        "provenance": rec.get("provenance") or {}, "depth": rec.get("depth"),
    })


# ------------------------------------------------------------------ deterministic search (§6–§9)

def search(estate: IntelligenceEstate, query: str, *, limit: int = 25) -> dict:
    """Resolve a query against the Pyrnova estate deterministically (no LLM, ever).

    Order: exact identifier → exact name/alias → scored partial name. Resolution state is honest —
    EXACT only for a single unambiguous match; several equal matches are AMBIGUOUS (never merged); a
    scored partial is PROBABLE with an explicit confidence; nothing found is UNRESOLVED.
    """
    raw = query or ""
    q = raw.strip()
    if not q or not _name_tokens(q) and not re.search(r"[A-Za-z0-9]", q):
        return {"query": raw, "resolution": RESOLUTION_UNRESOLVED, "match_basis": None,
                "note": "empty or malformed query", "count": 0, "results": []}
    if len(q) > 256:
        return {"query": raw[:64] + "…", "resolution": RESOLUTION_UNRESOLVED, "match_basis": None,
                "note": "query too long to resolve", "count": 0, "results": []}

    # 1) Exact identifier — pure dictionary lookup.
    ident_hits = estate.resolve_identifier(q)
    if ident_hits:
        basis = _identifier_basis(estate, q)
        results = [_result_for(estate, kind, key, match_basis=basis) for kind, key in ident_hits]
        results.sort(key=lambda r: (r["type"], r["canonical_name"], r["key"]))
        resolution = RESOLUTION_EXACT if len(results) == 1 else RESOLUTION_AMBIGUOUS
        return {"query": raw, "resolution": resolution, "match_basis": basis,
                "count": len(results), "results": results[:limit]}

    # 2) Name / alias search — deterministic scored matching.
    qn = _norm_name(q)
    qtokens = set(_name_tokens(q))
    exact: list[tuple[str, str, str]] = []   # (objkind, key, match_basis)
    partial: list[tuple[float, str, str]] = []  # (score, objkind, key)

    for ref, ent in estate.entities.items():
        names = {ent["canonical_name"], *ent["names"]}
        norms = {_norm_name(n) for n in names if n}
        if qn and qn in norms:
            basis = MATCH_NAME_EXACT if _norm_name(ent["canonical_name"]) == qn else MATCH_ALIAS_EXACT
            exact.append((KIND_COMPANY, ref, basis))
            continue
        score = max((_token_score(qtokens, set(_name_tokens(n))) for n in names if n), default=0.0)
        if score > 0:
            partial.append((score, KIND_COMPANY, ref))
    for key, prog in estate.programs.items():
        norms = {_norm_name(prog["name"]) } if prog["name"] else set()
        if qn and qn in norms:
            exact.append((KIND_PROGRAM, key, MATCH_NAME_EXACT))
            continue
        score = _token_score(qtokens, set(_name_tokens(prog["name"]))) if prog["name"] else 0.0
        if score > 0:
            partial.append((score, KIND_PROGRAM, key))

    if exact:
        results = [_result_for(estate, k, key, match_basis=b) for k, key, b in exact]
        results.sort(key=lambda r: (r["type"], r["canonical_name"], r["key"]))
        resolution = RESOLUTION_EXACT if len(results) == 1 else RESOLUTION_AMBIGUOUS
        return {"query": raw, "resolution": resolution, "match_basis": MATCH_NAME_EXACT,
                "count": len(results), "results": results[:limit]}

    if partial:
        partial.sort(key=lambda t: (-t[0], t[1], t[2]))
        results = [dict(_result_for(estate, k, key, match_basis=MATCH_NAME_PARTIAL), confidence=round(score, 3))
                   for score, k, key in partial]
        top = partial[0][0]
        # Several equally-strong partial matches → ambiguous; otherwise a ranked probable list.
        resolution = (RESOLUTION_AMBIGUOUS
                      if sum(1 for s, _, _ in partial if s == top) > 1 else RESOLUTION_PROBABLE)
        return {"query": raw, "resolution": resolution, "match_basis": MATCH_NAME_PARTIAL,
                "count": len(results), "results": results[:limit]}

    return {"query": raw, "resolution": RESOLUTION_UNRESOLVED, "match_basis": None,
            "note": "no entity or program in the Pyrnova estate matched", "count": 0, "results": []}


def _token_score(q: set, cand: set) -> float:
    """Deterministic token-overlap score in [0,1]; 0 when the query is not a meaningful subset overlap."""
    if not q or not cand:
        return 0.0
    inter = q & cand
    if not inter:
        return 0.0
    # Jaccard-like, but require that the overlap covers a real share of the shorter side so a single
    # common token ("technologies") does not mint a match.
    coverage = len(inter) / min(len(q), len(cand))
    if coverage < 0.5:
        return 0.0
    return len(inter) / len(q | cand)


def _identifier_basis(estate: IntelligenceEstate, q: str) -> str:
    v = q.strip().upper()
    if _ENTITY_REF_RE.match(v):
        return MATCH_ENTITY_ID
    # Prefer the structural id-shape of the value, then confirm it exists in the index.
    if _UEI_RE.match(v) and estate._ident_index.get(("uei", v)):
        return MATCH_UEI
    if estate._ident_index.get(("program", v)):
        return MATCH_PROGRAM_ID
    if _LEI_RE.match(v) and estate._ident_index.get(("lei", v)):
        return MATCH_LEI
    if _CIK_RE.match(v) and estate._ident_index.get(("cik", v)):
        return MATCH_CIK
    if _CAGE_RE.match(v) and estate._ident_index.get(("cage", v)):
        return MATCH_CAGE
    if _UEI_RE.match(v):
        return MATCH_UEI
    if _PIID_RE.match(v):
        return MATCH_PROGRAM_ID
    return MATCH_ENTITY_ID


def _result_for(estate: IntelligenceEstate, objkind: str, key: str, *, match_basis: str) -> dict:
    if objkind == KIND_PROGRAM:
        prog = estate.programs[key]
        return {"type": KIND_PROGRAM, "key": key, "canonical_name": prog["name"],
                "identifier": key, "identifier_kind": MATCH_PROGRAM_ID,
                "parent_or_agency": prog.get("agency"), "match_basis": match_basis,
                "link": {"program": key}}
    ent = estate.entities[key]
    ident_kind, ident_val = _primary_identifier(ent)
    parent = ent.get("parent_ref")
    parent_name = estate.entities[parent]["canonical_name"] if parent in estate.entities else parent
    return {"type": KIND_COMPANY, "key": key, "canonical_name": ent["canonical_name"],
            "identifier": ident_val, "identifier_kind": ident_kind,
            "parent_or_agency": parent_name, "match_basis": match_basis,
            "link": {"company": key}}


def _primary_identifier(ent: dict) -> tuple[Optional[str], Optional[str]]:
    ids = ent.get("identifiers") or {}
    for kind, label in (("uei", MATCH_UEI), ("cage", MATCH_CAGE), ("cik", MATCH_CIK), ("lei", MATCH_LEI)):
        if ids.get(kind):
            return label, ids[kind]
    return MATCH_ENTITY_ID, ent["ref"]


# ------------------------------------------------------------------ page projections (§3/§4)

def _finalize_entity(ent: dict) -> dict:
    """Public identity view for one entity (aliases = observed name variants other than the canonical)."""
    canonical = ent["canonical_name"]
    aliases = sorted(n for n in ent["names"] if n and n != canonical)
    return {"ref": ent["ref"], "kind": ent["kind"], "canonical_name": canonical, "aliases": aliases,
            "identifiers": dict(sorted((ent.get("identifiers") or {}).items())),
            "parent_ref": ent.get("parent_ref"),
            "subsidiary_refs": sorted(ent.get("subsidiary_refs") or []),
            "first_seen_at": ent.get("first_seen_at")}


def _material_event(norm: dict) -> dict:
    """Compact GLOBAL material-event view (observed fact / assessment kept distinct — never flattened).

    This is the supporting-surface projection: it references the change by id so a client can open the
    full Material Change, and never asserts a customer-specific relevance on a global page.
    """
    prop = norm.get("propagation") or {}
    return {
        "id": norm.get("id"), "kind": norm.get("_kind"),
        "title": norm.get("title") or norm.get("event_summary") or norm.get("mechanism"),
        "observed": {
            "event_type": norm.get("event_type"), "event_summary": norm.get("event_summary"),
            "affected_program": norm.get("affected_program"), "agency": norm.get("agency"),
            "event_time": norm.get("event_time") or "UNKNOWN",
            "observed_at": norm.get("observed_at") or "UNKNOWN",
            "catalyst_class": norm.get("catalyst_class"),
        },
        "assessment": {
            "mechanism": norm.get("mechanism"), "consequence": norm.get("consequence"),
            "materiality": norm.get("severity", "UNKNOWN"), "confidence": norm.get("confidence", "UNKNOWN"),
            "affected_value_category": norm.get("affected_value_category"),
        },
        "is_propagated": bool(prop.get("is_propagated")),
        "propagation_depth": prop.get("depth") if prop else None,
        "outcome_state": norm.get("outcome_state", "UNKNOWN"),
        "evidence_ids": list(norm.get("evidence_ids") or []),
        "root_change_id": norm.get("root_change_id"),
    }


def _evidence_refs(norms: list[dict], edges: list[dict]) -> list[dict]:
    """Distinct evidence references (source + id), never bodies (§18). Independence stays conservative."""
    seen: dict[str, dict] = {}
    def _add(eid: str, source: Optional[str], etype: str):
        eid = str(eid)
        if eid and eid not in seen:
            seen[eid] = {"evidence_id": eid, "source": source or _source_of(eid), "type": etype}
    for n in norms:
        source = (n.get("evidence_sources") or [None])[0]
        for eid in (n.get("evidence_ids") or []):
            _add(eid, source, "intelligence")
        if n.get("archive_hash"):
            _add(f"archive:{n['archive_hash']}", n.get("source_ref"), "raw_authoritative_bytes")
    for e in edges:
        for eid in (e.get("evidence_ids") or []):
            _add(eid, e.get("source_id"), "relationship")
    return sorted(seen.values(), key=lambda r: (r["type"], r["source"] or "", r["evidence_id"]))


def _source_of(evidence_id: str) -> Optional[str]:
    eid = str(evidence_id)
    if ":" in eid:
        return eid.split(":", 1)[0]
    return None


def _edges_touching(estate: IntelligenceEstate, ref: str, *, as_of: Optional[str]) -> list[dict]:
    """Relationship edges incident to ``ref``, temporally valid at ``as_of`` (validity respected, §19)."""
    out = []
    for e in estate.edges:
        if ref not in (e.get("from_ref"), e.get("to_ref")):
            continue
        if as_of is not None:
            vf, vt = e.get("valid_from"), e.get("valid_to")
            if vf and str(vf) > str(as_of):
                continue
            if vt and str(vt) <= str(as_of):
                continue
        direction = "OUTBOUND" if e.get("from_ref") == ref else "INBOUND"
        other = e.get("to_ref") if direction == "OUTBOUND" else e.get("from_ref")
        other_name = (estate.entities.get(other) or {}).get("canonical_name", other)
        out.append({
            "relation": e.get("relation"), "direction": direction,
            "related_ref": other, "related_name": other_name,
            "link_class": e.get("link_class"), "join_method": e.get("join_method"),
            "confidence": e.get("confidence"),
            "valid_from": e.get("valid_from"), "valid_to": e.get("valid_to"),
            "evidence_ids": list(e.get("evidence_ids") or []),
            "source_id": e.get("source_id"),
        })
    out.sort(key=lambda r: (r["relation"] or "", r["related_name"] or "", r["related_ref"] or ""))
    return out


def company_intelligence(estate: IntelligenceEstate, ref: str, *,
                         as_of: Optional[str] = None, customer_context: Optional[dict] = None) -> dict:
    """Assemble the minimum useful company investigation page (§3). Global truth; customer overlay isolated.

    Raises ``KeyError`` when the ref is unknown in the estate (the console maps this to HTTP 404)."""
    if ref not in estate.entities:
        raise KeyError(ref)
    ent = estate.entities[ref]
    norms = estate.changes_by_entity.get(ref, [])
    edges = _edges_touching(estate, ref, as_of=as_of)
    identity = _finalize_entity(ent)

    events = sorted((_material_event(n) for n in norms),
                    key=lambda e: (e["observed"]["observed_at"] or "", e["id"] or ""), reverse=True)

    # Government activity: programs the entity is evidenced on (from its changes + COMPANY_TO_PROGRAM edges).
    gov: dict[str, dict] = {}
    for n in norms:
        prog = n.get("affected_program")
        if prog:
            row = gov.setdefault(prog, {"program_key": prog, "agency": n.get("agency"),
                                        "role": "incumbent" if n.get("_kind") == "threat" else "exposed",
                                        "evidence_ids": set()})
            row["evidence_ids"].update(n.get("evidence_ids") or [])
    for e in edges:
        if e["relation"] == "COMPANY_TO_PROGRAM" and e["direction"] == "OUTBOUND":
            row = gov.setdefault(e["related_ref"], {"program_key": e["related_ref"], "agency": None,
                                                    "role": "prime", "evidence_ids": set()})
            row["evidence_ids"].update(e.get("evidence_ids") or [])
    government_activity = [dict(r, evidence_ids=sorted(r["evidence_ids"])) for r in
                           sorted(gov.values(), key=lambda r: r["program_key"])]

    history = _history(norms, edges)
    evidence = _evidence_refs(norms, edges)
    gaps = _company_gaps(identity, norms, edges, government_activity)

    page = {
        "as_of": as_of,
        "identity": identity,
        "current_intelligence": {
            "count": len(events),
            "by_disposition": _count_by(norms, lambda n: _disp(n)),
            "material_events": events,
        },
        "government_activity": government_activity,
        "relationships": edges,
        "material_history": history,
        "evidence": evidence,
        "intelligence_gaps": gaps,
    }
    if customer_context is not None:
        page["customer_context"] = customer_context  # separately keyed; never merged into global truth
    return page


def program_intelligence(estate: IntelligenceEstate, program_key: str, *,
                         as_of: Optional[str] = None, customer_context: Optional[dict] = None) -> dict:
    """Assemble the minimum useful program investigation page (§4)."""
    if program_key not in estate.programs:
        raise KeyError(program_key)
    prog = estate.programs[program_key]
    norms = estate.changes_by_program.get(program_key, [])
    events = sorted((_material_event(n) for n in norms),
                    key=lambda e: (e["observed"]["observed_at"] or "", e["id"] or ""), reverse=True)

    companies = []
    for ref in sorted(prog["companies"]):
        ent = estate.entities.get(ref, {"ref": ref, "canonical_name": ref})
        role = "incumbent"
        for n in norms:
            if n.get("subject_ref") == ref:
                role = "incumbent" if n.get("_kind") == "threat" else "exposed"
                break
        ident_kind, ident_val = _primary_identifier(ent) if ref in estate.entities else (None, None)
        companies.append({"ref": ref, "name": ent.get("canonical_name", ref), "role": role,
                          "identifier": ident_val, "identifier_kind": ident_kind})

    all_edges = [e for e in (_edges_touching(estate, r, as_of=as_of) for r in prog["companies"]) for e in e]
    history = _history(norms, [])
    evidence = _evidence_refs(norms, [])
    gaps = _program_gaps(prog, norms, companies)

    page = {
        "as_of": as_of,
        "program_identity": {
            "program_key": program_key, "kind": KIND_PROGRAM, "name": prog["name"],
            "agency": prog.get("agency"), "identifiers": {"program_id": program_key},
            "status": "UNKNOWN", "first_seen_at": prog.get("first_seen_at"),
        },
        "material_changes": {"count": len(events), "material_events": events},
        "companies": companies,
        "evidence": evidence,
        "material_history": history,
        "intelligence_gaps": gaps,
    }
    if customer_context is not None:
        page["customer_context"] = customer_context
    return page


# ------------------------------------------------------------------ history / gaps / small helpers

def _disp(norm: dict) -> str:
    kind = norm.get("_kind")
    if kind in ("threat", "propagated_threat"):
        return "THREAT"
    if kind == "opportunity":
        return "OPPORTUNITY"
    return "MONITORING"


def _count_by(items, keyfn) -> dict:
    out: dict[str, int] = {}
    for it in items:
        k = keyfn(it)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _history(norms: list[dict], edges: list[dict]) -> list[dict]:
    """A chronological intelligence history: material events, relationship establishments, outcomes.

    Point-in-time states are NOT flattened into the present — each entry keeps its own ``at`` and kind so
    a reader sees when each fact became knowable (§19)."""
    rows: list[dict] = []
    for n in norms:
        rows.append({"at": n.get("observed_at") or "UNKNOWN", "kind": "MATERIAL_EVENT",
                     "summary": n.get("event_summary") or n.get("mechanism"),
                     "detail": {"mechanism": n.get("mechanism"), "severity": n.get("severity"),
                                "confidence": n.get("confidence"), "program": n.get("affected_program")},
                     "ref_id": n.get("id")})
        outcome = n.get("outcome_state")
        if outcome and outcome != "UNKNOWN":
            rows.append({"at": n.get("observed_at") or "UNKNOWN", "kind": "OUTCOME",
                         "summary": f"outcome: {outcome}", "detail": {"outcome_state": outcome},
                         "ref_id": n.get("id")})
    for e in edges:
        rows.append({"at": e.get("valid_from") or "UNKNOWN", "kind": "RELATIONSHIP",
                     "summary": f"{e.get('relation')} — {e.get('related_name')}",
                     "detail": {"relation": e.get("relation"), "link_class": e.get("link_class"),
                                "join_method": e.get("join_method")},
                     "ref_id": e.get("related_ref")})
    rows.sort(key=lambda r: (str(r["at"]), r["kind"], str(r.get("ref_id") or "")))
    return rows


def _company_gaps(identity: dict, norms: list[dict], edges: list[dict],
                  government_activity: list[dict]) -> list[str]:
    """State honestly what Pyrnova does NOT know (§17). No inference to fill a section."""
    gaps: list[str] = []
    ids = identity.get("identifiers") or {}
    if not ids.get("uei"):
        gaps.append("No UEI stored for this entity.")
    if not ids.get("cage"):
        gaps.append("No CAGE code stored.")
    if not ids.get("cik"):
        gaps.append("No SEC CIK stored (no linked public-filer identity).")
    if not identity.get("parent_ref") and not identity.get("subsidiary_refs"):
        gaps.append("Ownership unresolved: no parent or subsidiary relationship evidenced.")
    if not any(e["relation"] in ("SUBCONTRACTOR_OF", "COMPANY_TO_PROGRAM") for e in edges):
        gaps.append("No evidenced teaming or prime/sub relationship currently stored.")
    if not government_activity:
        gaps.append("No evidenced government program activity currently stored.")
    if any((n.get("outcome_state") in (None, "UNKNOWN", "UNRESOLVED")) for n in norms):
        gaps.append("One or more material changes have an unresolved outcome.")
    gaps.append("No verified facility, capacity, workforce, or supplier information stored (out of scope).")
    return gaps


def _program_gaps(prog: dict, norms: list[dict], companies: list[dict]) -> list[str]:
    gaps: list[str] = []
    if not prog.get("agency"):
        gaps.append("No contracting agency evidenced.")
    if len(companies) <= 1:
        gaps.append("Only one company is evidenced on this program; teaming structure is not fully known.")
    if any((n.get("outcome_state") in (None, "UNKNOWN", "UNRESOLVED")) for n in norms):
        gaps.append("One or more program-linked material changes have an unresolved outcome.")
    gaps.append("Program status (active/awarded/closed), full value, and period of performance are not "
                "independently evidenced here (out of scope).")
    return gaps


__all__ = [
    "IntelligenceEstate", "build_estate", "search",
    "company_intelligence", "program_intelligence",
    "KIND_COMPANY", "KIND_PROGRAM",
    "RESOLUTION_EXACT", "RESOLUTION_PROBABLE", "RESOLUTION_AMBIGUOUS", "RESOLUTION_UNRESOLVED",
    "MATCH_ENTITY_ID", "MATCH_PROGRAM_ID", "MATCH_UEI", "MATCH_CAGE", "MATCH_CIK", "MATCH_LEI",
    "MATCH_NAME_EXACT", "MATCH_ALIAS_EXACT", "MATCH_NAME_PARTIAL",
]
