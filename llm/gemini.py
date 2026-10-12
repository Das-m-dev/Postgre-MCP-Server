import json
import os
from typing import Any

from google import genai
from google.genai import types


class GeminiLLM:

    def __init__(self):

        api_key = os.environ.get(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        )

        self.client = genai.Client(
            api_key=api_key
        )

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ):

        response = self.client.models.generate_content(
            model=self.model,

            contents=messages,

            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        function_declarations=tools
                    )
                ],

                temperature=0,
            ),
        )

        return response