# Runbook: README Update Failure

## Scope

Use this runbook when the automated README refresh fails, stalls, or opens an
unexpected pull request.

## Typical Symptoms

- The scheduled workflow fails in GitHub Actions
- No PR is created after the daily refresh
- The PR is created but the generated README content is invalid
- The workflow logs show GitHub API errors or README marker errors

## First Checks

1. Inspect the latest runs of `Update README Top 50 GitHub Stars`.
2. Confirm that `README.md` still contains `<!-- TOP50:START -->` and `<!-- TOP50:END -->`.
3. Verify that `ci` and `security` are green on the proposed branch.
4. Check whether the workflow already updated the dedicated branch and PR.

## Common Causes

### Rate limit or API access issues

- Symptoms: `403`, `429`, or connection failures in the GitHub client step
- Action: confirm `GITHUB_TOKEN` availability and review the logged rate-limit wait

### Marker drift

- Symptoms: `Balises TOP50 introuvables dans README.md`
- Action: restore the two README markers around the generated block

### Broken rendering

- Symptoms: malformed tables, broken anchors, or invalid repository links
- Action: run `make test` locally and inspect the README-link integration tests

### PR automation issues

- Symptoms: branch updated but no PR created
- Action: inspect the `gh pr list` / `gh pr create` step and token permissions

## Recovery

1. Run `make install-dev`.
2. Run `make test`.
3. Run `make run`.
4. Inspect the local `README.md` diff.
5. If valid, create or update the automation PR manually.

## Escalation

- If GitHub Actions cannot create or update the PR, check repository permissions and branch settings.
- If contributor or insights data looks stale, treat it as a GitHub platform issue rather than a code issue in this repository.
