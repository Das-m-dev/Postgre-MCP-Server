import json
import os
import time
from typing import Any

from google import genai
from google.genai import errors, types

RETRYABLE_CODES = {429, 500, 503, 504}


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

        fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "")
        self.fallback_models = [
            m.strip() for m in fallbacks.split(",") if m.strip()
        ]

        self.client = genai.Client(
            api_key=api_key
        )

    def _call(self, model, messages, tools):
        return self.client.models.generate_content(
            model=model,
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

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_attempts: int = 4,
    ):
        models = [self.model] + self.fallback_models
        last_error = None

        for model in models:
            delay = 2

            for attempt in range(1, max_attempts + 1):
                try:
                    return self._call(model, messages, tools)

                except errors.APIError as e:
                    code = getattr(e, "code", None)

                    # Non-retryable (bad request, auth, etc.): fail immediately
                    if code not in RETRYABLE_CODES:
                        raise

                    last_error = e
                    print(
                        f"[{model}: {code}, attempt {attempt}/{max_attempts}]"
                    )

                    if attempt < max_attempts:
                        time.sleep(delay)
                        delay *= 2

            print(f"[{model} exhausted, trying next model]")

        raise last_error