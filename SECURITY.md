# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do not open a public issue for security vulnerabilities.**

Instead, please send an email to: **yannerwann@proton.me**

You should expect a response within **48 hours**. We will work with you to understand and address the issue before any public disclosure.

## Scope

This project is a README auto-generation tool. Security concerns may include:

- Injection via GitHub API responses rendered in Markdown
- Exposure of secrets or tokens in CI workflows
- Dependency vulnerabilities in Python packages

## Automated Security Controls

The repository enforces automated controls in GitHub Actions to reduce supply-chain
and delivery risk:

- dependency auditing with `pip-audit`
- static analysis with `bandit`
- dependency review on pull requests
- secret scanning with `gitleaks`
- CodeQL analysis for Python sources
- CycloneDX SBOM generation for traceability and release assets
