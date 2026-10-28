import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class LLMClient:
    def __init__(self):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL")

        if not openai_api_key:
            raise ValueError("A variável de ambiente OPENAI_API_KEY não foi encontrada")

        if not self.model:
            raise ValueError("A variável de ambiente OPENAI_MODEL não foi encontrada.")

        self.client = OpenAI(api_key=openai_api_key)

    def generate_response(self, instructions: str, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=prompt,
        )

        return response.output_text
