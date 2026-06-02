# API Reference

## Core classes

### `Scenario`
```python
@dataclass
class Scenario:
    id: str
    category: str           # one of THREAT_CATEGORIES
    description: str
    world_factory: Callable[[], World]
    user_task: str
    attack_goal: AttackGoal | None    # for attack scenarios
    success_goal: AttackGoal | None   # for benign scenarios
    benign: bool = False
    reference_plan: list[dict] | None = None
```

### `ControlPosture`
```python
class ControlPosture(Enum):
    NONE     = "none"      # no policy stated
    ADVISORY = "advisory"  # policy stated, not enforced
    ENFORCED = "enforced"  # system hard-blocks
```

### `Scorecard`
```python
@dataclass
class Scorecard:
    asr_none: float
    asr_advisory: float
    asr_enforced: float
    utility_none: float
    utility_advisory: float
    utility_enforced: float

    @property
    def policy_following_uplift(self) -> float: ...   # asr_none - asr_advisory
    @property
    def enforcement_uplift(self) -> float: ...        # asr_advisory - asr_enforced
    @property
    def residual_asr(self) -> float: ...              # asr_enforced
    @property
    def over_refusal(self) -> float: ...              # utility_none - utility_enforced
```

## Key functions

### `run_postures`
```python
def run_postures(
    agent_factory: Callable[[], AgentModel],
    scenario: Scenario,
    max_steps: int = 8,
) -> dict:
    """Run one scenario under all three postures with a fresh agent per run."""
```

### `generate_scenarios`
```python
def generate_scenarios(seed: int = 0, per_threat: int = 6) -> list[Scenario]:
    """Produce a seeded, deterministic suite of generated scenarios."""
```

### `run_model`
```python
def run_model(
    model: str,
    agent_factory: Callable[[], AgentModel],
    scenarios: list[Scenario],
    trials: int = 1,
    max_steps: int = 8,
) -> ModelReport:
    """Run the full suite across all postures and trials for one model."""
```
