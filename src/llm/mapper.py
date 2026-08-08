import json
import re
from pathlib import Path

import google.generativeai as genai

from config.settings import settings


class GeminiMapper:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY no configurada en .env")
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)
        self._schema = self._load_schema()
        self._system_prompt_template = self._load_system_prompt()

    def _load_schema(self) -> dict:
        schema_path = settings.template_schema_path
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)

    def _load_system_prompt(self) -> str:
        prompt_path = settings.system_prompt_path
        with open(prompt_path, encoding="utf-8") as f:
            return f.read()

    def map_to_template(self, extracted_text: str) -> dict:
        prompt = self._system_prompt_template.format(
            schema=json.dumps(self._schema, ensure_ascii=False, indent=2),
            extracted_text=extracted_text,
        )
        response = self._model.generate_content(prompt)
        return self._parse_json_response(response.text)

    def _parse_json_response(self, raw_text: str) -> dict:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        return json.loads(cleaned)
