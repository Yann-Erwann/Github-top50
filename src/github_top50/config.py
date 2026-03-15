"""Project configuration and static category metadata."""

from pathlib import Path

from github_top50.domain.models import CategoryDefinition

README_PATH = Path("README.md")
START = "<!-- TOP50:START -->"
END = "<!-- TOP50:END -->"

GLOBAL_QUERY = "stars:>1"
PER_PAGE = 50
CATEGORY_PER_PAGE = 10

CATEGORIES: tuple[CategoryDefinition, ...] = (
    CategoryDefinition(
        title="☕ Backend — Java & Spring Boot",
        tag="JAVA",
        query="language:java topic:spring-boot stars:>1000",
    ),
    CategoryDefinition(
        title="🟢 Backend — NestJS & Node.js",
        tag="NESTJS",
        query="topic:nestjs stars:>500",
    ),
    CategoryDefinition(
        title="🐍 Backend — Python",
        tag="PYTHON",
        query="language:python topic:python stars:>5000",
    ),
    CategoryDefinition(
        title="⚛️ Frontend — React & Next.js",
        tag="REACT",
        query="topic:react stars:>5000",
    ),
    CategoryDefinition(
        title="🅰️ Frontend - Angular",
        tag="ANGULAR",
        query="topic:angular stars:>1000",
    ),
    CategoryDefinition(
        title="🎨 Frontend — UI & Design Systems",
        tag="UIDESIGN",
        query="topic:design-system stars:>500",
    ),
    CategoryDefinition(
        title="🔌 API & Contracts",
        tag="API",
        query="topic:openapi stars:>500",
    ),
    CategoryDefinition(
        title="🏗️ Architecture-DDD/Event Storming",
        tag="DDD",
        query="topic:domain-driven-design stars:>200",
    ),
    CategoryDefinition(
        title="🧪 Architecture — TDD & Tests",
        tag="TDD",
        query="topic:testing-framework stars:>1000",
    ),
    CategoryDefinition(
        title="📐 Architecture-Agile Engineering",
        tag="AGILE",
        query="topic:architecture stars:>1000",
    ),
    CategoryDefinition(
        title="📊 Quality & Observability",
        tag="OBS",
        query="topic:observability stars:>500",
    ),
    CategoryDefinition(
        title="☁️ DevOps & Infrastructure",
        tag="DEVOPS",
        query="topic:devops stars:>5000",
    ),
    CategoryDefinition(
        title="🌐 Cloud & Platform Engineering",
        tag="CLOUD",
        query="topic:cloud-native stars:>1000",
    ),
    CategoryDefinition(
        title="🤖 MLOps & Data Engineering",
        tag="MLOPS",
        query="topic:mlops stars:>1000",
    ),
    CategoryDefinition(
        title="🗄️ Data & Databases",
        tag="DB",
        query="topic:database stars:>5000",
    ),
    CategoryDefinition(
        title="🛠️ Dev Tools & Productivity",
        tag="DEVTOOLS",
        query="topic:cli stars:>5000",
    ),
    CategoryDefinition(
        title="🔧 Toolchain — Build & DX",
        tag="TOOLCHAIN",
        query="topic:build-tool stars:>1000",
    ),
    CategoryDefinition(
        title="📚 Tech Radar & References",
        tag="TECHRADAR",
        query="topic:awesome-list stars:>10000",
    ),
    CategoryDefinition(
        title="📖 Documentation & ADR",
        tag="DOCS",
        query="topic:documentation stars:>5000",
    ),
    CategoryDefinition(
        title="⚖️ IA Ethics & Responsible AI",
        tag="ETHICSAI",
        query="topic:fairness-ai stars:>200",
    ),
    CategoryDefinition(
        title="🛡️ Governance & Compliance",
        tag="GOVERNANCE",
        query="topic:compliance stars:>500",
    ),
    CategoryDefinition(
        title="🔒 Security & DevSecOps",
        tag="SECURITY",
        query="topic:devsecops stars:>500",
    ),
    CategoryDefinition(
        title="🧠 GenAI & LLM",
        tag="GENAI",
        query="topic:llm stars:>1000",
    ),
    CategoryDefinition(
        title="🐳 Kubernetes & Containers",
        tag="K8S",
        query="topic:kubernetes stars:>5000",
    ),
)
