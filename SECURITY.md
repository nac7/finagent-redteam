# Security Policy

## Scope

FinAgent Red-Team is a **defensive red-team benchmark**. It operates exclusively
on synthetic, in-memory state and makes no network calls except to model
endpoints you supply. There are no real financial credentials, account numbers,
card data, or personally identifiable information anywhere in this repository.

## Supported versions

We maintain security fixes on the latest `main` branch only.

## Reporting a vulnerability

If you discover a security issue in this project (e.g. a scenario whose
`reference_plan` could be adapted to attack a real system, a dependency with a
known CVE, or a data-handling bug):

**Please do not open a public GitHub issue.**

Instead, email **lelenachiket991@gmail.com** with:

- A description of the issue and its potential impact.
- Steps to reproduce.
- Any suggested mitigations.

We will acknowledge within 72 hours and aim to resolve or mitigate within
14 days for critical issues. We will credit you in the release notes unless you
request otherwise.

## Responsible use

This benchmark is designed for:

- Academic research into LLM agent safety.
- Pre-deployment evaluation of financial AI agents.
- Development of guardrails and policy enforcement mechanisms.

It is **not** designed to generate, test, or distribute exploits against live
financial systems. Contributors and users are expected to follow all applicable
laws and the terms of any model API they use.

## Dual-use disclosure

The threat scenarios in this benchmark model real attack patterns (prompt
injection, sanctions evasion, payment structuring). We have taken the following
mitigations:

1. All execution is against a fully synthetic, in-memory sandbox — no real
   financial system is ever contacted.
2. The `reference_plan` in each scenario describes the minimal action sequence
   needed to pass the sandbox evaluator, not a real-world exploit.
3. The benchmark measures *model susceptibility* and *control efficacy*, not
   how to defeat a specific institution's defenses.

We welcome engagement from financial regulators, AISI, and AI safety
organizations who wish to review the scenario set or methodology.
