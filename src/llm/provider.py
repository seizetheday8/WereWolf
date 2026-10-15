import json
import os
from dotenv import load_dotenv
from src.utils.prompt_loader import load_prompt
from openai import AsyncOpenAI
load_dotenv()

class LLMProvider:
    def __init__(self, model: str|None, api_key: str|None, base_url: str | None = None):
        self.model = model or os.getenv("MODEL") or "deepseek-v4-pro"
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("API_KEY"),
            base_url=base_url or os.getenv("BASE_URL")
        )
    
    async def chat(self, messages: list[dict]) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        content = response.choices[0].message.content
        return content or ""
    
    async def chat_json(self,messages: list[dict]) -> dict:
        # 硬约束模型必须返回JSON格式，否则重试，最多3次
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            if response.choices[0].message.content is None:
                return {}
            return json.loads(response.choices[0].message.content)
        except Exception:
            pass 

        raw = await self.chat(messages)
        if raw:
            return json.loads(raw)
        return {}
