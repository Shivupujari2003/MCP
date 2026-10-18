
import os
import json
import asyncio

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

MODEL = "gemini-3.8-flash"

SERVER = StdioServerParameters(
    command="uv",
    args=[
        "run",
        "python",
        "-m",
        "mcp_learning.servers.stdio.server",
    ],
    env=os.environ.copy(),
)


def _build_tool_declarations(result) -> list[types.FunctionDeclaration]:
    """Convert MCP tool metadata into Gemini function declarations."""
    return [
        types.FunctionDeclaration(
            name=tool.name,
            description=tool.description or "",
            parameters_json_schema=tool.inputSchema,
        )
        for tool in result.tools
    ]


def _print_available_tools(result, tool_count: int):
    """Display the MCP tools discovered from the stdio server."""
    print(f"    Found {tool_count} tools:")
    for tool in result.tools:
        print(f"      - {tool.name}: {tool.description}")


async def _call_tool(session, call_name: str, arguments: dict):
    """Call an MCP tool, asking for confirmation before course deletion."""
    if call_name == "remove_course" and arguments.get("confirm"):
        try:
            approval = input("Confirm deletion? Type DELETE: ")
        except (EOFError, KeyboardInterrupt):
            return {"error": "Deletion cancelled by user"}

        if approval != "DELETE":
            return {"error": "Deletion cancelled by user"}

    tool_result = await session.call_tool(call_name, arguments=arguments)
    if hasattr(tool_result, "model_dump"):
        return tool_result.model_dump(mode="json")
    return tool_result


async def _answer_question(llm, session, tools, question: str):
    """Generate a response and execute any MCP tools requested by Gemini."""
    contents = [question]

    for attempt in range(5):
        print(
            f"\n[5] Gemini processing "
            f"(iteration {attempt + 1}/5)..."
        )
        response = await llm.aio.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=tools)],
            ),
        )

        if not response.function_calls:
            print("\n[6] Final answer:")
            print(response.text)
            return

        calls = response.function_calls
        print(f"    Gemini requested {len(calls)} tool call(s).")
        contents.append(response.candidates[0].content)
        function_responses = []

        for call in calls:
            arguments = dict(call.args or {})
            print(f"\n[7] Calling tool: {call.name}")
            print(json.dumps(arguments, indent=2, default=str))
            tool_result = await _call_tool(session, call.name, arguments)
            print(f"    Tool {call.name} completed.")

            function_responses.append(
                types.Part.from_function_response(
                    name=call.name,
                    response={"result": tool_result},
                )
            )

        print("\n[8] Returning tool results to Gemini...")
        contents.append(
            types.Content(
                role="user",
                parts=function_responses,
            )
        )
    else:
        print("Gemini reached the tool-call limit.")


async def _run_chat(llm, session, tools):
    """Read questions until the user exits and route them to Gemini."""
    print("\n" + "=" * 50)
    print(" Gemini + MCP stdio Client Ready")
    print(" Type 'exit' to quit.")
    print("=" * 50)

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting client...")
            return

        if question.lower() == "exit":
            print("Exiting client...")
            return
        if question:
            print("\n[4] Sending question to Gemini...")
            await _answer_question(llm, session, tools, question)


async def main():
    """Launch the stdio server and run the interactive MCP client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from .env")

    print("\n[1] Initializing Gemini...")
    llm = genai.Client(api_key=api_key)
    print(f"    Model: {MODEL}")

    try:
        print("\n[2] Launching stdio MCP server...")
        async with stdio_client(SERVER) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("    MCP server initialized!")

                print("\n[3] Discovering MCP tools...")
                result = await session.list_tools()
                tools = _build_tool_declarations(result)

                _print_available_tools(result, len(tools))
                await _run_chat(llm, session, tools)

    finally:
        llm.close()
        print("\nGemini client closed.")


if __name__ == "__main__":
    asyncio.run(main())
