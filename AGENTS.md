# AGENTS.md: SkillAction Sandbox Operating Manual

## 1. Project Overview & Core Mission
**SkillAction Sandbox** is a high-performance, containerized execution environment designed for the deterministic evaluation of AI-generated code. The mission is to provide a zero-trust, ephemeral runtime that validates logic, security, and performance constraints before integration into production pipelines. Agents must treat the codebase as a immutable-first, strictly-typed system where every modification must be verifiable via the automated test suite.

## 2. Local PowerShell Commands
All agents must execute tasks via the following standardized PowerShell interface. Do not bypass these scripts.

*   **Setup:** `./scripts/setup.ps1` (Installs venv, syncs `pyproject.toml`, installs dev-dependencies).
*   **Test:** `./scripts/test.ps1` (Executes `pytest` with coverage reporting and strict assertion flags).
*   **Run:** `./scripts/run.ps1 --module <name>` (Invokes the entry point with isolated environment variables).
*   **Lint:** `./scripts/lint.ps1` (Runs `ruff` for linting/formatting and `mypy` for static type analysis).
*   **Clean:** `./scripts/clean.ps1` (Purges `__pycache__`, `.pytest_cache`, and ephemeral build artifacts).

## 3. Engineering Invariants
Agents are bound by the following non-negotiable constraints:

*   **Zero-Placeholder Mandate:** Never commit `TODO`, `FIXME`, or `// TODO: Implement later` comments. If a feature is incomplete, the code must raise `NotImplementedError` with a descriptive message or remain uncommitted.
*   **Typing Strictness:** All functions must include PEP 484 type hints. `Any` is strictly forbidden unless explicitly approved by the Lead Architect. Use `Protocol` or `TypeVar` for generics.
*   **CRLF/LF Preservation:** The repository enforces `LF` line endings. Ensure your environment configuration matches the `.gitattributes` settings.
*   **Modular Decoupling:** Business logic must be separated from I/O and infrastructure concerns. Dependency Injection (DI) is the required pattern for all external service interactions.
*   **Atomic Commits:** Each commit must represent a single, functional change that passes the full lint/test suite.

## 4. Self-Healing & Error Recovery Protocol
When a process fails, agents must follow this recursive diagnostic loop:

1.  **Traceback Analysis:** Capture the full stack trace from the `stderr` output. Identify the root cause (e.g., `ImportError`, `TypeError`, `RuntimeError`).
2.  **State Inspection:** Run `./scripts/lint.ps1` to ensure the error is not a result of type mismatch or syntax drift.
3.  **Isolation:** Create a minimal reproduction script in `/tests/repro/` that triggers the specific error.
4.  **Correction:** Apply the fix. Do not "guess" at solutions. Use the `mypy` output to guide type corrections.
5.  **Verification:** Run `./scripts/test.ps1`. If the test fails, revert the change and re-evaluate the architectural assumption.
6.  **Logging:** If the error persists, append the diagnostic findings to the `DEBUG.log` file before attempting a secondary architectural refactor.

## 5. Definition of Done (DoD) Quality Gate
A task is only considered "Done" when it satisfies the following criteria:

*   **Static Analysis:** `mypy` reports zero errors; `ruff` reports zero violations.
*   **Test Coverage:** 100% branch coverage for new logic; existing coverage must not decrease.
*   **Documentation:** All public APIs are documented with Google-style docstrings, including `Args`, `Returns`, and `Raises` sections.
*   **Performance:** Execution time for the new module must fall within the baseline latency defined in `ARCHITECTURE.md`.
*   **Integration:** The code passes the full suite of integration tests in the CI pipeline without warnings.
*   **Cleanup:** No temporary files, debug prints, or commented-out code blocks remain in the codebase.