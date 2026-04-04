# Architecture

## Purpose

`github-top50` updates the profile `README.md` with a curated "Top 50 GitHub Stars"
section and category-specific repository tables.

The project has two execution modes:

- local execution through the packaged CLI or the compatibility script
- automated execution through GitHub Actions

## Repository Layout

- `src/github_top50/config.py`: static configuration, markers, category metadata, and hosting recommendations
- `src/github_top50/cli.py`: command-line entrypoint and orchestration
- `src/github_top50/services/github_client.py`: GitHub API search client and rate-limit handling
- `src/github_top50/services/readme_builder.py`: markdown rendering and README replacement
- `src/github_top50/utils/slug.py`: heading-to-anchor normalization
- `scripts/build_top50.py`: backward-compatible wrapper around the packaged implementation

## Execution Flow

1. The CLI loads static categories and README markers from configuration.
2. The GitHub client fetches the global top repositories and then the category-specific lists.
3. The README builder renders the hosting section, markdown tables, a table of contents, and category sections.
4. The generated block replaces the content between `<!-- TOP50:START -->` and `<!-- TOP50:END -->`.
5. In automation, GitHub Actions opens or updates a pull request instead of pushing directly to `main`.

## Boundaries

- Domain/config boundary: category definitions and markers are static and versioned in the repo.
- Transport boundary: only the GitHub Search API client performs network I/O.
- Rendering boundary: markdown generation is isolated from transport concerns.
- Compatibility boundary: the legacy script delegates to the packaged code path.

## Operational Model

- CI validates linting, formatting, tests, and coverage.
- Security checks run dependency audit and Bandit analysis.
- The scheduled README update workflow refreshes content and proposes the change through a PR.
- Tagged releases create GitHub releases with generated notes.

## Failure Modes

- GitHub API rate limiting or transient network issues during repository search
- README marker drift or accidental removal
- Invalid or stale automation token permissions
- Rendering regressions that break anchors or repository links

## Security Notes

- The generator uses `GITHUB_TOKEN` when available and does not require hard-coded credentials.
- README generation is constrained to a marker-delimited section.
- Dependency and static-analysis checks are enforced in dedicated workflows.

## Non-Goals

- Persisting repository data outside the repository
- Mutating GitHub state beyond opening or updating the README automation PR
- Acting as a generic GitHub analytics service
