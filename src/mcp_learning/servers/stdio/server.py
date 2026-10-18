
from mcp.server.fastmcp import FastMCP
from mcp_learning.tools.db_tools import (
    list_courses,
    search_courses,
    get_course,
    add_course,
    update_course,
    delete_course,
    get_lessons,
    mark_lesson_completed,
    get_learning_progress,
)
from mcp_learning.tools.tools import (
    get_country_info,
    get_github_issues,
    get_github_repository,
    get_weather,
    get_weather_forecast,
    get_wikipedia_summary,
    search_countries,
    search_github_repositories,
    search_wikipedia,
)

mcp = FastMCP("Course Learning Server")


@mcp.tool()
def get_courses():
    """Return all available courses."""
    return list_courses()


@mcp.tool()
def find_courses(search_item: str = "", category: str = "", difficulty: str = ""):
    """Search courses by title text, category, or difficulty."""
    return search_courses(search_item, category, difficulty)


@mcp.tool()
def fetch_course(course_id: int):
    """Return one course by its ID."""
    return get_course(course_id)


@mcp.tool()
def create_course(title: str, category: str, difficulty: str = "Beginner"):
    """Create a course with a title, category, and difficulty."""
    return add_course(title, category, difficulty)


@mcp.tool()
def edit_course(course_id: int, title: str = None, category: str = None, difficulty: str = None):
    """Update one or more fields of an existing course."""
    return update_course(course_id, title, category, difficulty)


@mcp.tool()
def remove_course(course_id: int, confirm: bool = False):
    """Delete a course only when confirm is true."""
    return delete_course(course_id, confirm)


@mcp.tool()
def fetch_lessons(course_id: int):
    """Return all lessons belonging to a course."""
    return get_lessons(course_id)


@mcp.tool()
def complete_lesson(lesson_id: int, completed: bool = True):
    """Mark a lesson as completed or incomplete."""
    return mark_lesson_completed(lesson_id, completed)


@mcp.tool()
def fetch_learning_progress():
    """Return lesson completion progress for every course."""
    return get_learning_progress()


@mcp.tool(name="get_weather")
async def get_weather_tool(city: str):
    """Return current weather for a city.

    Args:
        city: City name to geocode, such as Bengaluru.
    """
    return await get_weather(city)


@mcp.tool(name="get_weather_forecast")
async def get_weather_forecast_tool(city: str, days: int = 3):
    """Return a daily weather forecast for a city.

    Args:
        city: City name to geocode.
        days: Number of forecast days, from 1 through 7.
    """
    return await get_weather_forecast(city, days)


@mcp.tool(name="search_wikipedia")
async def search_wikipedia_tool(query: str, limit: int = 5):
    """Search English Wikipedia articles.

    Args:
        query: Article or topic search phrase.
        limit: Maximum results, from 1 through 10.
    """
    return await search_wikipedia(query, limit)


@mcp.tool(name="get_wikipedia_summary")
async def get_wikipedia_summary_tool(title: str):
    """Return a concise Wikipedia article summary.

    Args:
        title: Wikipedia article title.
    """
    return await get_wikipedia_summary(title)


@mcp.tool(name="search_github_repositories")
async def search_github_repositories_tool(query: str, limit: int = 5):
    """Search public GitHub repositories.

    Args:
        query: GitHub repository search syntax.
        limit: Maximum results, from 1 through 10.
    """
    return await search_github_repositories(query, limit)


@mcp.tool(name="get_github_repository")
async def get_github_repository_tool(owner: str, repo: str):
    """Return public details for a GitHub repository.

    Args:
        owner: GitHub user or organization.
        repo: Repository name.
    """
    return await get_github_repository(owner, repo)


@mcp.tool(name="get_github_issues")
async def get_github_issues_tool(owner: str, repo: str, limit: int = 5):
    """Return open GitHub issues excluding pull requests.

    Args:
        owner: GitHub user or organization.
        repo: Repository name.
        limit: Maximum issues, from 1 through 10.
    """
    return await get_github_issues(owner, repo, limit)


@mcp.tool(name="get_country_info")
async def get_country_info_tool(country: str):
    """Return structured information for a country.

    Args:
        country: Common country name, such as India.
    """
    return await get_country_info(country)


@mcp.tool(name="search_countries")
async def search_countries_tool(query: str, limit: int = 5):
    """Search countries using a free-text query.

    Args:
        query: Country search phrase.
        limit: Maximum results, from 1 through 10.
    """
    return await search_countries(query, limit)


if __name__ == "__main__":
    try:
        # Start the stdio MCP server for local client communication.
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        # Ctrl+C is an intentional, clean server shutdown.
        pass
