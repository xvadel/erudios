# Erudios — AI Curriculum Builder

> Open-source personalized learning platform for AI & Machine Learning

Erudios solves the biggest pain point in technical learning: **not knowing what to learn, in what order, from which sources**. It automatically builds a dependency-ordered curriculum for any AI/ML topic, discovers curated resources, and always answers *"what should I learn next?"*

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Topic Dependency Graph** | Pre-built prerequisite map for 50+ AI/ML topics with smart acronym-aware search |
| **What to Learn Next** | Graph traversal tells you exactly which topics you've unlocked |
| **Resource Discovery** | Multi-source discovery (web, GitHub, papers) with trust scoring |
| **Lazy Content Generation** | Shell → Sections → Styles — generated only when requested |
| **Multi-Provider LLM Router** | Gemini + Groq + HuggingFace with daily budget tracking |
| **Shared Content Cache** | Generated content cached across ALL users (Redis + PostgreSQL) |
| **Self-Hosted Local Auth** | Simple Username + Password login — built for local/offline hosting |

---

## 🚀 Quick Start (Docker)

### 1. Clone & Configure

```bash
git clone https://github.com/xvadel/erudios.git
cd erudios
cp .env.example .env
```

### 2. Fill in your API keys in `.env`

At minimum you need **one** LLM provider API key to generate curriculum modules, descriptions, and section content:

| Key | Where to get it | Free tier |
|---|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) | 1M tokens/day |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com/keys) | 1M tokens/day |

### 3. Run

```bash
docker compose up -d
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

---

## 🏗️ Architecture

```
erudios/
├── backend/              # FastAPI (Python 3.11)
│   ├── app/
│   │   ├── api/v1/       # REST endpoints
│   │   ├── core/         # Security, exceptions
│   │   ├── db/           # SQLAlchemy + Alembic
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── modules/
│   │   │   ├── topic_graph/   # Dependency graph engine
│   │   │   ├── research/      # Resource discovery + ranking
│   │   │   ├── curriculum/    # Personalized path generation
│   │   │   └── rag/           # AI tutor
│   │   ├── providers/
│   │   │   └── llms/          # Gemini, Groq, HuggingFace + router
│   │   └── services/          # Cache, content cache
│   └── seed/             # Pre-built AI taxonomy + trusted sources
├── frontend/             # Next.js 15 (TypeScript)
│   └── src/
│       ├── app/          # App Router pages
│       ├── components/   # UI components
│       ├── hooks/        # Custom hooks
│       └── lib/          # API client + utilities
└── docker-compose.yml
```

### Infrastructure

| Service | Purpose |
|---|---|
| **PostgreSQL 16** | Primary data store (users, topics, resources, curricula) |
| **Redis 7** | Hot cache (L1) + provider budget tracking |
| **Qdrant** | Vector store for RAG tutor embeddings |

---

## 💡 Token Budget Strategy

Erudios is designed to operate entirely within **free API tiers**:

| Provider | Model | Daily Limit | Used For |
|---|---|---|---|
| Gemini | gemini-2.0-flash | 1,000,000 tokens | Medium/deep content gen |
| Groq | llama-3.3-70b-versatile | 1,000,000 tokens | Classification, short gen |
| Groq | gemma2-9b-it | 500,000 tokens | Fast classification |
| HuggingFace | Inference API | Unlimited (rate limited) | Fallback embeddings |
| DuckDuckGo | Search | Unlimited | Resource discovery |
| OpenAlex | Academic papers | Unlimited | Paper discovery |

**Key optimizations:**
- All generated content is **shared across users** — one user's generation benefits everyone
- Content generated in **stages** (shell → section → quiz) — pay only for what's viewed  
- Redis budget tracker prevents **daily limit overruns** automatically

---

## 🛠️ Local Development Setup

To run Erudios locally, the recommended workflow is a **hybrid setup**: run the database services (PostgreSQL, Redis, and Qdrant) via Docker Compose, and run the FastAPI backend and Next.js frontend code directly in your local environment. This enables fast hot-reloading and easy debugging.

### 1. Initialize Configuration
From the workspace root, copy the environment file:
```bash
cp .env.example .env
```
Fill in the required environment variables in the newly created `.env` file (minimum one LLM provider API key like `GEMINI_API_KEY`).

### 2. Start Databases (Via Docker)
Start only the supporting database containers:
```bash
docker compose up -d postgres redis qdrant
```
This spins up PostgreSQL on port `5432`, Redis on port `6379`, and Qdrant on port `6333`.

### 3. Setup & Start Backend
Open a new terminal and navigate to the backend folder:
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell/CMD):
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# Install dependencies in editable development mode
pip install -e ".[dev]"

# Copy the configured env file from root
cp ../.env .env

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
- API Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### 4. Setup & Start Frontend
Open a new terminal and navigate to the frontend folder:
```bash
cd frontend

# Install package dependencies
npm install

# Run the Next.js development server
npm run dev
```
- Frontend application: http://localhost:3000

---

## 📡 API Reference

See the auto-generated docs at http://localhost:8000/docs after starting the backend.

Key endpoints:

| Endpoint | Description |
|---|---|
| `GET /api/v1/topics` | List all AI domains |
| `GET /api/v1/topics/{slug}/whats-next` | What to learn next (zero LLM cost) |
| `GET /api/v1/topics/{slug}/learning-path` | Topologically sorted path |
| `GET /api/v1/topics/{slug}/prerequisites` | Prerequisites with explanations |
| `GET /api/v1/resources/topics/{slug}` | Ranked resources for a topic |
| `POST /api/v1/resources/topics/{slug}/discover` | Trigger resource discovery |
| `GET /api/v1/health` | Provider status + budget remaining |

---

## 🤝 Contributing

Pull requests welcome. Please open an issue first to discuss major changes.

---

## 📄 License

MIT — free to use, fork, and self-host.
