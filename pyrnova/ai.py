"""AI Intelligence Layer — single bounded interface (authority Part II §B).

v1 keeps AI OPTIONAL: the deterministic path produces real intelligence with no model dependency. When a
reasoner is supplied it may EXTRACT / CONNECT / REASON / CHALLENGE / COMMUNICATE, but every output is an
evidence-grounded *claim* or recommendation — never an authoritative fact — and is routed through human
REVIEW before customer exposure. Pyrnova is model-agnostic: implement this protocol against any provider.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from .models import Opportunity


@runtime_checkable
class Reasoner(Protocol):
    def enrich(self, opp: Opportunity) -> Opportunity:
        """Attach non-authoritative enrichment (e.g. mechanism reasoning, contra-evidence prompts).

        Must not overwrite deterministic fields (ids, dates, evidence, calculations). Should append to
        opp.meta['ai'] and may propose a sharper falsification note or recommended action.
        """
        ...


class NullReasoner:
    """Default: no AI. The deterministic kernel stands alone."""

    def enrich(self, opp: Opportunity) -> Opportunity:
        return opp


def get_reasoner(reasoner: Optional[Reasoner] = None) -> Reasoner:
    return reasoner or NullReasoner()
