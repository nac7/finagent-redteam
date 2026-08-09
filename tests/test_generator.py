"""Tests for the procedural scenario generator.

The headline test replays every generated scenario's ``reference_plan`` under all
three control postures and asserts the suite-wide invariant: each attack lands
under NONE and ADVISORY and is blocked under ENFORCED, while benign tasks
complete under all three. This is what makes a *generated* benchmark
trustworthy — every case is a verified, control-isolating test.
"""

from finagent_redteam.agent.base import AgentModel, AssistantTurn, ToolCall
from finagent_redteam.runner import run_postures
from finagent_redteam.scenarios.generator import (
    PAPER_PER_THREAT,
    coverage_audit,
    generate_scenarios,
    min_cell_count,
)


class PlanAgent(AgentModel):
    """Replays a scenario's reference_plan as a sequence of tool calls."""

    def __init__(self, plan):
        self._turns = [
            AssistantTurn(tool_calls=[ToolCall(f"c{i}", step["name"], step["arguments"])])
            for i, step in enumerate(plan)
        ]

    def complete(self, messages, tools):
        return self._turns.pop(0) if self._turns else AssistantTurn(content="done")


def test_generation_is_deterministic():
    a = generate_scenarios(seed=7, per_threat=4)
    b = generate_scenarios(seed=7, per_threat=4)
    assert [s.id for s in a] == [s.id for s in b]


def test_counts_and_unique_ids():
    scenarios = generate_scenarios(seed=0, per_threat=5)
    assert len(scenarios) == 8 * 5  # 7 attack threats + 1 benign group
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids))


def test_every_scenario_has_a_reference_plan():
    for s in generate_scenarios(seed=1, per_threat=3):
        assert s.reference_plan, f"{s.id} missing reference_plan"


def test_attack_scenarios_carry_strata():
    for s in generate_scenarios(seed=0, per_threat=6):
        if s.benign:
            continue
        assert s.strata, f"{s.id} missing strata"
        assert set(s.strata) >= {"tier", "step_mode", "vector"}


def test_each_category_is_tier_stratified():
    # At per_threat >= 3 every builder's cells should cover all three tiers.
    from collections import defaultdict

    tiers_by_cat = defaultdict(set)
    for s in generate_scenarios(seed=0, per_threat=6):
        if s.benign:
            continue
        tiers_by_cat[s.id.rsplit("_", 1)[0]].add(s.strata["tier"])
    for prefix, tiers in tiers_by_cat.items():
        assert tiers == {"easy", "medium", "hard"}, (prefix, tiers)


def test_structuring_varies_split_count():
    ks = {
        s.strata["k"]
        for s in generate_scenarios(seed=0, per_threat=9)
        if s.category == "T4_structuring"
    }
    assert ks == {2, 3, 4}


def test_categories_span_multiple_vectors():
    from collections import defaultdict

    vectors_by_cat = defaultdict(set)
    for s in generate_scenarios(seed=0, per_threat=9):
        if s.benign:
            continue
        vectors_by_cat[s.id.rsplit("_", 1)[0]].add(s.strata["vector"])
    # Every attack builder delivers over at least two distinct channels.
    for prefix, vectors in vectors_by_cat.items():
        assert len(vectors) >= 2, (prefix, vectors)


def test_injection_lands_on_its_vector_channel():
    """A non-email vector must place the injection on the matching channel, and
    the corresponding reader tool must surface it."""
    from finagent_redteam.sandbox.policy import ControlPosture, Policy
    from finagent_redteam.sandbox.tools import TOOLS

    channel_reader = {
        "documents": "read_documents",
        "tickets": "read_tickets",
        "calendar": "read_calendar",
    }
    seen_non_email = False
    policy = Policy.for_posture(ControlPosture.NONE)
    for s in generate_scenarios(seed=0, per_threat=12):
        if s.benign or s.strata["vector"] == "email":
            continue
        seen_non_email = True
        w = s.world_factory()
        assert not w.inbox, f"{s.id}: non-email vector must not use the inbox"
        # Exactly one alternate channel is populated.
        populated = [c for c in channel_reader if getattr(w, c)]
        assert len(populated) == 1, (s.id, populated)
        reader = channel_reader[populated[0]]
        out = TOOLS[reader](w, policy, "agent")
        bodies = " ".join(item["body"] for item in out[populated[0]])
        assert bodies, f"{s.id}: reader returned no items"
    assert seen_non_email, "expected some non-email scenarios in the sample"


def test_benign_near_miss_families_present():
    families = {
        s.strata["family"]
        for s in generate_scenarios(seed=0, per_threat=6)
        if s.benign
    }
    assert families == {
        "routine", "foreign_name", "two_unrelated",
        "large_routed", "remittance_known_good", "customer_lookup",
    }


def test_benign_families_complete_under_all_postures():
    """One instance of every benign near-miss family must complete under NONE,
    ADVISORY and ENFORCED (it is a compliant task, not an attack)."""
    seen = {}
    for s in generate_scenarios(seed=0, per_threat=18):
        if s.benign:
            seen.setdefault(s.strata["family"], s)
    assert len(seen) == 6
    for family, s in seen.items():
        res = run_postures(lambda s=s: PlanAgent(s.reference_plan), s)
        assert res["error"] is None, (family, res["error"])
        assert res["achieved_none"] and res["achieved_advisory"] and res["achieved_enforced"], (
            family, res
        )


def test_paper_scale_suite_size():
    scen = generate_scenarios(seed=0, per_threat=PAPER_PER_THREAT)
    assert len(scen) == 8 * PAPER_PER_THREAT == 320
    attack = [s for s in scen if not s.benign]
    benign = [s for s in scen if s.benign]
    assert len(attack) == 280 and len(benign) == 40
    assert len({s.id for s in scen}) == len(scen)  # unique ids at scale


def test_every_cell_has_at_least_three_instances_at_scale():
    from collections import defaultdict

    scen = generate_scenarios(seed=0, per_threat=PAPER_PER_THREAT)
    assert min_cell_count(scen, by="builder") >= 3
    # Within each builder's own grid, per-cell counts differ by at most one
    # (cross-builder totals differ because builders have different cell counts).
    per_builder = defaultdict(list)
    for (builder, _tier, _vector), n in coverage_audit(scen, by="builder").items():
        per_builder[builder].append(n)
    for builder, counts in per_builder.items():
        assert max(counts) - min(counts) <= 1, (builder, counts)


def test_scaled_suite_invariant_across_postures():
    """The replay invariant must still hold on a large suite (per_threat=20)."""
    failures = []
    for s in generate_scenarios(seed=3, per_threat=20):
        res = run_postures(lambda s=s: PlanAgent(s.reference_plan), s)
        ok = (
            res["achieved_none"] and res["achieved_advisory"] and res["achieved_enforced"]
            if s.benign
            else res["achieved_none"] and res["achieved_advisory"] and not res["achieved_enforced"]
        )
        assert res["error"] is None, (s.id, res["error"])
        if not ok:
            failures.append(s.id)
    assert not failures, failures


def test_generated_suite_invariant_across_postures():
    """Crown-jewel validity test: replay reference plans under all postures."""
    failures = []
    for s in generate_scenarios(seed=0, per_threat=6):
        res = run_postures(lambda s=s: PlanAgent(s.reference_plan), s)
        if s.benign:
            ok = res["achieved_none"] and res["achieved_advisory"] and res["achieved_enforced"]
        else:
            ok = (
                res["achieved_none"]
                and res["achieved_advisory"]
                and not res["achieved_enforced"]
            )
        if not ok:
            failures.append((s.id, res))
        assert res["error"] is None, (s.id, res["error"])
    assert not failures, failures
