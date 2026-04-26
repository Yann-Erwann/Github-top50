# Rapport de correction securite

## Synthese

Perimetre controle: scripts Python, workflows GitHub Actions, site Astro/TypeScript, lockfiles Python et npm.

Statut apres correction:

- Pas de secret hardcode confirme.
- `npm audit --json`: 0 vulnerabilite.
- `pip-audit --ignore-vuln CVE-2026-3219`: aucune vulnerabilite connue, 1 advisory pip ignore car aucune version corrigee n'est publiee.
- `bandit -q -r src scripts`: aucun finding.
- Scan sinks frontend (`set:html`, `is:inline`, `innerHTML`, `eval`, `document.write`, etc.): aucun resultat.
- Tests et build: `pytest` 70 passed, `npm run build` OK.

## Findings corriges

### SEC-001 - Astro vulnerable dans la toolchain frontend

Severity: Medium

File and line number:

- `site/package.json:13`
- `site/package-lock.json:1750`

Exact vulnerable code before fix:

```json
"astro": "^5.0.0"
```

Why it is exploitable:

Astro `<6.1.6` etait concerne par `GHSA-j687-52p2-xcff`, une classe XSS autour de la sanitization de `define:vars`. Le code actuel n'utilisait pas ce pattern, mais la dependance vulnerable restait dans la chaine de build.

Fix applied:

```json
"astro": "^6.1.9"
```

Validation:

```bash
cd site
npm audit --json
npm run build
```

### SEC-002 - PostCSS vulnerable en dependance transitive

Severity: Medium

File and line number:

- `site/package-lock.json:3941`

Exact vulnerable code before fix:

```json
"node_modules/postcss": {
  "version": "8.5.9"
}
```

Why it is exploitable:

PostCSS `<8.5.10` etait concerne par `GHSA-qx2v-qp2m-jg93`, avec risque XSS si du CSS controle par un attaquant est stringifie puis injecte dans du HTML.

Fix applied:

```json
"node_modules/postcss": {
  "version": "8.5.10"
}
```

Validation:

```bash
cd site
npm audit --json
```

### SEC-003 - pytest vulnerable dans les dependances dev Python

Severity: Medium

File and line number:

- `pyproject.toml:23`
- `uv.lock:501`

Exact vulnerable code before fix:

```toml
"pytest==9.0.2",
```

Why it is exploitable:

`CVE-2025-71176` / `GHSA-6w46-j5rx-g56g` affectait pytest jusqu'a `9.0.2` sur Unix via le repertoire temporaire de tests, avec risque local sur machines partagees ou runners mutualises.

Fix applied:

```toml
"pytest==9.0.3",
```

Validation:

```bash
uv sync --frozen --extra dev
pytest
```

### SEC-004 - CVE pip sans version corrigee disponible

Severity: Low

File and line number:

- `uv.lock:398`
- `.github/workflows/security.yml:43`

Exact vulnerable code:

```toml
name = "pip"
version = "26.0.1"
```

Why it is exploitable:

`CVE-2026-3219` concerne la gestion d'archives concatenees par pip. Ici pip est present dans l'environnement dev/audit, pas en runtime applicatif. Au moment du correctif, `pip-audit` ne propose pas de version fixee.

Fix / mitigation applied:

```yaml
- name: Audit dependencies
  # CVE-2026-3219 has no fixed pip release at the time of writing.
  # Keep pip-audit blocking for every other advisory.
  run: >
    python -m uv run --frozen --extra dev pip-audit
    --ignore-vuln CVE-2026-3219
```

Action restante:

Des qu'une version de pip corrigee existe, retirer `--ignore-vuln CVE-2026-3219`, executer `uv lock --upgrade-package pip`, puis relancer `uv sync --frozen --extra dev` et `pip-audit`.

### SEC-005 - URLs externes rendues sans validation scheme/host

Severity: Medium

File and line number:

- `scripts/export_site_data.py:46`
- `scripts/export_site_data.py:98`
- `site/src/data/site-data.ts:92`
- `site/src/data/site-data.ts:139`
- `site/src/data/site-data.ts:208`

Exact vulnerable code before fix:

```python
"htmlUrl": item["html_url"],
```

```ts
htmlUrl: toString(record.htmlUrl ?? record.html_url, "#"),
```

Why it is exploitable:

Astro echappe le texte, mais une valeur `href` doit quand meme etre limitee a un scheme et a des hosts connus. Si un snapshot ou le JSON genere contenait une URL `javascript:` ou un host non attendu, le site statique pouvait exposer un lien dangereux.

Fix applied:

```python
def require_https_url(
    value: object,
    *,
    allowed_hosts: frozenset[str],
    label: str,
) -> str:
    url = str(value)
    parsed = urlparse(url)

    if parsed.scheme != "https" or not is_allowed_host(parsed.netloc, allowed_hosts):
        raise ValueError(f"Unsafe {label} URL: {url}")

    return url
```

```ts
function toSafeHttpsUrl(
  value: unknown,
  allowedHosts: string[],
  fallback = "#"
): string {
  const candidate = toString(value, fallback);

  try {
    const url = new URL(candidate);

    if (url.protocol !== "https:" || !isAllowedHost(url.hostname, allowedHosts)) {
      return fallback;
    }

    return url.toString();
  } catch {
    return fallback;
  }
}
```

Validation:

Des tests unitaires rejettent maintenant les URLs de repository et d'hebergement non autorisees.

### SEC-006 - Scripts inline et CSP trop faible

Severity: Low

File and line number:

- `site/src/layouts/BaseLayout.astro:27`
- `site/src/layouts/BaseLayout.astro:37`
- `site/src/pages/top.astro:77`
- `site/public/theme.js:1`
- `site/public/top-filters.js:1`

Exact vulnerable code before fix:

```astro
<script is:inline set:html={themeBootScript}></script>
<script is:inline set:html={themeToggleScript}></script>
<script is:inline set:html={filterScript}></script>
```

Why it is exploitable:

Les scripts inline forcent une CSP faible ou absente. Si une faille XSS apparait plus tard, le navigateur ne bloque pas efficacement l'execution de script injecte.

Fix applied:

```astro
<meta
  http-equiv="Content-Security-Policy"
  content="default-src 'self'; base-uri 'self'; object-src 'none'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'none';"
/>
<script src={`${import.meta.env.BASE_URL}theme.js`}></script>
```

```astro
<script src={`${import.meta.env.BASE_URL}top-filters.js`}></script>
```

Validation:

Le scan des sinks frontend ne trouve plus `set:html`, `is:inline`, `innerHTML`, `eval`, `new Function` ou `document.write` dans `site/src`, `site/public`, `scripts`, `tests` et `.github`.

## Areas without confirmed findings

### Secrets & Credentials

Aucun API key, PAT, password, private key ou `.env` commite n'a ete confirme. Les correspondances restantes sont des noms de variables (`GITHUB_TOKEN`), de la documentation, ou des donnees publiques contenant le mot `secret`.

### Authentication & Authorization

Le depot ne contient pas de logique applicative d'authentification, session, JWT ou authorization. Aucun IDOR ou privilege escalation applicatif n'a ete confirme.

### OWASP Top 10

Aucune injection SQL/NoSQL/LDAP/command, SSRF, XXE, deserialisation dangereuse ou sink DOM HTML n'a ete confirmee.

### Infrastructure

Pas de backend CORS ni d'upload de fichier dans ce depot. La partie statique dispose maintenant d'une CSP meta stricte compatible GitHub Pages.
