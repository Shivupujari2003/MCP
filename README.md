# MCP Learning Server

A Python MCP project that connects Gemini to course-learning database tools and
external APIs through stdio and Streamable HTTP transports.

## Requirements

- Python 3.11 or newer
- PostgreSQL with the `courses` and `lessons` tables
- A Gemini API key for the example clients
- [uv](https://docs.astral.sh/uv/) for environment and dependency management

## Installation

Install `uv` if it is not already installed:

```powershell
pip install uv
```

Clone the repository and enter the project directory:

```powershell
git clone <repository-url>
cd mcp-weather
```

Create the virtual environment and install the locked dependencies:

```powershell
uv sync
```

`uv sync` reads `pyproject.toml`, uses `uv.lock`, and creates `.venv`
automatically. You do not need to activate the virtual environment when using
`uv run`.

## Environment configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key

DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

# Optional GitHub authentication for higher API rate limits
GITHUB_TOKEN=your_github_token

# Optional REST Countries token; the demo value is used by default
REST_COUNTRIES_TOKEN=rc_live_demo
```

The database tools require a reachable PostgreSQL database with these tables:

- `courses`: course ID, title, category, and difficulty.
- `lessons`: lesson ID, course ID, title, duration, and completion status.

`.env` is ignored by Git. Never commit API keys, database passwords, or other
secrets.

## Project structure

```text
src/mcp_learning/
├── clients/
│   ├── http_client.py       # Gemini client for the HTTP MCP server.
│   └── stdio_client.py      # Gemini client that launches the stdio server.
├── servers/
│   ├── http/server.py       # Streamable HTTP MCP server on port 8000.
│   └── stdio/server.py      # Local MCP server over standard input/output.
└── tools/
    ├── db_tools.py          # PostgreSQL course and lesson operations.
    └── tools.py             # Async weather, Wikipedia, GitHub, and country APIs.
```

## Available MCP tools

### Course and lesson tools

Database-backed operations for managing courses, lessons, and learning
progress:

- `get_courses` — list all courses.
- `find_courses` — search courses by title, category, or difficulty.
- `fetch_course` — retrieve one course by ID.
- `create_course` — create a course.
- `edit_course` — update selected course fields.
- `remove_course` — delete a course after confirmation.
- `fetch_lessons` — list lessons for a course.
- `complete_lesson` — mark a lesson complete or incomplete.
- `fetch_learning_progress` — show progress for every course.

### External API tools

Async HTTP tools that return compact structured results from public APIs:

- `get_weather` — get current weather for a city using Open-Meteo.
- `get_weather_forecast` — get a 1–7 day forecast using Open-Meteo.
- `search_wikipedia` — search English Wikipedia articles.
- `get_wikipedia_summary` — retrieve a plain-text article introduction.
- `search_github_repositories` — search public GitHub repositories.
- `get_github_repository` — retrieve public repository details.
- `get_github_issues` — list open issues while excluding pull requests.
- `get_country_info` — retrieve country details from REST Countries.
- `search_countries` — search countries by free-text query.

## Servers and clients

### Stdio

The stdio server communicates over the process's standard input and output.
The stdio client starts that server automatically, so only one command is
required:

```powershell
uv run python -m mcp_learning.clients.stdio_client
```

Use this mode for local MCP integrations where the client launches the server
as a child process.

### Streamable HTTP

The HTTP server runs as a separate web service at
`http://127.0.0.1:8000/mcp`. Start it in one terminal:

```powershell
uv run python -m mcp_learning.servers.http.server
```

Then start the HTTP Gemini client in a second terminal:

```powershell
uv run python -m mcp_learning.clients.http_client
```

Use this mode when multiple clients or remote HTTP-capable MCP integrations
need to connect to the same running server.

### Transport comparison

| Feature | Stdio | Streamable HTTP |
| --- | --- | --- |
| Connection | Process pipes | HTTP endpoint |
| Server startup | Client starts it automatically | Started separately |
| Client terminals | One command | Server and client terminals |
| Best for | Local single-client use | Shared or HTTP-based clients |
| Endpoint | None | `http://127.0.0.1:8000/mcp` |

Type `exit` in either interactive client to close it.

## Testing and validation

Run the test suite:

```powershell
uv run pytest tests
```

Compile the application modules:

```powershell
uv run python -m py_compile `
  src\mcp_learning\tools\tools.py `
  src\mcp_learning\tools\db_tools.py `
  src\mcp_learning\servers\http\server.py `
  src\mcp_learning\servers\stdio\server.py
```

## Useful example questions

- `What's the current weather in Bengaluru?`
- `Give me the 5-day weather forecast for Mumbai.`
- `Search Wikipedia for Model Context Protocol.`
- `Summarize the Wikipedia article about Python.`
- `Search GitHub for MCP servers written in Python.`
- `Show details for the owner/repository repository.`
- `List open issues in the owner/repository repository.`
- `Give me information about India.`
- `Search for countries matching United.`
- `Show my learning progress.`
