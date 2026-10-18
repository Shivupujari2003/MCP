import os
from functools import wraps
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()

HTTP_TIMEOUT = httpx.Timeout(10.0)
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
GITHUB_API_URL = "https://api.github.com"
COUNTRIES_API_URL = "https://api.restcountries.com/countries/v5"


def _error(message: str) -> dict[str, str]:
    """Return a consistent, user-safe API error response."""
    return {"error": message}


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | list[Any]:
    """Fetch JSON and translate expected HTTP failures into safe errors."""
    try:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as exc:
        raise ValueError("The external API request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ValueError("The requested resource was not found.") from exc
        if exc.response.status_code == 429:
            raise ValueError("The external API rate limit was reached.") from exc
        raise ValueError("The external API returned an HTTP error.") from exc
    except httpx.RequestError as exc:
        raise ValueError("Could not connect to the external API.") from exc
    except ValueError as exc:
        raise ValueError("The external API returned invalid JSON.") from exc


def _validate_text(value: str, field_name: str) -> str | None:
    """Validate and normalize a required text argument."""
    value = value.strip()
    if not value:
        return f"{field_name} is required."
    return None


def _validate_limit(limit: int, maximum: int = 10) -> str | None:
    """Validate a bounded result limit used by search tools."""
    if not 1 <= limit <= maximum:
        return f"limit must be between 1 and {maximum}."
    return None


async def _geocode_city(client: httpx.AsyncClient, city: str) -> dict[str, Any] | None:
    """Resolve a city to the first useful Open-Meteo location."""
    data = await _get_json(
        client,
        OPEN_METEO_GEOCODING_URL,
        params={"name": city, "count": 5, "language": "en", "format": "json"},
    )
    results = data.get("results") if isinstance(data, dict) else None
    return results[0] if results else None


def _github_headers() -> dict[str, str]:
    """Build GitHub headers with optional bearer authentication."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _country_token() -> str:
    """Read the configurable REST Countries bearer token."""
    return os.getenv("REST_COUNTRIES_TOKEN", "rc_live_demo")


def _country_headers() -> dict[str, str]:
    """Build headers for the REST Countries API."""
    return {"Authorization": f"Bearer {_country_token()}"}


def _handle_api_errors(function):
    """Convert expected external API failures into structured tool results."""
    @wraps(function)
    async def wrapped(*args, **kwargs):
        try:
            return await function(*args, **kwargs)
        except ValueError as exc:
            return _error(str(exc))

    return wrapped


def _country_record(country: dict[str, Any]) -> dict[str, Any]:
    """Extract stable fields from a REST Countries v5 record."""
    name = country.get("name") or {}
    native_name = next(iter((name.get("nativeName") or {}).values()), {})
    currencies = [
        {"code": code, "name": details.get("name")}
        for code, details in (country.get("currencies") or {}).items()
    ]
    return {
        "name": name.get("common"),
        "official_name": name.get("official"),
        "capital": country.get("capital") or [],
        "region": country.get("region"),
        "subregion": country.get("subregion"),
        "iso_alpha_2": country.get("cca2"),
        "iso_alpha_3": country.get("cca3"),
        "currencies": currencies,
        "languages": list((country.get("languages") or {}).values()),
        "population": country.get("population"),
        "area": country.get("area"),
        "flag": country.get("flag"),
        "native_name": native_name.get("common"),
    }


@_handle_api_errors
async def get_weather(city: str) -> dict[str, Any]:
    """Return current weather for a city.

    Args:
        city: City name to geocode, such as ``Bengaluru``.
    """
    error = _validate_text(city, "city")
    if error:
        return _error(error)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        location = await _geocode_city(client, city)
        if not location:
            return _error(f"No location found for '{city.strip()}'.")
        data = await _get_json(
            client,
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "precipitation,weather_code,wind_speed_10m,wind_direction_10m"
                ),
                "timezone": "auto",
            },
        )

    if not isinstance(data, dict) or not isinstance(data.get("current"), dict):
        return _error("The weather API returned an unexpected response.")
    return {
        "city": location.get("name"),
        "country": location.get("country"),
        "coordinates": {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
        },
        "timezone": data.get("timezone"),
        "current": data.get("current", {}),
        "units": data.get("current_units", {}),
    }


@_handle_api_errors
async def get_weather_forecast(city: str, days: int = 3) -> dict[str, Any]:
    """Return a daily weather forecast for a city.

    Args:
        city: City name to geocode, such as ``Mumbai``.
        days: Number of forecast days, from 1 through 7.
    """
    error = _validate_text(city, "city")
    if error:
        return _error(error)
    if not 1 <= days <= 7:
        return _error("days must be between 1 and 7.")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        location = await _geocode_city(client, city)
        if not location:
            return _error(f"No location found for '{city.strip()}'.")
        data = await _get_json(
            client,
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": (
                    "temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,wind_speed_10m_max"
                ),
                "forecast_days": days,
                "timezone": "auto",
            },
        )

    if not isinstance(data, dict) or not isinstance(data.get("daily"), dict):
        return _error("The forecast API returned an unexpected response.")
    daily = data["daily"]
    records = [
        {
            "date": date,
            "temperature_max": maximum,
            "temperature_min": minimum,
            "precipitation_sum": precipitation,
            "wind_speed_max": wind,
        }
        for date, maximum, minimum, precipitation, wind in zip(
            daily.get("time", []),
            daily.get("temperature_2m_max", []),
            daily.get("temperature_2m_min", []),
            daily.get("precipitation_sum", []),
            daily.get("wind_speed_10m_max", []),
        )
    ]
    if not isinstance(data, dict):
        return _error("The GitHub API returned an unexpected response.")
    return {
        "city": location.get("name"),
        "country": location.get("country"),
        "timezone": data.get("timezone"),
        "forecast": records,
        "units": data.get("daily_units", {}),
    }


@_handle_api_errors
async def search_wikipedia(query: str, limit: int = 5) -> dict[str, Any]:
    """Search English Wikipedia articles.

    Args:
        query: Required article or topic search phrase.
        limit: Maximum number of results, from 1 through 10.
    """
    error = _validate_text(query, "query") or _validate_limit(limit)
    if error:
        return _error(error)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _get_json(
            client,
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query.strip(),
                "srlimit": limit,
                "format": "json",
            },
        )
    results = data.get("query", {}).get("search", []) if isinstance(data, dict) else []
    return {
        "results": [
            {
                "title": item.get("title"),
                "page_id": item.get("pageid"),
                "snippet": item.get("snippet"),
            }
            for item in results
        ]
    }


@_handle_api_errors
async def get_wikipedia_summary(title: str) -> dict[str, Any]:
    """Return the plain-text introduction of a Wikipedia article.

    Args:
        title: Article title, such as ``Python (programming language)``.
    """
    error = _validate_text(title, "title")
    if error:
        return _error(error)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _get_json(
            client,
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "prop": "extracts",
                "exintro": "true",
                "explaintext": "true",
                "redirects": "1",
                "titles": title.strip(),
                "format": "json",
            },
        )
    pages = data.get("query", {}).get("pages", {}) if isinstance(data, dict) else {}
    page = next(iter(pages.values()), {}) if pages else {}
    if not page or "missing" in page:
        return _error(f"No Wikipedia article found for '{title.strip()}'.")
    return {
        "title": page.get("title"),
        "summary": page.get("extract", ""),
        "url": f"https://en.wikipedia.org/wiki/{quote(page.get('title', '').replace(' ', '_'))}",
    }


@_handle_api_errors
async def search_github_repositories(query: str, limit: int = 5) -> dict[str, Any]:
    """Search public GitHub repositories.

    Args:
        query: GitHub repository search syntax, such as ``MCP server language:Python``.
        limit: Maximum number of repositories, from 1 through 10.
    """
    error = _validate_text(query, "query") or _validate_limit(limit)
    if error:
        return _error(error)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _get_json(
            client,
            f"{GITHUB_API_URL}/search/repositories",
            params={"q": query.strip(), "per_page": limit},
            headers=_github_headers(),
        )
    items = data.get("items", []) if isinstance(data, dict) else []
    return {
        "repositories": [
            {
                "full_name": item.get("full_name"),
                "description": item.get("description"),
                "html_url": item.get("html_url"),
                "primary_language": item.get("language"),
                "stars": item.get("stargazers_count"),
                "forks": item.get("forks_count"),
                "open_issues": item.get("open_issues_count"),
            }
            for item in items
        ]
    }


@_handle_api_errors
async def get_github_repository(owner: str, repo: str) -> dict[str, Any]:
    """Return public details for a GitHub repository.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
    """
    owner_error = _validate_text(owner, "owner")
    repo_error = _validate_text(repo, "repo")
    if owner_error or repo_error:
        return _error(owner_error or repo_error or "Repository is required.")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _get_json(
            client,
            f"{GITHUB_API_URL}/repos/{quote(owner.strip())}/{quote(repo.strip())}",
            headers=_github_headers(),
        )
    return {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "html_url": data.get("html_url"),
        "default_branch": data.get("default_branch"),
        "primary_language": data.get("language"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }


@_handle_api_errors
async def get_github_issues(owner: str, repo: str, limit: int = 5) -> dict[str, Any]:
    """Return open issues, excluding pull requests, for a repository.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        limit: Maximum number of issues, from 1 through 10.
    """
    owner_error = _validate_text(owner, "owner")
    repo_error = _validate_text(repo, "repo")
    limit_error = _validate_limit(limit)
    if owner_error or repo_error or limit_error:
        return _error(owner_error or repo_error or limit_error or "Invalid input.")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _get_json(
            client,
            f"{GITHUB_API_URL}/repos/{quote(owner.strip())}/{quote(repo.strip())}/issues",
            params={"state": "open", "per_page": limit},
            headers=_github_headers(),
        )
    items = data if isinstance(data, list) else []
    return {
        "issues": [
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "html_url": issue.get("html_url"),
                "created_at": issue.get("created_at"),
                "labels": [label.get("name") for label in issue.get("labels", [])],
            }
            for issue in items
            if "pull_request" not in issue
        ]
    }


@_handle_api_errors
async def get_country_info(country: str) -> dict[str, Any]:
    """Return structured information for a country common name.

    Args:
        country: Common country name, such as ``India``.
    """
    error = _validate_text(country, "country")
    if error:
        return _error(error)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _get_json(
            client,
            f"{COUNTRIES_API_URL}/names.common/{quote(country.strip())}",
            headers=_country_headers(),
        )
    records = data if isinstance(data, list) else []
    if not records or not isinstance(records[0], dict):
        return _error(f"No country found for '{country.strip()}'.")
    return _country_record(records[0])


@_handle_api_errors
async def search_countries(query: str, limit: int = 5) -> dict[str, Any]:
    """Search countries using the REST Countries free-text query.

    Args:
        query: Required free-text country search phrase.
        limit: Maximum number of countries, from 1 through 10.
    """
    error = _validate_text(query, "query") or _validate_limit(limit)
    if error:
        return _error(error)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _get_json(
            client,
            COUNTRIES_API_URL,
            params={"q": query.strip(), "limit": limit},
            headers=_country_headers(),
        )
    records = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(records, list):
        return _error("The country API returned an unexpected response.")
    return {
        "countries": [
            {
                "name": record.get("name", {}).get("common"),
                "official_name": record.get("name", {}).get("official"),
                "capital": record.get("capital") or [],
                "region": record.get("region"),
                "iso_alpha_2": record.get("cca2"),
                "iso_alpha_3": record.get("cca3"),
                "flag": record.get("flag"),
            }
            for record in records[:limit]
            if isinstance(record, dict) and isinstance(record.get("name"), dict)
        ]
    }