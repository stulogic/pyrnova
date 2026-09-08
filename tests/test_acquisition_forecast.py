from pathlib import Path

import pytest

from pyrnova.sources.acquisition_forecast import AcquisitionForecastClient, parse_forecast_csv, public_artifact_url


FIXTURE = Path(__file__).parent / "fixtures" / "acquisition_forecast.csv"


def test_forecast_normalization_is_conservative_and_deterministic():
    rows = parse_forecast_csv(
        FIXTURE.read_bytes(),
        agency="DISA",
        artifact_url="https://example.mil/forecast.csv?tracking=discarded",
        observed_at="2026-09-08T12:00:00+00:00",
    )
    assert len(rows) == 2
    assert rows[0]["source_ref"] == "DISA-2027-001"
    assert rows[0]["stage"] == "MARKET_ENGAGEMENT"
    assert rows[0]["candidate_eligible"] is False
    assert rows[1]["source_ref"].endswith("forecast.csv#row=3")
    assert rows == parse_forecast_csv(
        FIXTURE.read_bytes(), agency="DISA", artifact_url="https://example.mil/forecast.csv?other=1",
        observed_at="2026-09-08T12:00:00+00:00",
    )


def test_forecast_artifact_url_requires_https_and_drops_query():
    assert public_artifact_url("https://agency.gov/data.csv?token=secret") == "https://agency.gov/data.csv"
    with pytest.raises(ValueError):
        public_artifact_url("http://agency.gov/data.csv")


def test_forecast_client_defaults_offline_and_uses_shared_budget(monkeypatch):
    monkeypatch.setattr(
        "pyrnova.sources.acquisition_forecast.get_bytes",
        lambda *_args, **_kwargs: pytest.fail("offline mode made a network call"),
    )
    with pytest.raises(RuntimeError, match="OFFLINE"):
        AcquisitionForecastClient().fetch("https://agency.gov/forecast.csv", agency="Agency")

    monkeypatch.setattr(
        "pyrnova.sources.acquisition_forecast.get_bytes",
        lambda *_args, **_kwargs: (200, FIXTURE.read_bytes()),
    )
    client = AcquisitionForecastClient(mode="LIVE-SAFE", request_budget=1)
    observation = client.fetch("https://agency.gov/forecast.csv", agency="Agency")
    assert observation.mode == "LIVE_SAFE"
    assert client.metrics["calls_made"] == 1
    with pytest.raises(RuntimeError, match="budget exhausted"):
        client.fetch("https://agency.gov/forecast.csv", agency="Agency")
