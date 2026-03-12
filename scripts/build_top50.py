import os
import requests
from pathlib import Path

README_PATH = Path("README.md")
START = "<!-- TOP50:START -->"
END = "<!-- TOP50:END -->"

# Vous pouvez filtrer différemment ici :
# q = "stars:>1"
# ou par langage : "language:typescript stars:>1000"
QUERY = "stars:>1"
PER_PAGE = 50

token = os.getenv("GITHUB_TOKEN")

headers = {
    "Accept": "application/vnd.github+json",
}
if token:
    headers["Authorization"] = f"Bearer {token}"

url = "https://api.github.com/search/repositories"
params = {
    "q": QUERY,
    "sort": "stars",
    "order": "desc",
    "per_page": PER_PAGE,
    "page": 1,
}

resp = requests.get(url, headers=headers, params=params, timeout=30)
resp.raise_for_status()
items = resp.json().get("items", [])

lines = []
lines.append("| Rang | Repository | Stars | Langage |")
lines.append("|---:|---|---:|---|")

for idx, repo in enumerate(items, start=1):
    name = repo["full_name"]
    html_url = repo["html_url"]
    stars = repo["stargazers_count"]
    language = repo["language"] or "-"
    lines.append(f"| {idx} | [{name}]({html_url}) | {stars:,} | {language} |")

generated = "\n".join(lines)

content = README_PATH.read_text(encoding="utf-8")

if START not in content or END not in content:
    raise RuntimeError("Balises TOP50 introuvables dans README.md")

before = content.split(START)[0]
after = content.split(END)[1]

new_content = f"{before}{START}\n{generated}\n{END}{after}"
README_PATH.write_text(new_content, encoding="utf-8")

print("README.md mis à jour.")