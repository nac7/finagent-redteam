"""FinAgent Red-Team — a benchmark for regulatory-control bypass in AI agents
that operate on financial workflows.

The core (``sandbox``, ``scenarios``, ``eval``) is dependency-free and fully
deterministic so the test-suite runs offline with no model or GPU. The
``agent`` driver, which needs the ``openai`` client, is imported explicitly.
"""

__version__ = "0.1.0"
