# 🌐 OmniResearch AI — Autonomous Web Intelligence & Executive Reporting Agent

An intelligent, autonomous multi-tool AI Research Agent powered by **LangChain**, **LangGraph**, **Google Gemini**, **Playwright**, and **MCP (Model Context Protocol)**. Equipped with an ultra-premium, modern **Django Web Interface** featuring Dark & Light mode, full Conversation History persistence, a Research Artifacts Vault, and executive document exports in **PDF, Word (.docx), and Markdown**.

---

## ✨ Features & Highlights

### 🧠 Autonomous Research Agent
- **Live Web Scraping & Search**: Autonomous headless browser discovery powered by Playwright and DuckDuckGo for real-time information retrieval.
- **Deep Reasoning & Fact Verification**: Multi-step intent analysis, tool execution, and context cross-referencing powered by Gemini models.
- **Perplexity-Style Source Pill**: Compact citation capsule with site favicons and an expandable grid of source cards.
- **MCP Storage Management**: Integrated Model Context Protocol architecture for standardized tool interaction and artifact tracking.
- **Multi-Format Document Export**: Save executive research dossiers instantly into **PDF**, **Microsoft Word (.docx)**, or **Markdown (.md)**.

### 🎨 Ultra-Premium Modern Frontend (Django)
- **Multi-Theme Support**: Dark Mode and Executive Light Mode with persistent localStorage preference and zero flash of unstyled content (FOUC).
- **Universal Quantum Neural Loader**: Unified spinning quantum rings and neural frequency wave animations with live elapsed execution timers.
- **Conversation History Drawer**: Slide-over drawer with thread auto-titling, search, history switching, and local persistence (`research/conversations.json`).
- **Research Artifacts Vault**: Dedicated drawer to browse generated reports with format filtering tabs (**All**, **PDF**, **Word**, **Markdown**) and real-time filename search.
- **Interactive Markdown Preview**: Full-screen modal to read and syntax-highlight reports directly inside the browser before downloading.
- **100% Mobile & Desktop Responsive**: Optimized touch interaction, safe-area padding for notch/home-bars, and responsive layouts across all viewport sizes.

---

## 🏗️ Project Architecture

```
AI-Agent/
├── agent.py                 # Core LangChain/LangGraph agent logic & prompts
├── browser_tools.py         # Playwright headless browser & document conversion tools
├── mcp_manager.py           # Model Context Protocol filesystem & artifact tools
├── manage.py                # Django CLI entrypoint
├── requirements.txt         # Project dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules for virtualenvs, keys, & outputs
│
├── web_config/              # Django Project Configuration
│   ├── settings.py          # Django settings, staticfiles, & PKG paths
│   ├── urls.py              # Root URL router
│   └── wsgi.py              # WSGI server entrypoint
│
├── research_ui/             # Django Frontend & REST API App
│   ├── views.py             # Chat streaming, reports preview, conversation history APIs
│   ├── urls.py              # API & UI endpoints
│   ├── templates/
│   │   └── research_ui/
│   │       └── index.html   # Primary single-page web application
│   └── static/
│       ├── css/
│       │   └── styles.css   # Custom styling, quantum animations, & theme tokens
│       └── js/
│           └── app.js       # Vanilla ES6 client logic, drawers, marked.js integration
│
└── research/                # Dynamic Agent Storage
    ├── conversations.json   # Persisted chat threads & history
    └── reports/             # Generated PDFs, DOCX, and Markdown artifacts
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Google Gemini API Key** (Get one at [Google AI Studio](https://aistudio.google.com/))

### 2. Installation

Clone the repository and set up a virtual environment:

```bash
git clone <repository-url>
cd AI-Agent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. Environment Configuration

Copy the example environment file and insert your API keys:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-flash-lite-latest
TAVILY_API_KEY=your_tavily_api_key_here  # Optional
```

---

## 💻 Running the Application

### Launch the Web Application (Recommended)
Run the Django development server:

```bash
python manage.py runserver
```

Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

### Running the Agent via CLI (Headless Mode)
You can also run the agent directly from the terminal without the web UI:

```bash
python agent.py
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main Web Application UI |
| `/api/chat/` | `POST` | Execute agent research query / export commands |
| `/api/reports/` | `GET` | List all files in the Research Artifacts Vault |
| `/api/reports/download/<path>` | `GET` | Download a generated report |
| `/api/reports/preview/<path>` | `GET` | Get text content of a markdown report for modal preview |
| `/api/conversations/` | `GET` | List past conversation threads |
| `/api/conversations/<id>/` | `GET` | Fetch specific conversation thread |
| `/api/conversations/<id>/delete/` | `POST` | Delete a single conversation thread |
| `/api/conversations/clear/` | `POST` | Clear all conversation history |
| `/api/reset/` | `POST` | Reset current memory checkpoint for a new session |
| `/api/status/` | `GET` | Agent healthcheck and model runtime status |

---

## 📄 Exporting Reports

While chatting with the agent, simply type or click any of the export commands:
- `save as pdf` — Generates a professionally styled PDF document in `research/reports/`.
- `save as docx` (or `save as word`) — Generates a Microsoft Word document.
- `save as markdown` — Saves a clean GitHub-flavored Markdown file.

All files are automatically indexed in the **Report Vault** drawer for instant download or in-browser preview.

---

## 🛡️ License

This project is licensed under the MIT License.
