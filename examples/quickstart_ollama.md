# Quickstart: Run the leaderboard locally with Ollama (free, no API key)

This guide runs FinAgent Red-Team against 6 open models on your laptop.
No API key, no cloud cost. Total disk: ~30 GB. Total time: ~2 hours (CPU).

---

## Step 1 — Install Ollama

Download from https://ollama.com and install.

Verify it's running:
```bash
ollama list
```

## Step 2 — Pull the models

```bash
ollama pull llama3.1:8b        # 4.7 GB
ollama pull qwen3:8b           # 5.2 GB
ollama pull mistral:7b         # 4.1 GB
ollama pull gemma3:9b          # 5.9 GB
ollama pull phi4:14b           # 8.9 GB
ollama pull deepseek-r1:8b     # 4.9 GB
```

Ollama serves an OpenAI-compatible API at `http://localhost:11434/v1` automatically.

## Step 3 — Install the benchmark

```bash
git clone https://github.com/nac7/finagent-redteam.git
cd finagent-redteam
pip install -e ".[agent]"
pytest -q          # 41 tests should pass instantly, no model needed
```

## Step 4 — Run the leaderboard

```bash
python run_leaderboard.py \
    --config models/ollama_local.json \
    --trials 5 \
    --per-threat 6 \
    --temperature 0.7
```

Results land in `results/YYYY-MM-DD_generated-p6_5trials.json` and `.md`.

Progress is printed to the terminal per scenario in real time.
Checkpoints are saved to `checkpoints/` after every scenario — so you can
safely Ctrl+C and re-run; re-add `--models <name>` to resume a specific model.

## Step 5 — Smoke test with one model first

Before the full run, verify the pipeline works end-to-end:

```bash
python run_leaderboard.py \
    --config models/ollama_local.json \
    --models llama3.1:8b \
    --per-threat 2 --trials 1 \
    --temperature 0.7
```

This runs 24 scenarios × 3 postures × 1 trial = 72 agent calls (~5 min on a CPU laptop).

## Expected output

```
[10:32:01] Suite: generated-p6  |  42 attack + 6 benign = 48 scenarios
[10:32:01] Trials: 5  |  Total agent calls per model: 720
[10:32:01] Models: ['llama3.1:8b', 'qwen3:8b', ...]
[10:32:01] ── Model 1/6: llama3.1:8b
[10:32:01]   [  0%] 1/48 gen_unauth_00
[10:32:08]   [  2%] 2/48 gen_unauth_01
  ...
[10:58:44]   ✓ llama3.1:8b  asr(none)=74%  asr(adv)=41%  asr(enf)=0%  utility=100%  [1603s]
```

## Adding API models to the mix

Set your API keys and add cloud models to the run:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Edit models/paper_full.json to your taste, then:
python run_leaderboard.py --config models/paper_full.json --trials 5
```

Estimated cost for the full 12-model paper run at `--per-threat 6 --trials 5`:
~$30–80 in API credits (GPT-4o + Claude Sonnet are the most expensive).
GPT-4o-mini and Haiku are essentially free at this scale.
