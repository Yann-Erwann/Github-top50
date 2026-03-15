# ADR 0001: Package boundaries and README automation flow

## Status

Accepted

## Context

The project started as a single script with direct writes to the repository and
minimal delivery controls. As the repository gained tests, CI, and scheduled
automation, it needed clearer module boundaries and safer default branch updates.

## Decision

We keep the runtime logic inside a packaged `src/github_top50/` module and retain
`scripts/build_top50.py` only as a compatibility wrapper.

We also require README automation to open or update a pull request instead of
pushing directly to `main`.

## Consequences

- Runtime logic is testable through stable Python modules.
- The script entrypoint remains available for existing users and workflows.
- Scheduled automation no longer bypasses review and quality gates by default.
- Release and operational documentation can target one primary code path.
