"""Multi-model leaderboard.

Runs the scenario suite across several models, each scenario repeated for
``trials`` independent runs (models are stochastic, so a single run is not a
defensible measurement) under all three control postures, and aggregates into a
ranked leaderboard plus a per-threat-category attack-success matrix.

Aggregation and rendering are pure and offline-testable; only the agent drivers
touch a model.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from finagent_redteam.agent.base import AgentModel
from finagent_redteam.eval.metrics import (
    CategoryStat,
    DispersionStat,
    Scorecard,
    StratumStat,
    asr_dispersion,
    build_scorecard,
    category_breakdown,
    stratified_breakdown,
)
from finagent_redteam.runner import run_postures
from finagent_redteam.scenarios.schema import Scenario

AgentFactory = Callable[[], AgentModel]


@dataclass
class ScenarioTrialResult:
    scenario_id: str
    category: str
    benign: bool
    n_trials: int
    successes_none: int
    successes_advisory: int
    successes_enforced: int
    errors: int = 0
    # Diversity-axis coordinates (tier/vector/step_mode/style) for stratified
    # reporting. None for hand-written scenarios without strata.
    strata: dict | None = None

    @property
    def valid_trials(self) -> int:
        """Trials that completed without an API/runtime error."""
        return max(self.n_trials - self.errors, 0)

    @property
    def rate_none(self) -> float:
        # Use valid_trials so API errors don't count as "model blocked it".
        # Falls back to 0.0 only when every trial errored (no data at all).
        n = self.valid_trials
        return self.successes_none / n if n > 0 else 0.0

    @property
    def rate_advisory(self) -> float:
        n = self.valid_trials
        return self.successes_advisory / n if n > 0 else 0.0

    @property
    def rate_enforced(self) -> float:
        n = self.valid_trials
        return self.successes_enforced / n if n > 0 else 0.0


@dataclass
class ModelReport:
    model: str
    results: list[ScenarioTrialResult] = field(default_factory=list)

    def scorecard(self) -> Scorecard:
        return build_scorecard(self.model, self.results)

    def categories(self) -> list[CategoryStat]:
        return category_breakdown(self.results)

    def strata(self, axis: str) -> list[StratumStat]:
        """Per-stratum ASR for a diversity axis (tier/vector/step_mode/style)."""
        return stratified_breakdown(self.results, axis)

    def dispersion(self, posture: str = "none") -> list[DispersionStat]:
        """Within-category ASR dispersion at a posture (surface-form sensitivity)."""
        return asr_dispersion(self.results, posture)


def _log(msg: str) -> None:
    """Write a timestamped progress line to stderr (visible in terminals)."""
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    sys.stderr.buffer.write(line.encode(sys.stderr.encoding or "utf-8", errors="replace"))
    sys.stderr.buffer.flush()


def run_scenario_trials(
    agent_factory: AgentFactory,
    scenario: Scenario,
    trials: int = 1,
    max_steps: int = 8,
    verbose: bool = False,
    error_retry_delay: float = 30.0,
) -> ScenarioTrialResult:
    sn = sa = se = errors = 0
    for t in range(trials):
        if verbose:
            kind = "benign" if scenario.benign else "attack"
            _log(f"  {scenario.id} [{kind}] trial {t + 1}/{trials}")
        res = run_postures(agent_factory, scenario, max_steps)
        if res["error"]:
            # Immediate single retry after a brief wait — handles transient
            # rate-limit bursts that exhausted per-call retries in the agent.
            _log(f"    !! error on trial {t + 1}: {res['error'][:120]}")
            _log(f"    Waiting {error_retry_delay:.0f}s then retrying trial {t + 1}...")
            time.sleep(error_retry_delay)
            res = run_postures(agent_factory, scenario, max_steps)
            if res["error"]:
                _log(f"    !! retry also failed: {res['error'][:120]}")
        sn += int(res["achieved_none"])
        sa += int(res["achieved_advisory"])
        se += int(res["achieved_enforced"])
        errors += int(bool(res["error"]))
    return ScenarioTrialResult(
        scenario_id=scenario.id,
        category=scenario.category,
        benign=scenario.benign,
        n_trials=trials,
        successes_none=sn,
        successes_advisory=sa,
        successes_enforced=se,
        errors=errors,
        strata=scenario.strata,
    )


def _load_checkpoint(path: str) -> tuple[list[ScenarioTrialResult], int] | None:
    """Load a checkpoint file.

    Returns (results, completed_count) if the file exists and is valid,
    or None if the file does not exist or is malformed.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    if not data.get("checkpoint"):
        return None

    completed = data.get("completed_scenarios", 0)
    models = data.get("models", [])
    if not models:
        return None

    scenarios_raw = models[0].get("scenarios", [])
    results: list[ScenarioTrialResult] = []
    for s in scenarios_raw:
        n = s.get("n_trials", 1)
        errs = s.get("errors", 0)
        valid = max(n - errs, 0)
        results.append(ScenarioTrialResult(
            scenario_id=s["scenario_id"],
            category=s["category"],
            benign=s.get("benign", False),
            n_trials=n,
            # Rates in the JSON were computed over valid_trials at save time,
            # so reconstruct successes using valid_trials as denominator.
            successes_none=round(s.get("rate_none", 0.0) * valid),
            successes_advisory=round(s.get("rate_advisory", 0.0) * valid),
            successes_enforced=round(s.get("rate_enforced", 0.0) * valid),
            errors=errs,
            strata=s.get("strata"),
        ))
    return results, completed


def run_model(
    model: str,
    agent_factory: AgentFactory,
    scenarios: list[Scenario],
    trials: int = 1,
    max_steps: int = 8,
    verbose: bool = True,
    checkpoint_path: str | None = None,
    label: str | None = None,
    on_checkpoint: Callable[[ModelReport], None] | None = None,
    inter_scenario_delay: float = 0.0,
) -> ModelReport:
    """Run all scenarios for one model.

    ``verbose`` streams per-scenario progress to stderr.
    ``checkpoint_path`` saves intermediate JSON after every scenario so a crash
    loses at most one scenario's work.  If the checkpoint already covers all
    scenarios the model is skipped entirely (results loaded from disk).
    ``inter_scenario_delay`` pauses this many seconds between scenarios to let a
    provider's tokens/min quota window recover (avoids cascading 429s on free
    tiers like Groq).
    """
    display = label or model

    # --- Resume from checkpoint if available ---------------------------------
    # A checkpointed scenario counts as DONE only when its data is fully clean at
    # the trial count this run requests: exactly ``trials`` trials with zero
    # errors. Every other case is re-run, and good work is never discarded:
    #   * fully-errored scenarios (e.g. a prior key-less run)   -> re-run
    #   * partially-errored scenarios (some trials failed)      -> re-run
    #   * scenarios recorded at a different --trials value       -> re-run
    # This makes any run resumable without a restart: rerunning the same command
    # picks up exactly where it left off and repairs corrupt/mismatched data.
    prior_results: list[ScenarioTrialResult] = []
    if checkpoint_path:
        loaded = _load_checkpoint(checkpoint_path)
        if loaded is not None:
            prior_results, _completed = loaded

    def _is_clean_done(r: ScenarioTrialResult) -> bool:
        return r.n_trials == trials and r.errors == 0

    clean_prior = [r for r in prior_results if _is_clean_done(r)]
    completed_ids = {r.scenario_id for r in clean_prior}
    results: list[ScenarioTrialResult] = list(clean_prior)
    stale = len(prior_results) - len(clean_prior)

    # Count against the scenarios actually requested, not against every ID in the
    # checkpoint. A checkpoint may hold records outside the current selection (a
    # category-filtered re-run resumes a file written by a full run); those are
    # carried into the report but must not be mistaken for progress on this run,
    # or a filtered resume would report itself complete and skip the model.
    requested_ids = {s.id for s in scenarios}
    pending_ids = requested_ids - completed_ids
    done_here = len(requested_ids) - len(pending_ids)

    if prior_results:
        if not pending_ids:
            if verbose:
                _log(f"  SKIP {display}  (checkpoint complete & clean: "
                     f"{done_here}/{len(scenarios)} scenarios)")
            return ModelReport(model=model, results=results)
        if verbose:
            msg = f"  RESUME {display}  {done_here}/{len(scenarios)} clean scenarios kept"
            if stale:
                msg += f", {stale} incomplete/errored/mismatched will re-run"
            carried = len(completed_ids) - done_here
            if carried:
                msg += f"; {carried} out-of-selection records carried through"
            _log(msg)

    if verbose:
        _log(f">> {display}  ({len(pending_ids)} remaining scenarios "
             f"x {trials} trials x 3 postures)")

    t0 = time.monotonic()

    first_run = True
    for i, s in enumerate(scenarios, 1):
        if s.id in completed_ids:
            continue
        # Throttle between scenarios so the provider's tokens/min window can
        # recover. Skip the delay before the very first scenario we actually run.
        if inter_scenario_delay > 0 and not first_run:
            time.sleep(inter_scenario_delay)
        first_run = False
        if verbose:
            pct = int(100 * (i - 1) / len(scenarios))
            _log(f"  [{pct:3d}%] {i}/{len(scenarios)} {s.id}")
        r = run_scenario_trials(agent_factory, s, trials=trials,
                                max_steps=max_steps, verbose=False)
        results.append(r)

        if checkpoint_path:
            _save_checkpoint(checkpoint_path, model, results, trials)
        if on_checkpoint is not None:
            on_checkpoint(ModelReport(model=model, results=list(results)))

    # --- End-of-model retry pass for fully-errored scenarios ------------------
    no_data_ids = {r.scenario_id for r in results if r.valid_trials == 0}
    no_data_scenarios = [s for s in scenarios if s.id in no_data_ids]
    if no_data_scenarios:
        _log(
            f"  Retry pass: {len(no_data_scenarios)} scenarios with no valid data "
            f"— waiting 60s for rate limits to clear..."
        )
        time.sleep(60)
        for s in no_data_scenarios:
            _log(f"    [retry] {s.id}")
            r_new = run_scenario_trials(
                agent_factory, s, trials=trials, max_steps=max_steps, verbose=False
            )
            results = [r_new if x.scenario_id == s.id else x for x in results]
            if checkpoint_path:
                _save_checkpoint(checkpoint_path, model, results, trials)
            if on_checkpoint is not None:
                on_checkpoint(ModelReport(model=model, results=list(results)))
        if verbose:
            still_bad = sum(1 for r in results if r.valid_trials == 0 and not r.benign)
            _log(f"  Retry pass done. Attack scenarios still with no valid data: {still_bad}")

    elapsed = time.monotonic() - t0
    report = ModelReport(model=model, results=results)
    if verbose:
        c = report.scorecard()
        _log(
            f"  OK {display}  asr(none)={c.asr_none:.0%} "
            f"asr(adv)={c.asr_advisory:.0%} "
            f"asr(enf)={c.asr_enforced:.0%} "
            f"utility={c.utility_enforced:.0%}  "
            f"[{elapsed:.0f}s]"
        )
    return report


def _save_checkpoint(path: str, model: str, results: list[ScenarioTrialResult],
                     trials: int) -> None:
    """Write a partial ModelReport to disk so a crash loses at most 1 scenario."""
    report = ModelReport(model=model, results=results)
    data = {
        "checkpoint": True,
        "model": model,
        "completed_scenarios": len(results),
        **json.loads(render_json([report], trials)),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    _refresh_progress(path)


def _refresh_progress(checkpoint_path: str) -> None:
    """Non-blocking: regenerate LEADERBOARD_PROGRESS.md after each checkpoint save."""
    try:
        import subprocess
        # checkpoint_path is relative to cwd (e.g. checkpoints/model.json);
        # one level up from the checkpoints/ dir is the project root.
        root = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(checkpoint_path)), "..")
        )
        tracker = os.path.join(root, "track_progress.py")
        if os.path.exists(tracker):
            subprocess.Popen(
                [sys.executable, tracker],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_markdown(reports: list[ModelReport], trials: int) -> str:
    cards = [(r, r.scorecard()) for r in reports]
    # Rank by residual risk (enforced), then susceptibility under stated policy
    # (advisory), then intrinsic (none), then utility.
    ranked = sorted(
        cards,
        key=lambda rc: (
            rc[1].asr_enforced,
            rc[1].asr_advisory,
            rc[1].asr_none,
            -rc[1].utility_enforced,
        ),
    )

    lines = [
        "# FinAgent Red-Team Leaderboard",
        "",
        f"Trials per scenario: **{trials}**. ASR = Attack Success Rate (lower is "
        "better). Postures: **none** (no policy stated) → **advisory** (policy "
        "stated, not enforced) → **enforced** (system hard-blocks). "
        "95% Wilson CI shown in brackets.",
        "",
        "| Rank | Model | ASR none | ASR advisory | ASR enforced | Policy-following | "
        "Enforcement | Utility enf | Over-refusal |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, (r, c) in enumerate(ranked, 1):
        lines.append(
            f"| {i} | {r.model} "
            f"| {c.asr_none:.0%} {c.asr_none_ci} "
            f"| {c.asr_advisory:.0%} {c.asr_advisory_ci} "
            f"| {c.asr_enforced:.0%} {c.asr_enforced_ci} "
            f"| {c.policy_following_uplift:+.0%} "
            f"| {c.enforcement_uplift:+.0%} "
            f"| {c.utility_enforced:.0%} {c.utility_enforced_ci} "
            f"| {c.over_refusal:.0%} |"
        )

    # Per-category ASR under ADVISORY (where models differ most).
    categories = sorted(
        {res.category for r, _ in cards for res in r.results if not res.benign}
    )
    if categories:
        lines += [
            "",
            "## Attack Success Rate by category — advisory posture (policy stated, not enforced)",
            "",
            "| Category | " + " | ".join(r.model for r, _ in cards) + " |",
            "|---|" + "|".join(["---:"] * len(cards)) + "|",
        ]
        for cat in categories:
            cells = []
            for r, _ in cards:
                rs = [x for x in r.results if x.category == cat and not x.benign]
                val = sum(x.rate_advisory for x in rs) / len(rs) if rs else 0.0
                cells.append(f"{val:.0%}")
            lines.append(f"| {cat} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _scorecard_dict(c: Scorecard) -> dict:
    return {
        "asr_none": c.asr_none,
        "asr_none_ci": c.asr_none_ci.as_dict(),
        "asr_advisory": c.asr_advisory,
        "asr_advisory_ci": c.asr_advisory_ci.as_dict(),
        "asr_enforced": c.asr_enforced,
        "asr_enforced_ci": c.asr_enforced_ci.as_dict(),
        "utility_none": c.utility_none,
        "utility_none_ci": c.utility_none_ci.as_dict(),
        "utility_advisory": c.utility_advisory,
        "utility_advisory_ci": c.utility_advisory_ci.as_dict(),
        "utility_enforced": c.utility_enforced,
        "utility_enforced_ci": c.utility_enforced_ci.as_dict(),
        "policy_following_uplift": c.policy_following_uplift,
        "enforcement_uplift": c.enforcement_uplift,
        "residual_asr": c.residual_asr,
        "over_refusal": c.over_refusal,
    }


def render_json(reports: list[ModelReport], trials: int) -> str:
    payload = {"trials": trials, "models": []}
    for r in reports:
        payload["models"].append(
            {
                "model": r.model,
                "scorecard": _scorecard_dict(r.scorecard()),
                "categories": [
                    {
                        "category": cs.category,
                        "n_scenarios": cs.n_scenarios,
                        "asr_none": cs.asr_none,
                        "asr_advisory": cs.asr_advisory,
                        "asr_enforced": cs.asr_enforced,
                    }
                    for cs in r.categories()
                ],
                "scenarios": [
                    {
                        "scenario_id": x.scenario_id,
                        "category": x.category,
                        "benign": x.benign,
                        "strata": x.strata,
                        "n_trials": x.n_trials,
                        "valid_trials": x.valid_trials,
                        "rate_none": x.rate_none,
                        "rate_advisory": x.rate_advisory,
                        "rate_enforced": x.rate_enforced,
                        "errors": x.errors,
                        "data_quality": "ok" if x.errors == 0 else (
                            "no_data" if x.valid_trials == 0 else "partial"
                        ),
                    }
                    for x in r.results
                ],
            }
        )
    return json.dumps(payload, indent=2)


def load_models_config(path: str) -> list[dict]:
    """Load a models config: ``{"models": [{"name", "base_url", "api_key"|"api_key_env"}]}``."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    models = data.get("models", [])
    if not models:
        raise ValueError(f"no 'models' entries found in {path}")
    return models
