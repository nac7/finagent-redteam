"""Tests for stratified ASR breakdowns and within-category dispersion."""

from finagent_redteam.eval.metrics import asr_dispersion, stratified_breakdown
from finagent_redteam.leaderboard import ModelReport, ScenarioTrialResult


def _r(sid, cat, benign, n, sn, sa, se, strata):
    return ScenarioTrialResult(
        scenario_id=sid, category=cat, benign=benign, n_trials=n,
        successes_none=sn, successes_advisory=sa, successes_enforced=se,
        strata=strata,
    )


def _sample():
    # Two tiers, differing enforced ASR; benign row must be ignored.
    return [
        _r("a", "T2", False, 10, 10, 8, 2, {"tier": "easy", "vector": "email", "step_mode": "single"}),
        _r("b", "T2", False, 10, 6, 4, 0, {"tier": "hard", "vector": "chat_message", "step_mode": "single"}),
        _r("c", "T3", False, 10, 10, 10, 5, {"tier": "hard", "vector": "email", "step_mode": "single"}),
        _r("z", "BENIGN", True, 10, 10, 10, 10, {"tier": "n/a", "vector": "email", "step_mode": "single"}),
    ]


def test_stratified_breakdown_by_tier_ignores_benign_and_pools():
    rows = {s.value: s for s in stratified_breakdown(_sample(), "tier")}
    assert set(rows) == {"easy", "hard"}  # benign 'n/a' tier excluded
    assert rows["easy"].n_scenarios == 1
    assert rows["hard"].n_scenarios == 2
    # easy enforced ASR = 2/10 = 0.2; hard enforced = mean(0/10, 5/10) = 0.25
    assert abs(rows["easy"].asr_enforced - 0.2) < 1e-9
    assert abs(rows["hard"].asr_enforced - 0.25) < 1e-9
    # Wilson CI is a proper interval around the pooled rate.
    assert rows["easy"].asr_none_ci.lower <= 1.0 >= rows["easy"].asr_none_ci.upper - 1e-9


def test_stratified_breakdown_by_vector():
    rows = {s.value: s for s in stratified_breakdown(_sample(), "vector")}
    assert set(rows) == {"email", "chat_message"}
    assert rows["email"].n_scenarios == 2  # a (T2) + c (T3)


def test_stratified_breakdown_skips_results_without_strata():
    res = [_r("a", "T2", False, 5, 5, 5, 0, None)]
    assert stratified_breakdown(res, "tier") == []


def test_asr_dispersion_reports_spread_across_instances():
    disp = {d.category: d for d in asr_dispersion(_sample(), posture="enforced")}
    assert set(disp) == {"T2", "T3"}
    t2 = disp["T2"]
    # T2 enforced rates: 0.2 and 0.0 -> mean 0.1, spread 0.2, sd 0.1
    assert t2.n_scenarios == 2
    assert abs(t2.mean_asr - 0.1) < 1e-9
    assert abs(t2.spread - 0.2) < 1e-9
    assert abs(t2.sd_asr - 0.1) < 1e-9


def test_model_report_exposes_strata_and_dispersion():
    mr = ModelReport(model="m", results=_sample())
    assert {s.value for s in mr.strata("tier")} == {"easy", "hard"}
    assert {d.category for d in mr.dispersion("none")} == {"T2", "T3"}
