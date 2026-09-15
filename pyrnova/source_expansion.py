"""Offline-first M4 integration from archived source pages into the intelligence kernel."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .archive import EvidenceArchive
from .contribution import SourceContributionLedger
from .integrate import sec_issuer_entity
from .models import Entity, Evidence
from .normalize import normalize_grant_opportunity
from .precursors import ProgramChain, ProgramSignal, build_program_chains
from .sources.acquisition_forecast import parse_forecast_csv, public_artifact_url
from .sources.grants_gov import deduplicate_opportunities
from .sources.registry import get_spec
from .sources.sec_edgar import extract_capex_facts, filing_url, filings_since, normalize_filing


@dataclass
class SourceExpansionBatch:
    normalized: dict[str, list[dict]] = field(default_factory=dict)
    signals: list[ProgramSignal] = field(default_factory=list)
    chains: list[ProgramChain] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    evidence_by_signal_id: dict[str, Evidence] = field(default_factory=dict)
    source_contribution: dict[str, dict] = field(default_factory=dict)


def _archive_page(archive: EvidenceArchive, source_id: str, raw: bytes, source_ref: str,
                  source_url: str, observed_at: str,
                  normalized: dict | None = None, meta: dict | None = None) -> Evidence:
    spec = get_spec(source_id)
    return archive.put(
        raw,
        source_id=source_id,
        retention_tier=spec.retention_tier,
        source_ref=source_ref,
        source_url=source_url,
        normalized=normalized,
        meta=meta if meta is not None else {"offline_replay": True, "observed_at": observed_at},
    )


def ingest_source_expansion(
    *,
    archive: EvidenceArchive,
    observed_at: str,
    grants_response: bytes | None = None,
    sec_submissions_response: bytes | None = None,
    sec_companyfacts_response: bytes | None = None,
    forecast_response: bytes | None = None,
    forecast_agency: str | None = None,
    forecast_url: str | None = None,
) -> SourceExpansionBatch:
    """Replay exact archived/fixture bytes with no external calls or candidate creation."""
    batch = SourceExpansionBatch()
    ledger = SourceContributionLedger()

    if grants_response is not None:
        payload = json.loads(grants_response)
        data = payload.get("data") if isinstance(payload, dict) else None
        rows = data.get("oppHits") if isinstance(data, dict) else None
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError("malformed Grants.gov archived response")
        unique = deduplicate_opportunities(rows)
        normalized = [normalize_grant_opportunity(row) for row in unique]
        batch.normalized["grants_gov"] = normalized
        metrics = ledger.source("grants_gov")
        metrics.raw_records += len(rows)
        metrics.duplicates_removed += len(rows) - len(unique)
        metrics.normalized_events += len(normalized)
        evidence = _archive_page(
            archive, "grants_gov", grants_response, "search2:archived",
            "https://api.grants.gov/v1/api/search2", observed_at,
        )
        batch.evidence.append(evidence)
        for row in normalized:
            if row["grant_signal_class"] == "enrichment" or not row["grant_source_identity"]:
                continue
            stage = "FUNDING" if row["grant_signal_class"] == "direct_opportunity" else "INTENT"
            program_key = ":".join(filter(None, [row.get("agency_code"), row.get("opportunity_number")]))
            signal = ProgramSignal(
                source_id="grants_gov",
                source_ref=row["grant_source_identity"],
                stage=stage,
                program_key=program_key or row["grant_source_identity"],
                summary=row.get("title") or row["grant_source_identity"],
                available_at=observed_at,
                agency=row.get("agency"),
                confidence="HIGH" if row.get("candidate_eligible") else "LOW",
                meta={"signal_role": row["grant_signal_class"], "candidate_eligible": False},
            )
            batch.signals.append(signal)
            batch.evidence_by_signal_id[signal.id] = evidence

    if sec_submissions_response is not None:
        submissions = json.loads(sec_submissions_response)
        if not isinstance(submissions, dict) or submissions.get("cik") in (None, ""):
            raise ValueError("malformed SEC submissions archived response")
        companyfacts = json.loads(sec_companyfacts_response) if sec_companyfacts_response else {}
        rows = filings_since(submissions)
        filings = [normalize_filing(row, cik=submissions["cik"], company_metadata={**submissions, **companyfacts}) for row in rows]
        filings = [row for row in filings if row["filing_identity"] and row["focused_form"]]
        capex_facts = extract_capex_facts(companyfacts) if companyfacts else []
        batch.normalized["sec_edgar"] = filings + capex_facts
        metrics = ledger.source("sec_edgar")
        metrics.raw_records += len(rows) + len(capex_facts)
        metrics.normalized_events += len(filings) + len(capex_facts)
        cik10 = str(submissions["cik"]).zfill(10)
        # sec_edgar is NORMALIZED_ONLY: durably archive only reviewed structured facts +
        # hash provenance (original_content_sha256 links back to the raw page), never raw
        # source expression. Mirrors sec_edgar.archive_observation's normalized contract.
        submissions_facts = [
            {"accession_number": row.get("accessionNumber"), "form": row.get("form"),
             "filed_at": row.get("filingDate"), "date": row.get("reportDate"),
             "source_url": filing_url(cik10, row.get("accessionNumber"), row.get("primaryDocument"))}
            for row in rows
        ]
        evidence = _archive_page(
            archive, "sec_edgar", sec_submissions_response,
            f"submissions:{cik10}",
            f"https://data.sec.gov/submissions/CIK{cik10}.json", observed_at,
            normalized={"id": f"submissions:{cik10}", "cik": cik10,
                        "source_ref": f"submissions:{cik10}", "type": "submissions",
                        "value": submissions_facts},
            meta={"fetched_at": observed_at},
        )
        batch.evidence.append(evidence)
        companyfacts_evidence = None
        if sec_companyfacts_response is not None:
            companyfacts_facts = [
                {"id": fact["fact_identity"], **{key: fact[key] for key in (
                    "value_usd", "period_start", "period_end", "filed_at", "form",
                    "accession_number", "fiscal_year", "fiscal_period", "signal")}}
                for fact in capex_facts
            ]
            companyfacts_evidence = _archive_page(
                archive, "sec_edgar", sec_companyfacts_response,
                f"companyfacts:{cik10}",
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json",
                observed_at,
                normalized={"id": f"companyfacts:{cik10}", "cik": cik10,
                            "source_ref": f"companyfacts:{cik10}", "type": "companyfacts",
                            "value": companyfacts_facts},
                meta={"fetched_at": observed_at},
            )
            batch.evidence.append(companyfacts_evidence)
        batch.entities.append(sec_issuer_entity(
            cik=str(submissions["cik"]),
            company_name=submissions.get("name") or companyfacts.get("entityName") or "",
            tickers=submissions.get("tickers") or companyfacts.get("tickers") or [],
        ))
        for row in filings:
            signal = ProgramSignal(
                source_id="sec_edgar",
                source_ref=row["filing_identity"],
                stage="INTENT",
                program_key=f"sec:{row['cik']}:corporate-change",
                summary=row.get("primary_document_description") or f"{row.get('form')} filing",
                available_at=observed_at,
                confidence="MEDIUM" if row.get("signals") else "LOW",
                meta={"signals": row.get("signals") or [], "candidate_eligible": False},
            )
            batch.signals.append(signal)
            batch.evidence_by_signal_id[signal.id] = evidence
        for fact in capex_facts:
            signal = ProgramSignal(
                source_id="sec_edgar",
                source_ref=fact["fact_identity"],
                stage="OUTCOME",
                program_key=f"sec:{fact['cik']}:corporate-change",
                summary=f"Filed capital expenditure cash flow for period ending {fact.get('period_end') or 'unknown'}",
                available_at=fact["filed_at"],
                confidence="HIGH",
                meta={"value_usd": fact["value_usd"], "candidate_eligible": False},
            )
            batch.signals.append(signal)
            batch.evidence_by_signal_id[signal.id] = companyfacts_evidence or evidence

    if forecast_response is not None:
        if not forecast_agency or not forecast_url:
            raise ValueError("forecast agency and official artifact URL are required")
        safe_forecast_url = public_artifact_url(forecast_url)
        rows = parse_forecast_csv(
            forecast_response, agency=forecast_agency, artifact_url=safe_forecast_url,
            observed_at=observed_at,
        )
        batch.normalized["acquisition_forecast"] = rows
        metrics = ledger.source("acquisition_forecast")
        metrics.raw_records += len(rows)
        metrics.normalized_events += len(rows)
        evidence = _archive_page(
            archive, "acquisition_forecast", forecast_response, safe_forecast_url,
            safe_forecast_url, observed_at,
        )
        batch.evidence.append(evidence)
        for row in rows:
            signal = ProgramSignal(
                source_id="acquisition_forecast",
                source_ref=row["source_ref"],
                stage="MARKET_ENGAGEMENT",
                program_key=row["program_key"],
                summary=row["title"],
                available_at=observed_at,
                agency=row["agency"],
                capabilities=tuple(filter(None, [row.get("naics"), row.get("psc")])),
                confidence="MEDIUM",
                meta={"candidate_eligible": False},
            )
            batch.signals.append(signal)
            batch.evidence_by_signal_id[signal.id] = evidence

    batch.chains = build_program_chains(batch.signals)
    batch.source_contribution = ledger.snapshots()
    return batch
