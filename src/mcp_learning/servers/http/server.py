
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

# Configure the HTTP MCP server without per-client session state.
mcp = FastMCP("Course Learning Server", stateless_http=True)

# Register the database operations exposed to MCP clients.
mcp.add_tool(list_courses, name="get_courses")
mcp.add_tool(search_courses, name="find_courses")
mcp.add_tool(get_course, name="fetch_course")
mcp.add_tool(add_course, name="create_course")
mcp.add_tool(update_course, name="edit_course")
mcp.add_tool(delete_course, name="remove_course")
mcp.add_tool(get_lessons, name="fetch_lessons")
mcp.add_tool(mark_lesson_completed, name="complete_lesson")
mcp.add_tool(get_learning_progress, name="fetch_learning_progress")
mcp.add_tool(get_weather, name="get_weather")
mcp.add_tool(get_weather_forecast, name="get_weather_forecast")
mcp.add_tool(search_wikipedia, name="search_wikipedia")
mcp.add_tool(get_wikipedia_summary, name="get_wikipedia_summary")
mcp.add_tool(search_github_repositories, name="search_github_repositories")
mcp.add_tool(get_github_repository, name="get_github_repository")
mcp.add_tool(get_github_issues, name="get_github_issues")
mcp.add_tool(get_country_info, name="get_country_info")
mcp.add_tool(search_countries, name="search_countries")

if __name__ == "__main__":
    try:
        # Start the Streamable HTTP endpoint on the default MCP server port.
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        # Ctrl+C is an intentional, clean server shutdown.
        pass
