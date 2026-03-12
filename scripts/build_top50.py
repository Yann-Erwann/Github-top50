import os
import time
import requests
from pathlib import Path

README_PATH = Path("README.md")
START = "<!-- TOP50:START -->"
END = "<!-- TOP50:END -->"

GLOBAL_QUERY = "stars:>1"
PER_PAGE = 50
CATEGORY_PER_PAGE = 10

CATEGORIES = [
    {
        "title": "🔒 Security & DevSecOps",
        "tag": "SECURITY",
        "query": "topic:devsecops stars:>500",
    },
    {
        "title": "☁️ Infrastructure & Cloud",
        "tag": "INFRA",
        "query": "topic:infrastructure-as-code stars:>500",
    },
    {
        "title": "⚛️ Frontend Frameworks",
        "tag": "FRONTEND",
        "query": "topic:react stars:>5000",
    },
    {
        "title": "☕ Java Ecosystem",
        "tag": "JAVA",
        "query": "language:java stars:>5000",
    },
    {
        "title": "🤖 AI & Machine Learning",
        "tag": "AI",
        "query": "topic:machine-learning stars:>5000",
    },
    {
        "title": "📊 Observability & SRE",
        "tag": "OBS",
        "query": "topic:observability stars:>500",
    },
    {
        "title": "🔌 API Design & Contracts",
        "tag": "API",
        "query": "topic:openapi stars:>500",
    },
    {
        "title": "🛠️ Developer Tools & CLI",
        "tag": "DEVTOOLS",
        "query": "topic:cli stars:>5000",
    },
    {
        "title": "🗄️ Databases",
        "tag": "DB",
        "query": "topic:database stars:>5000",
    },
]

token = os.getenv("GITHUB_TOKEN")

headers = {
    "Accept": "application/vnd.github+json",
}
if token:
    headers["Authorization"] = f"Bearer {token}"

API_URL = "https://api.github.com/search/repositories"


def search_repos(query, per_page):
    """Search GitHub repos and return items list."""
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": 1,
    }
    resp = requests.get(API_URL, headers=headers, params=params, timeout=30)
    if resp.status_code == 403:
        print(f"Rate limited, waiting 60s...")
        time.sleep(60)
        resp = requests.get(API_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("items", [])


def build_table(items, start=1):
    """Build a markdown table from repo items."""
    lines = []
    lines.append("| # | Repository | Description | ⭐ Stars | Langage |")
    lines.append("|---:|---|---|---:|---|")
    for idx, repo in enumerate(items, start=start):
        name = repo["full_name"]
        html_url = repo["html_url"]
        stars = repo["stargazers_count"]
        language = repo["language"] or "-"
        desc = (repo.get("description") or "-").replace("|", "\\|")
        if len(desc) > 100:
            desc = desc[:97] + "..."
        lines.append(
            f"| {idx} | [{name}]({html_url}) | {desc} | {stars:,} | {language} |"
        )
    return "\n".join(lines)


# --- Build global top 50 ---
print("Fetching global top 50...")
global_items = search_repos(GLOBAL_QUERY, PER_PAGE)
global_table = build_table(global_items)

# --- Build category tables ---
category_sections = []
for cat in CATEGORIES:
    tag_start = f"<!-- {cat['tag']}:START -->"
    tag_end = f"<!-- {cat['tag']}:END -->"
    print(f"Fetching {cat['title']}...")
    items = search_repos(cat["query"], CATEGORY_PER_PAGE)
    table = build_table(items)
    section = f"### {cat['title']}\n\n{tag_start}\n{table}\n{tag_end}"
    category_sections.append(section)
    time.sleep(2)  # avoid rate limiting

categories_block = "\n\n".join(category_sections)

# --- Assemble and write ---
content = README_PATH.read_text(encoding="utf-8")

if START not in content or END not in content:
    raise RuntimeError("Balises TOP50 introuvables dans README.md")

before = content.split(START)[0]
after = content.split(END)[1]

generated = f"{global_table}\n\n## 📂 Top par catégorie\n\n{categories_block}"

new_content = f"{before}{START}\n{generated}\n{END}{after}"
README_PATH.write_text(new_content, encoding="utf-8")

print("README.md mis à jour.")