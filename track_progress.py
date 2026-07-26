#!/usr/bin/env python3
"""
Regenerates LEADERBOARD_PROGRESS.md from checkpoints/ and results/.

Runnable standalone:
    python track_progress.py

Also called automatically after each checkpoint save during a leaderboard run.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

TOTAL_SCENARIOS = 48  # generated suite, per_threat=6, seed=0

# Models confirmed complete by external verification (terminal output, chat logs).
# These bypass the results-file check and read metrics from their checkpoint.
CONFIRMED_COMPLETE = {"llama-3.3-70b-versatile"}


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #

def _slug(name: str) -> str:
    return name.replace("/", "_").replace(":", "_")


def _paths(root: str) -> tuple[str, str, str, str]:
    return (
        os.path.join(root, "models", "paper_full.json"),
        os.path.join(root, "checkpoints"),
        os.path.join(root, "results"),
        os.path.join(root, "LEADERBOARD_PROGRESS.md"),
    )


# --------------------------------------------------------------------------- #
# Data readers
# --------------------------------------------------------------------------- #

def _read_checkpoint(name: str, checkpoints_dir: str) -> dict | None:
    path = os.path.join(checkpoints_dir, f"{_slug(name)}.checkpoint.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _find_in_results(name: str, results_dir: str) -> dict | None:
    """Return model entry from a full-suite results file (per_threat>=6, trials>=3)."""
    if not os.path.isdir(results_dir):
        return None
    for fname in sorted(os.listdir(results_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(results_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        meta = data.get("metadata", {})
        if meta.get("per_threat", 0) < 6 or meta.get("trials", 0) < 3:
            continue
        for m in data.get("models", []):
            if m.get("model") == name:
                return m
    return None


def _scorecard(entry: dict) -> dict:
    sc = entry.get("scorecard", {})
    return {
        "asr_none":        sc.get("asr_none"),
        "asr_advisory":    sc.get("asr_advisory"),
        "asr_enforced":    sc.get("asr_enforced"),
        "utility_enforced": sc.get("utility_enforced"),
    }


def _trials_from_checkpoint(ckpt: dict) -> int | None:
    """Top-level 'trials' field written by render_json."""
    return ckpt.get("trials")


def _trials_from_results(entry: dict) -> int | None:
    scenarios = entry.get("scenarios", [])
    if scenarios:
        return scenarios[0].get("n_trials")
    return None


# --------------------------------------------------------------------------- #
# Status determination
# --------------------------------------------------------------------------- #

def _model_status(name: str, checkpoints_dir: str, results_dir: str) -> dict:
    """
    Returns a status dict with keys:
      status   : "done" | "checkpoint-complete" | "in-progress" | "not-started" | "malformed"
      confirmed: bool
      completed: int   (scenarios done so far)
      total    : int   (48)
      trials   : int | None
      scorecard: dict | None
      notes    : str
    """
    confirmed = name in CONFIRMED_COMPLETE
    results_entry = _find_in_results(name, results_dir)

    # --- Confirmed via results file ------------------------------------------
    if results_entry is not None:
        return {
            "status":    "done",
            "confirmed": True,
            "completed": TOTAL_SCENARIOS,
            "total":     TOTAL_SCENARIOS,
            "trials":    _trials_from_results(results_entry),
            "scorecard": _scorecard(results_entry),
            "notes":     "from results file",
        }

    ckpt = _read_checkpoint(name, checkpoints_dir)

    # --- No checkpoint at all -------------------------------------------------
    if ckpt is None:
        return {
            "status":    "not-started",
            "confirmed": False,
            "completed": 0,
            "total":     TOTAL_SCENARIOS,
            "trials":    None,
            "scorecard": None,
            "notes":     "",
        }

    # --- Malformed checkpoint (checkpoint flag not set) -----------------------
    if not ckpt.get("checkpoint", False):
        return {
            "status":    "malformed",
            "confirmed": False,
            "completed": ckpt.get("completed_scenarios", 0),
            "total":     TOTAL_SCENARIOS,
            "trials":    None,
            "scorecard": None,
            "notes":     "checkpoint flag missing — will restart from scratch on next run",
        }

    completed = ckpt.get("completed_scenarios", 0)
    trials    = _trials_from_checkpoint(ckpt)
    sc        = _scorecard(ckpt.get("models", [{}])[0]) if ckpt.get("models") else {}

    # --- All scenarios done in checkpoint ------------------------------------
    if completed >= TOTAL_SCENARIOS:
        status = "done" if confirmed else "checkpoint-complete"
        note   = "confirmed via run log (previous session)" if confirmed else \
                 "all 48 scenarios done; metrics from checkpoint (no formal results file yet)"
        return {
            "status":    status,
            "confirmed": confirmed,
            "completed": completed,
            "total":     TOTAL_SCENARIOS,
            "trials":    trials,
            "scorecard": sc,
            "notes":     note,
        }

    # --- Partial checkpoint --------------------------------------------------
    return {
        "status":    "in-progress",
        "confirmed": False,
        "completed": completed,
        "total":     TOTAL_SCENARIOS,
        "trials":    trials,
        "scorecard": None,
        "notes":     "",
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_STATUS_ICON = {
    "done":                "✅",
    "checkpoint-complete": "🔶",
    "in-progress":         "🔄",
    "not-started":         "⬜",
    "malformed":           "❌",
}

_STATUS_LABEL = {
    "done":                "Done",
    "checkpoint-complete": "Checkpoint complete*",
    "in-progress":         "In progress",
    "not-started":         "Not started",
    "malformed":           "Malformed checkpoint",
}


def _pct(v) -> str:
    return f"{v:.0%}" if v is not None else "—"


def render_md(models: list[dict], statuses: dict[str, dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    n_done    = sum(1 for s in statuses.values() if s["status"] in ("done", "checkpoint-complete"))
    n_prog    = sum(1 for s in statuses.values() if s["status"] == "in-progress")
    n_pending = sum(1 for s in statuses.values() if s["status"] in ("not-started", "malformed"))
    total     = len(models)

    lines = [
        "# FinAgent Red-Team — Leaderboard Progress",
        "",
        f"_Last updated: {now}_",
        "",
        f"**{n_done}/{total} complete** | {n_prog} in progress | {n_pending} pending",
        "",
        "## Model Status",
        "",
        "| # | Model | Provider | Tier | Status | Progress | Trials"
        " | ASR none | ASR adv | ASR enf | Utility | Notes |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for i, spec in enumerate(models, 1):
        name     = spec["name"]
        provider = spec.get("_provider", "—")
        tier     = spec.get("_tier", "—")
        s        = statuses[name]
        icon     = _STATUS_ICON[s["status"]]
        label    = _STATUS_LABEL[s["status"]]
        progress = f"{s['completed']}/{s['total']}"
        trials   = str(s["trials"]) if s["trials"] is not None else "—"

        sc = s.get("scorecard") or {}
        if s["status"] in ("done", "checkpoint-complete") and sc:
            asr_none = _pct(sc.get("asr_none"))
            asr_adv  = _pct(sc.get("asr_advisory"))
            asr_enf  = _pct(sc.get("asr_enforced"))
            utility  = _pct(sc.get("utility_enforced"))
        else:
            asr_none = asr_adv = asr_enf = utility = "—"

        lines.append(
            f"| {i} | `{name}` | {provider} | {tier} "
            f"| {icon} {label} "
            f"| {progress} | {trials} "
            f"| {asr_none} | {asr_adv} | {asr_enf} | {utility} "
            f"| {s['notes']} |"
        )

    lines += [
        "",
        "> \\* **Checkpoint-complete** = all 48 scenarios finished and saved in a checkpoint file,"
        " but not yet written to a formal `results/` file. Metrics are from the checkpoint scorecard.",
        "",
        "## Legend",
        "",
        "| Icon | Meaning |",
        "|---|---|",
        "| ✅ | Complete and confirmed |",
        "| 🔶 | All scenarios done (checkpoint only; awaiting formal results file) |",
        "| 🔄 | Run currently in progress |",
        "| ⬜ | Not started |",
        "| ❌ | Malformed checkpoint — will restart from scratch on next run |",
        "",
        "## Target Configuration",
        "",
        "| Parameter | Value |",
        "|---|---|",
        "| Config | `models/paper_full.json` (12 models) |",
        "| Suite | generated (`--per-threat 6`, `--seed 0`) |",
        "| Total scenarios | 48 (42 attack + 6 benign) |",
        "| Trials per scenario | 3 |",
        "| Max steps | 10 |",
        "",
        "## Confirmed Results",
        "",
        "| Model | ASR none | ASR advisory | ASR enforced | Utility | Trials | Source |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for spec in models:
        name = spec["name"]
        s    = statuses[name]
        if s["status"] in ("done", "checkpoint-complete") and s.get("scorecard"):
            sc     = s["scorecard"]
            source = s["notes"]
            lines.append(
                f"| `{name}` "
                f"| {_pct(sc.get('asr_none'))} "
                f"| {_pct(sc.get('asr_advisory'))} "
                f"| {_pct(sc.get('asr_enforced'))} "
                f"| {_pct(sc.get('utility_enforced'))} "
                f"| {s['trials'] or '—'} "
                f"| {source} |"
            )

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def update_progress_md(root: str | None = None) -> None:
    """Regenerate LEADERBOARD_PROGRESS.md. Safe to call from any context."""
    root = root or PROJECT_ROOT
    models_config, checkpoints_dir, results_dir, output_md = _paths(root)

    try:
        with open(models_config, encoding="utf-8") as f:
            models = json.load(f).get("models", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return

    statuses = {
        spec["name"]: _model_status(spec["name"], checkpoints_dir, results_dir)
        for spec in models
    }
    md = render_md(models, statuses)
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("\n")


def main() -> None:
    root = PROJECT_ROOT
    update_progress_md(root)
    output_md = _paths(root)[3]
    print(f"Updated {output_md}")


if __name__ == "__main__":
    main()
