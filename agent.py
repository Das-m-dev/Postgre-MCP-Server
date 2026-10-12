import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from mcp import Client
from mcp import StdioServerParameters

from llm.gemini import GeminiLLM


load_dotenv()


server = StdioServerParameters(
    command="python",
    args=[
        "-m",
        "mcp_server.server",
    ],
)


def convert_mcp_tools(
    mcp_tools,
) -> list[dict[str, Any]]:

    result = []

    for tool in mcp_tools:

        result.append(
            {
                "name": tool.name,

                "description":
                    tool.description or "",

                "parameters": tool.inputSchema,
            }
        )

    return result


async def main():

    llm = GeminiLLM()

    async with Client(server) as mcp_client:

        # ----------------------------------
        # Get MCP tools
        # ----------------------------------

        tools_response = (
            await mcp_client.list_tools()
        )

        tools = convert_mcp_tools(
            tools_response.tools
        )

        print(
            "MCP tools:"
        )

        for tool in tools:
            print(
                f"  - {tool['name']}"
            )

        print()

        print(
            f"Gemini model: "
            f"{llm.model}"
        )

        print(
            "Type 'exit' to quit."
        )

        print()

        messages = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "You are a PostgreSQL "
                            "data assistant. "
                            "You have access to "
                            "a READ-ONLY database "
                            "through MCP tools.\n\n"

                            "Rules:\n"
                            "1. Never modify data.\n"
                            "2. Never invent data.\n"
                            "3. Inspect the schema "
                            "when necessary.\n"
                            "4. Use MCP tools to "
                            "retrieve database data.\n"
                            "5. Explain the result "
                            "clearly.\n"
                            "6. Access is restricted to "
                            "specific tables only."
                        )
                    }
                ],
            }
        ]

        while True:

            question = input(
                "You: "
            ).strip()

            if question.lower() in {
                "exit",
                "quit",
            }:
                break

            if not question:
                continue

            messages.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": question
                        }
                    ],
                }
            )

            # ----------------------------------
            # Agent loop
            # ----------------------------------

            while True:

                response = llm.generate(
                    messages,
                    tools,
                )

                candidate = (
                    response.candidates[0]
                )

                parts = (
                    candidate.content.parts
                )

                function_calls = []

                normal_text = []

                for part in parts:

                    if getattr(
                        part,
                        "function_call",
                        None,
                    ):

                        function_calls.append(
                            part.function_call
                        )

                    elif getattr(
                        part,
                        "text",
                        None,
                    ):

                        normal_text.append(
                            part.text
                        )

                # ----------------------------------
                # No tool call
                # ----------------------------------

                if not function_calls:

                    answer = "".join(
                        normal_text
                    )

                    print(
                        f"\nAssistant: "
                        f"{answer}\n"
                    )

                    messages.append(
                        {
                            "role": "model",
                            "parts": parts,
                        }
                    )

                    break

                # ----------------------------------
                # Add model response
                # ----------------------------------

                messages.append(
                    {
                        "role": "model",
                        "parts": parts,
                    }
                )

                # ----------------------------------
                # Execute MCP tools
                # ----------------------------------

                tool_response_parts = []

                for call in function_calls:

                    name = call.name

                    arguments = dict(
                        call.args
                    )

                    print(
                        f"\n[MCP CALL] "
                        f"{name}"
                    )

                    print(
                        json.dumps(
                            arguments,
                            indent=2,
                            default=str,
                        )
                    )

                    try:

                        result = (
                            await mcp_client.call_tool(
                                name,
                                arguments,
                            )
                        )

                        if (
                            result.structuredContent
                        ):

                            output = (
                                result.structuredContent
                            )

                        else:

                            output = {}

                            for item in (
                                result.content
                                or []
                            ):

                                if hasattr(
                                    item,
                                    "text",
                                ):

                                    output = (
                                        item.text
                                    )

                    except Exception as exc:

                        output = {
                            "error": str(exc)
                        }

                    tool_response_parts.append(
                        {
                            "function_response":
                            {
                                "name": name,

                                "response": {
                                    "result":
                                        output
                                },
                            }
                        }
                    )

                # ----------------------------------
                # Give MCP results to Gemini
                # ----------------------------------

                messages.append(
                    {
                        "role": "user",
                        "parts":
                            tool_response_parts,
                    }
                )


if __name__ == "__main__":

    asyncio.run(
        main()
    )