"""B2.5 — Vehicle / Access analysis: can this customer actually pursue this?"""

from pyrnova.vehicle_access import (
    DIRECT_ACCESS, TEAMING_REQUIRED, NO_KNOWN_ACCESS, UNKNOWN,
    assess_vehicle_access,
)


def test_customer_holds_vehicle_is_direct_access():
    a = assess_vehicle_access(current_vehicle="SeaPort-NxG", customer_vehicles=["SeaPort-NxG"])
    assert a.verdict == DIRECT_ACCESS and a.teaming_required is False and a.required_vehicle is None


def test_open_market_path_is_direct_regardless_of_vehicle():
    a = assess_vehicle_access(acquisition_path="Full and Open", customer_vehicles=[])
    assert a.verdict == DIRECT_ACCESS and a.teaming_required is False


def test_vehicle_not_held_but_holders_exist_requires_teaming():
    a = assess_vehicle_access(current_vehicle="OASIS+", customer_vehicles=["SeaPort-NxG"],
                              vehicle_holders=["BigPrime"])
    assert a.verdict == TEAMING_REQUIRED
    assert a.teaming_required is True and a.required_vehicle == "OASIS+"
    assert "teammate" in a.summary.lower()


def test_restricting_vehicle_with_no_access_is_no_known_access():
    a = assess_vehicle_access(current_vehicle="Agency IDIQ")
    assert a.verdict == NO_KNOWN_ACCESS and a.required_vehicle == "Agency IDIQ"


def test_unknown_path_is_unknown_not_optimistic():
    a = assess_vehicle_access()
    assert a.verdict == UNKNOWN and a.is_unknown and a.teaming_required is None


def test_material_ceiling_and_expiration_are_recorded():
    a = assess_vehicle_access(current_vehicle="OASIS+", customer_vehicles=["OASIS+"],
                              ceiling=60_000_000_000, expiration="2027-12-31",
                              task_order_history=[{"ref": "TO-1", "vehicle": "OASIS+"}])
    assert a.by_dimension("ceiling") and a.by_dimension("expiration")
    assert a.by_dimension("task_order_history")[0].value["ref"] == "TO-1"
