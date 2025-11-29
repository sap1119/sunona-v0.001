"""
OpenRouter LLM Provider
Supports all models available through OpenRouter API
"""

import os
import json
import asyncio
from typing import List, Dict, Optional, Any
import httpx
from sunona.helpers.logger_config import configure_logger

logger = configure_logger(__name__)


class OpenRouterLLM:
    """OpenRouter LLM provider with cost tracking"""
    
    def __init__(
        self,
        model: str = "openai/gpt-4o-mini",
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        api_key: Optional[str] = None,
        **kwargs
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://sunona.ai"),
                "X-Title": os.getenv("OPENROUTER_TITLE", "Sunona Voice AI")
            },
            timeout=60.0
        )
        
        logger.info(f"Initialized OpenRouter LLM with model: {model}")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Generate completion from OpenRouter"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty,
                "stream": stream
            }
            
            if stream:
                return await self._generate_stream(payload)
            else:
                return await self._generate_sync(payload)
        
        except Exception as e:
            logger.error(f"OpenRouter generation error: {e}")
            raise
    
    async def _generate_sync(self, payload: Dict) -> Dict:
        """Synchronous generation"""
        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Track token usage
        from sunona.helpers.call_tracker import get_current_tracker
        tracker = get_current_tracker()
        if tracker and result.get("usage"):
            tracker.track_llm_usage(
                input_tokens=result["usage"].get("prompt_tokens", 0),
                output_tokens=result["usage"].get("completion_tokens", 0)
            )
        
        return result["choices"][0]["message"]["content"]
    
    async def _generate_stream(self, payload: Dict):
        """Streaming generation"""
        total_input_tokens = 0
        total_output_tokens = 0
        
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        
                        # Track usage if available
                        if chunk.get("usage"):
                            total_input_tokens = chunk["usage"].get("prompt_tokens", 0)
                            total_output_tokens += chunk["usage"].get("completion_tokens", 0)
                        
                        # Yield content
                        if chunk["choices"][0].get("delta", {}).get("content"):
                            yield chunk["choices"][0]["delta"]["content"]
                    
                    except json.JSONDecodeError:
                        continue
        
        # Track total usage after stream completes
        from sunona.helpers.call_tracker import get_current_tracker
        tracker = get_current_tracker()
        if tracker and (total_input_tokens > 0 or total_output_tokens > 0):
            tracker.track_llm_usage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens
            )
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup"""
        try:
            asyncio.create_task(self.close())
        except:
            pass
