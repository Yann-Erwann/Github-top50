# Contributing

Thank you for your interest in contributing to this project!

## How to Contribute

1. **Fork** the repository
2. **Create a branch** from `main` using a descriptive name:
   ```bash
   git checkout -b feat/my-feature
   ```
3. **Make your changes** following the conventions below
4. **Test locally** before pushing:
   ```bash
   make install-dev
   make lint
   make test
   ```
5. **Run the generator** when you change the README generation flow:
   ```bash
   make run
   ```
6. **Run security checks** when dependencies, workflows, or API access change:
   ```bash
   python -m uv lock --upgrade
   make audit
   make security
   ```
7. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(scope): add new feature
   fix(scope): fix a bug
   docs(scope): update documentation
   ci(scope): change CI configuration
   chore(scope): maintenance task
   ```
8. **Open a Pull Request** against `main`

## Release Process

1. Update `CHANGELOG.md`
2. Create and push a semantic version tag such as `v1.1.0`
3. Let the `Release` workflow publish the GitHub release with generated notes

## Code Standards

- Python 3.12+
- Source code lives under `src/github_top50/`
- Format with [Ruff](https://docs.astral.sh/ruff/)
- Type hints encouraged
- Keep scripts simple and readable

## Reporting Issues

- Use the [issue templates](.github/ISSUE_TEMPLATE/) when available
- Include steps to reproduce for bugs
- One issue per report

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
