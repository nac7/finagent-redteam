# Leaderboard

!!! note "Coming soon"
    The public multi-model leaderboard will be published here after the v0.2.0
    release. See [examples/sample_leaderboard.md](https://github.com/nac7/finagent-redteam/blob/main/examples/sample_leaderboard.md)
    for the output format.

## Running your own leaderboard

```bash
pip install finagent-redteam[agent]

# Create a models config (see examples/models.example.json)
finagent-redteam \
  --models-config models.json \
  --trials 5 \
  --temperature 0.7 \
  --suite generated \
  --per-threat 10 \
  --json leaderboard.json
```

## Submitting results

To include your model results in the public leaderboard, open a pull request
adding a results JSON to `results/<model-name>-<date>.json`. The file must
include the model name, API version or snapshot date, temperature, seed, and
trial count. See [CONTRIBUTING.md](https://github.com/nac7/finagent-redteam/blob/main/CONTRIBUTING.md)
for the full submission guide.
