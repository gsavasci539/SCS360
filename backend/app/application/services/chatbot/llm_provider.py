"""LLM Provider abstraction for chatbot intent detection."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Structured response from LLM."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate chat completion."""
        pass

    @abstractmethod
    async def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_schema: Dict[str, Any],
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Generate structured JSON completion."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        timeout_seconds: float = 12.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout_seconds,
                    max_retries=0,
                )
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                raise ImportError("OpenAI package is required for OpenAIProvider")
        return self._client

    async def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate chat completion using OpenAI API."""
        try:
            client = self._get_client()
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = await client.chat.completions.create(**kwargs)
            
            choice = response.choices[0]
            content = choice.message.content or ""
            
            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                finish_reason=choice.finish_reason,
            )
            
        except Exception as e:
            logger.exception(f"OpenAI API error: {e}")
            raise

    async def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_schema: Dict[str, Any],
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Generate structured JSON completion using OpenAI API."""
        import json
        
        # Add JSON format instruction to system message
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else {}
        original_system = system_msg.get("content", "")
        
        schema_instruction = (
            "\n\nIMPORTANT: You must respond with valid JSON only. "
            f"Use this schema: {json.dumps(response_schema, indent=2)}"
        )
        
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = original_system + schema_instruction
        else:
            messages.insert(0, {
                "role": "system",
                "content": "You are a helpful assistant." + schema_instruction
            })
        
        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            json_mode=True,
        )
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {response.content}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")


class OllamaProvider(LLMProvider):
    """Ollama provider for free local LLM support."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 12.0,
    ):
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client for Ollama."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                # Ollama is compatible with OpenAI API format
                self._client = AsyncOpenAI(
                    api_key="ollama",  # Ollama doesn't need a real API key
                    base_url=self.base_url,
                    timeout=self.timeout_seconds,
                    # Default SDK retries can turn a short timeout into a long wait.
                    max_retries=0,
                )
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                raise ImportError("OpenAI package is required for OllamaProvider")
        return self._client

    async def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate chat completion using Ollama API."""
        try:
            client = self._get_client()
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            # Ollama doesn't support response_format, rely on prompt instructions
            response = await client.chat.completions.create(**kwargs)
            
            choice = response.choices[0]
            content = choice.message.content or ""
            
            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                finish_reason=choice.finish_reason,
            )
            
        except Exception as e:
            logger.exception(f"Ollama API error: {e}")
            raise

    async def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_schema: Dict[str, Any],
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Generate structured JSON completion using Ollama API."""
        # Add JSON format instruction to system message
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else {}
        original_system = system_msg.get("content", "")
        
        # Simplified instruction for Ollama
        schema_instruction = (
            "\n\nIMPORTANT: Respond with valid JSON only. "
            "Do not include markdown code blocks, do not include the schema in your response. "
            "Only return the JSON object with the actual values."
        )
        
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = original_system + schema_instruction
        else:
            messages.insert(0, {
                "role": "system",
                "content": "You are a helpful assistant." + schema_instruction
            })
        
        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            json_mode=False,  # Ollama doesn't support this, rely on prompt
        )
        
        # Clean the response - remove markdown code blocks if present
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {content}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing without API calls."""

    async def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate mock response."""
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        return LLMResponse(
            content=f"Mock response to: {last_user_msg}",
            model="mock-gpt-4",
            tokens_used=100,
            finish_reason="stop",
        )

    async def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_schema: Dict[str, Any],
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Generate mock structured response."""
        # Return a valid ChatbotIntent structure
        result = {
            "intent": "GENERAL",
            "student_id": None,
            "teacher_id": None,
            "subject": None,
            "period": None,
            "operation": None,
            "search_text": None,
            "confidence": 0.5
        }
        return result


def get_llm_provider(
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    model: str = "llama3.2",
    base_url: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> LLMProvider:
    """Factory function to get LLM provider instance."""
    
    if provider_type == "openai":
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAI provider")
        return OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    
    elif provider_type == "ollama":
        # Ollama is free and local, no API key needed
        ollama_base_url = base_url or "http://localhost:11434"
        return OllamaProvider(
            model=model,
            base_url=ollama_base_url,
            timeout_seconds=timeout_seconds,
        )
    
    elif provider_type == "mock":
        return MockLLMProvider()
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
