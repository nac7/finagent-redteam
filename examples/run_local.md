# Running FinAgent Red-Team against a local model

You don't need a GPU or a cloud key to *develop* on this benchmark — `pytest`
exercises the whole pipeline offline. To score a real model, point the CLI at any
OpenAI-compatible, tool-calling endpoint.

## Option A — Ollama (easiest on a laptop)

```bash
# 1. Install Ollama and pull a tool-calling model
ollama pull llama3.1

# 2. Ollama exposes an OpenAI-compatible API at :11434/v1
pip install -e ".[agent]"
finagent-redteam --model llama3.1 --base-url http://localhost:11434/v1 --json results.json
```

## Option B — vLLM / SGLang

```bash
vllm serve Qwen/Qwen3-8B --port 8000 --enable-auto-tool-choice --tool-call-parser hermes
finagent-redteam --model Qwen/Qwen3-8B --base-url http://localhost:8000/v1
```

## Option C — hosted API

```bash
export OPENAI_API_KEY=sk-...
finagent-redteam --model gpt-4o-mini --api-key "$OPENAI_API_KEY"
```

## Reading the scorecard

- **Attack Success Rate (ON)** is the headline safety number — lower is better.
- **Defense efficacy** shows how much the built-in guardrails helped.
- **Utility (ON)** must stay high; a model that refuses the benign payment is
  over-refusing, not "safe".
