"""Golden tests: the taxi go/no-go against the independent Decimal oracle that verified the v0 workbook
(134 checks, discovery/concierge-phase-b-2026.md §8). The oracle below is copied from that check script,
not derived from the code under test."""

import datetime as dt
from decimal import ROUND_CEILING, ROUND_HALF_UP
from decimal import Decimal as D

import pytest

from tenderer.core.pricing.gonogo import GoNoGo
from tenderer.core.pricing.money import Money
from tenderer.jurisdictions.gr import PAYMENT_DEDUCTION_RATE
from tenderer.sectors.taxi_student_transport.costs import (
    ClientCosts,
    Contract,
    Missing,
    RouteInputs,
    analyse,
    fuel_scenario_net,
    warnings,
)
from tenderer.shell.packs import PACKS

# ---------------- oracle (from the workbook check script, 2026-09-24) ----------------
C = dict(years=3, sign=dt.date(2026, 10, 15), end=dt.date(2029, 6, 30), cons=D("6.5"), fuel=D("1.70"),
         wear=D("0.08"), opp=D("12"), ins=D("0"), rate=D("0.02"), fee=D("30"), share=D("0.95"), scn=D("0.20"))


def o_price(ref, d):
    return (D(ref) * (100 - d) / 100).quantize(D("0.01"), ROUND_HALF_UP)


def o_amt_p(budget):
    return (D(budget) * D("0.002")).quantize(D("0.01"), ROUND_CEILING)


def o_amt_g(ref, d, days):
    return (o_price(ref, d) * days * D("0.04")).quantize(D("0.01"), ROUND_CEILING)


def o_days360(s, e):
    return (e.year - s.year) * 360 + (e.month - s.month) * 30 + (min(e.day, 30) - min(s.day, 30))


O_DED = D("0.0012") * (1 + D("0.03") * D("1.2"))
O_GG_MONTHS = D(o_days360(C["sign"], C["end"])) / 360 * 12 + 2


def o_fixed(rt):
    q = D(rt["days"]) / C["years"] * C["share"]
    esc = D(rt["L"]) if rt["E"] == "ΝΑΙ" else D(0)
    return (D(rt["J"]) * (C["cons"] / 100 * C["fuel"] + C["wear"]) + esc + C["ins"] / q + D(rt["K"]) * C["opp"]
            + (2 * C["fee"] + C["rate"] * o_amt_p(rt["H"]) * 13 / 12) / (D(rt["days"]) * C["share"]))


def o_coef():
    return O_DED + D("0.04") * C["rate"] * O_GG_MONTHS / 12 / C["share"]


def o_net(rt, d):
    return o_price(rt["F"], d) * (1 - o_coef()) - o_fixed(rt)


def o_breakeven(rt):
    return None if o_net(rt, 0) < 0 else max(d for d in range(100) if o_net(rt, d) >= 0)


ROUTES = [
    dict(C_="G26-0703-Τ2", E="ΝΑΙ", F="51.18", days=525, H="26869.50", J="20", K="2.5", L="15", M=3),
    dict(C_="26-ΠΠ-Τ1", E="ΟΧΙ", F="77.55", days=525, H="40713.75", J="55", K="2", L=None, M=None),
    dict(C_="TEST-TIE", E="ΟΧΙ", F="51.25", days=525, H="26906.25", J="10", K="1", L=None, M=10),
    dict(C_="TEST-LOSS", E="ΟΧΙ", F="31.48", days=525, H="16527.00", J="30", K="3", L=None, M=None),
    dict(C_="S26-ΓΛΚΒ-Τ5", E="ΝΑΙ", F="586.30", days=105, H="61561.50", J="150", K="6", L="60", M=15),
]
_edge = dict(C_="TEST-EDGE", E="ΟΧΙ", F="80.00", days=525, H="42000.00", J="12", K="0", L=None, M=20)
_edge["K"] = str(((o_price(_edge["F"], 20) * (1 - o_coef()) - o_fixed(_edge) - D("0.00005")) / C["opp"])
                 .quantize(D("0.000000001")))
ROUTES.append(_edge)

# ---------------- code under test ----------------
@pytest.fixture(scope="module")
def terms(tender):
    return tender.offer


CLIENT = ClientCosts(C["cons"], C["fuel"], C["wear"], C["opp"], C["ins"], C["rate"], C["fee"], C["share"], C["scn"])
CONTRACT = Contract(C["years"], C["sign"], C["end"])


def inputs(rt):
    return RouteInputs(
        reference=Money(D(rt["F"])), days=rt["days"], budget=Money(D(rt["H"])), km_per_day=D(rt["J"]),
        hours_per_day=D(rt["K"]), escort=rt["E"] == "ΝΑΙ", escort_per_day=D(rt["L"]) if rt["L"] else None,
    )


def test_deduction_rate_matches_workbook():
    assert PAYMENT_DEDUCTION_RATE == O_DED == D("0.0012432")


@pytest.mark.parametrize("rt", ROUTES, ids=[r["C_"] for r in ROUTES])
def test_route_matches_oracle(rt, terms):
    result = analyse(inputs(rt), CLIENT, CONTRACT, terms, PAYMENT_DEDUCTION_RATE)
    assert isinstance(result, GoNoGo)
    for d in range(100):  # the workbook's 100-row grid
        assert result.net(d) == pytest.approx(o_net(rt, d), abs=D("1e-20"))
    q = D(rt["days"]) / C["years"] * C["share"]
    assert result.net_per_year(0) == pytest.approx(o_net(rt, 0) * q, abs=D("1e-18"))
    assert result.break_even == o_breakeven(rt)
    m = rt["M"] or 0
    fuel_day = D(rt["J"]) * C["cons"] / 100 * C["fuel"]
    assert fuel_scenario_net(result, inputs(rt), CLIENT, m) == pytest.approx(o_net(rt, m) - fuel_day * C["scn"],
                                                                             abs=D("1e-20"))


def test_edge_route_break_even_is_exactly_20(terms):
    result = analyse(inputs(_edge), CLIENT, CONTRACT, terms, PAYMENT_DEDUCTION_RATE)
    assert isinstance(result, GoNoGo)
    assert result.break_even == 20
    assert result.net(20) >= 0 > result.net(21)


def test_loss_route_has_no_break_even_and_warns(terms):
    rt = next(r for r in ROUTES if r["C_"] == "TEST-LOSS")
    result = analyse(inputs(rt), CLIENT, CONTRACT, terms, PAYMENT_DEDUCTION_RATE)
    assert isinstance(result, GoNoGo) and result.break_even is None
    assert "loss_at_zero" in warnings(inputs(rt), result)


def test_missing_escort_cost_is_missing_not_zero(terms):
    rt = dict(C_="TEST-MISS", E="ΝΑΙ", F="60.00", days=525, H="31500.00", J="10", K="1", L=None)
    assert analyse(inputs(rt), CLIENT, CONTRACT, terms, PAYMENT_DEDUCTION_RATE) == Missing(("escort_per_day",))


def test_taxi_warnings_always_include_fuel_and_cancellation(terms):
    rt = ROUTES[0]
    got = warnings(inputs(rt), analyse(inputs(rt), CLIENT, CONTRACT, terms, PAYMENT_DEDUCTION_RATE))
    assert got[:2] == ("fuel_no_adjustment", "cancellation_no_compensation")


def test_escort_at_zero_cost_warns():
    rt = dict(ROUTES[0], L="0")
    assert "escort_zero_cost" in warnings(inputs(rt), Missing(()))


def test_performance_guarantee_months_match_workbook(terms):
    from tenderer.sectors.taxi_student_transport.costs import performance_guarantee_months
    assert performance_guarantee_months(terms, CONTRACT) == O_GG_MONTHS


def test_packs_registry_holds_taxi():
    assert "taxi_student_transport" in PACKS.sectors


def _hook_inputs(rt):
    route = {"reference": rt["F"], "days": f"{rt['days']}.0", "budget": rt["H"], "km_per_day": rt["J"],
             "hours_per_day": rt["K"], "escort": rt["E"] == "ΝΑΙ", "escort_per_day": rt["L"]}
    costs = {"fuel_l_per_100km": str(C["cons"]), "fuel_price_per_l": str(C["fuel"]), "wear_per_km": str(C["wear"]),
             "opportunity_per_hour": str(C["opp"]), "extra_insurance_per_year": str(C["ins"]),
             "bank_rate_per_year": str(C["rate"]), "bank_fee_per_guarantee": str(C["fee"]),
             "paid_share": str(C["share"]), "fuel_increase": str(C["scn"])}
    return route, costs, {"school_years": C["years"], "signed_on": C["sign"], "ends_on": C["end"]}


def test_registry_hook_equals_the_oracle(tender):
    hook = PACKS.sectors["taxi_student_transport"].gonogo
    for rt in ROUTES:
        result, warns = hook(*_hook_inputs(rt), tender.offer, PAYMENT_DEDUCTION_RATE)
        assert result.net(0).quantize(D("0.0001")) == o_net(rt, 0).quantize(D("0.0001"))
        assert result.break_even == o_breakeven(rt)
        assert warns[:2] == ("fuel_no_adjustment", "cancellation_no_compensation")


def test_registry_hook_reports_missing_and_refuses_floats(tender):
    hook = PACKS.sectors["taxi_student_transport"].gonogo
    route, costs, contract = _hook_inputs(ROUTES[0])  # escort route
    result, warns = hook({**route, "escort_per_day": None, "km_per_day": ""}, costs, contract, tender.offer,
                         PAYMENT_DEDUCTION_RATE)
    assert (result, warns) == (Missing(("km_per_day", "escort_per_day")), ())
    with pytest.raises(TypeError, match="floats"):
        hook({**route, "reference": 51.18}, costs, contract, tender.offer, PAYMENT_DEDUCTION_RATE)
    with pytest.raises(TypeError, match="date"):
        hook(route, costs, {**contract, "signed_on": "2026-10-15"}, tender.offer, PAYMENT_DEDUCTION_RATE)
