import json
from datetime import date
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
AS_OF = date(2026, 9, 8)


@pytest.fixture
def as_of():
    return AS_OF


@pytest.fixture
def award_rows():
    return json.loads((FIXTURES / "usaspending_awards.json").read_text())["results"]


@pytest.fixture
def notice_rows():
    return json.loads((FIXTURES / "sam_opportunities.json").read_text())["opportunitiesData"]


@pytest.fixture
def precursor_rows():
    return json.loads((FIXTURES / "federal_register_documents.json").read_text())["results"]


@pytest.fixture
def profile():
    from pyrnova.match import CapabilityProfile

    data = json.loads(
        (Path(__file__).resolve().parent.parent / "examples" / "profiles" / "acme_c4isr.json").read_text()
    )
    return CapabilityProfile.from_dict(data)
