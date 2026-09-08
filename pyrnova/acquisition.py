"""Source acquisition boundary shared by the CLI and operator console."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone

from .config import Config
from .match import CapabilityProfile


@dataclass
class SourceStatus:
    source: str
    status: str
    records: int = 0
    observed_at: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def fixture_rows(fixtures_dir) -> tuple[list[dict], list[dict]]:
    import json

    awards = json.loads((fixtures_dir / "usaspending_awards.json").read_text())["results"]
    notices = json.loads((fixtures_dir / "sam_opportunities.json").read_text())["opportunitiesData"]
    return awards, notices


def fetch_live_rows(
    cfg: Config,
    profile: CapabilityProfile,
    as_of: date,
    *,
    sam_lookback_days: int = 30,
) -> tuple[list[dict], list[dict], list[SourceStatus]]:
    """Fetch current sources without coupling callers to connector details.

    A source failure is represented explicitly and does not erase a successful
    result from the other source.
    """
    from .sources.usaspending import USAspendingClient

    statuses: list[SourceStatus] = []
    award_rows: list[dict] = []
    seen: set[str] = set()
    observed_at = datetime.now(timezone.utc).isoformat()
    start = (as_of - timedelta(days=6 * 365)).isoformat()
    end = as_of.isoformat()
    naics = profile.naics or None

    try:
        client = USAspendingClient()

        def collect(**kwargs):
            for _raw, results in client.search_awards(
                action_date_start=start,
                action_date_end=end,
                max_pages=3,
                limit=100,
                **kwargs,
            ):
                for row in results:
                    key = row.get("generated_internal_id") or row.get("Award ID")
                    if key and key not in seen:
                        seen.add(str(key))
                        award_rows.append(row)

        for name in profile.search_names:
            collect(recipient_search=[name])
        if naics:
            collect(naics_codes=naics)
        statuses.append(SourceStatus("usaspending", "success", len(award_rows), observed_at))
    except Exception as exc:  # pragma: no cover - network dependent
        statuses.append(SourceStatus("usaspending", "failed", 0, observed_at, str(exc)))

    notice_rows: list[dict] = []
    if not cfg.has_sam:
        statuses.append(
            SourceStatus(
                "sam",
                "unavailable",
                0,
                observed_at,
                "SAM_API_KEY is not configured",
            )
        )
        return award_rows, notice_rows, statuses

    from .sources.sam import SamClient

    failures: list[str] = []
    sam = SamClient(cfg.sam_api_key)
    posted_from = (as_of - timedelta(days=max(1, sam_lookback_days))).strftime("%m/%d/%Y")
    posted_to = as_of.strftime("%m/%d/%Y")
    for ptype in ("r", "p", "s"):
        try:
            _raw, rows = sam.search(
                posted_from=posted_from,
                posted_to=posted_to,
                ptype=ptype,
                naics=(naics[0] if naics else None),
                limit=100,
            )
            notice_rows.extend(rows)
        except Exception as exc:  # pragma: no cover - network dependent
            failures.append(f"{ptype}: {exc}")
    status = "success" if not failures else ("partial" if notice_rows else "failed")
    statuses.append(SourceStatus("sam", status, len(notice_rows), observed_at, "; ".join(failures)))
    return award_rows, notice_rows, statuses
