"""Global Kernel <-> National Domain contract.

Doctrine: **SHARE MECHANISM. KEEP NATIONAL TRUTH NATIONAL.**

The Pyrnova kernel already owns the genuinely country-neutral machinery — provenance, AS-OF,
Material Change, Opportunity/Decision primitives, Decision Window, Decision Memory, the source-rights
*enforcement mechanism*, the Decision-Lead-Time *engine*, tenant isolation, the customer-product SPA.
None of that is duplicated per country.

A :class:`NationalDomain` declares only what a nation *owns* and must not be flattened into a single
universal procurement ontology:

* acquisition/procurement **lifecycle** states and their meaning;
* acquisition **route** semantics (open / limited / panel / FMS / GtG / direct, etc.);
* **access** position taxonomy;
* **Industrial Position** classification (nationally specific; e.g. AU AIC vs sovereign capability);
* **Important Miss** taxonomy (what this nation's product must never fail to surface);
* **DLT calibration** (national — never shared, never fabricated: ``None`` until validated);
* the national **source-rights ownership** (which sources belong to the domain and their activation
  posture — ``UNKNOWN = DENY``, production activation requires rights approval);
* the national **evidence/data boundary** (evidence languages, original-language authority).

This module is additive. It does not change any accepted US semantics; the US domain is a *declaration*
over the existing implementation (see ``us.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


UNKNOWN = "UNKNOWN"


class SourceActivation(str, Enum):
    """Per-source national activation posture. Fail-closed: absence / UNKNOWN => DENY.

    ``ACTIVE``            production acquisition is rights-approved and live.
    ``FIXTURE_ONLY``      lawful for replay/fixtures; live production acquisition NOT yet authorized.
    ``DECLARED``          source exists in the national picture but activation is UNKNOWN => DENY.
    ``PROHIBITED``        a hard lock — this source must NEVER be ingested (e.g. NZ GETS).
    """

    ACTIVE = "ACTIVE"
    FIXTURE_ONLY = "FIXTURE_ONLY"
    DECLARED = "DECLARED"
    PROHIBITED = "PROHIBITED"

    @property
    def ingestible(self) -> bool:
        """Only ACTIVE permits live production ingestion. Everything else is denied by default."""
        return self is SourceActivation.ACTIVE


class ProhibitedSourceIngestion(RuntimeError):
    """Raised when anything attempts to ingest a source a national domain marks PROHIBITED.

    This is the enforcement point for hard locks such as the NZ GETS lock: GETS is national truth
    but is NOT a Pyrnova ingestion source — no scrape, crawl, systematic browse, manual harvest,
    agent-harvest, or reproduction.
    """


@dataclass(frozen=True)
class DLTCalibration:
    """National Decision-Lead-Time calibration. NEVER shared across nations, NEVER fabricated.

    Left ``None`` on a domain whose historical validation has not returned; numbers are only ever the
    accepted, cited validation result for that nation.
    """

    median_dlt_to_market_days: float
    p25_days: float
    corpus_size: int
    qualifying_cases: int
    source_reference: str  # the accepted spec/replay this calibration is cited from


@dataclass(frozen=True)
class NationalSource:
    """A source owned by a national domain, with its national activation posture (rights ownership)."""

    id: str
    name: str
    activation: SourceActivation = SourceActivation.DECLARED
    role: str = "evidence"      # 'evidence' (downstream) is the default; a source is NOT the ontology
    note: str = ""

    @property
    def ingestible(self) -> bool:
        return self.activation.ingestible


@dataclass(frozen=True)
class NationalDomain:
    """A national government-intelligence domain. Declarative national truth + activation posture.

    Behavioural intelligence machinery (Material Change, Opportunity, Decision Object, DLT engine) is
    the *shared kernel's* — a domain feeds it national truth; it does not re-implement it.
    """

    code: str                                    # ISO-3166 alpha-2, uppercase: US, AU, UK, CA, NZ
    name: str
    lifecycle: tuple[str, ...]                   # ordered acquisition lifecycle states (national truth)
    routes: dict[str, str]                       # route code -> national meaning
    access_classes: tuple[str, ...]              # national access position taxonomy
    industrial_position_classes: tuple[str, ...] # national Industrial Position taxonomy
    important_miss: tuple[str, ...]              # national Important Miss taxonomy
    evidence_languages: tuple[str, ...]          # e.g. ("en",) US; ("en","fr") CA (original-language authority)
    sources: tuple[NationalSource, ...] = ()     # national source-rights ownership
    dlt_calibration: Optional[DLTCalibration] = None   # None until validated — never fabricated
    validated: bool = False                      # historical validation accepted for this nation?
    build_authority: bool = False                # owner build authority granted?
    notes: str = ""

    # ---- source-rights ownership helpers (enforcement mechanism is shared; decisions are national) ----

    def source(self, source_id: str) -> Optional[NationalSource]:
        for s in self.sources:
            if s.id == source_id:
                return s
        return None

    def is_ingestible(self, source_id: str) -> bool:
        """Fail-closed: a source unknown to this domain, or not ACTIVE, is NOT ingestible."""
        s = self.source(source_id)
        return bool(s and s.ingestible)

    def assert_ingestible(self, source_id: str) -> None:
        """Raise :class:`ProhibitedSourceIngestion` for a hard-locked source; deny anything not ACTIVE."""
        s = self.source(source_id)
        if s and s.activation is SourceActivation.PROHIBITED:
            raise ProhibitedSourceIngestion(
                f"[{self.code}] {source_id} is PROHIBITED as an ingestion source and must never be "
                f"scraped, crawled, browsed, harvested or reproduced")
        if not (s and s.ingestible):
            raise ProhibitedSourceIngestion(
                f"[{self.code}] {source_id} is not an approved ACTIVE ingestion source (UNKNOWN => DENY)")

    def known_route(self, route_code: str) -> bool:
        return route_code in self.routes

    def __post_init__(self):
        if len(self.code) != 2 or not self.code.isupper():
            raise ValueError(f"national code must be ISO-3166 alpha-2 uppercase: {self.code!r}")
        if self.dlt_calibration is not None and not self.validated:
            raise ValueError(
                f"[{self.code}] DLT calibration present but domain is not validated — refusing to "
                f"present fabricated national calibration")
