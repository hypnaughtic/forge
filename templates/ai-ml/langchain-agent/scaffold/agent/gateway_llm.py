"""
GatewayLLM — LangChain-compatible LLM that routes through llm-gateway.

CRITICAL: This class is the ONLY way LLM calls should be made in this
template. Do NOT use ChatOpenAI, ChatAnthropic, or any other LangChain
native provider. All calls must go through llm-gateway for centralized
rate limiting, cost tracking, and audit logging.
"""

from typing import Any, Iterator, List, Optional

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent.config import settings


def _message_to_dict(message: BaseMessage) -> dict:
    """Convert a LangChain message to llm-gateway format."""
    if isinstance(message, SystemMessage):
        role = "system"
    elif isinstance(message, HumanMessage):
        role = "user"
    elif isinstance(message, AIMessage):
        role = "assistant"
    else:
        role = "user"

    return {"role": role, "content": message.content}


class GatewayLLM(BaseChatModel):
    """Chat model that routes all requests through llm-gateway.

    This class implements LangChain's BaseChatModel interface so it can
    be used as a drop-in replacement anywhere LangChain expects an LLM.
    Under the hood, it sends requests to llm-gateway instead of directly
    to an LLM provider.

    Usage:
        from agent.gateway_llm import GatewayLLM

        llm = GatewayLLM(model="gpt-4")
        response = llm.invoke("Hello, world!")

    NEVER do this:
        from langchain_openai import ChatOpenAI  # WRONG — bypasses gateway
        llm = ChatOpenAI(model="gpt-4")          # WRONG
    """

    model: str = "gpt-4"
    temperature: float = 0.0
    max_tokens: int = 4096
    gateway_url: str = ""
    gateway_api_key: str = ""

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        if not self.gateway_url:
            self.gateway_url = settings.llm_gateway_url
        if not self.gateway_api_key:
            self.gateway_api_key = settings.llm_gateway_api_key

    @property
    def _llm_type(self) -> str:
        return "gateway-llm"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Send messages to llm-gateway and return the response.

        This method converts LangChain messages to the gateway format,
        sends them via HTTP, and converts the response back to LangChain
        message types.
        """
        # Build the gateway request payload
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [_message_to_dict(m) for m in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if stop:
            payload["stop"] = stop

        # Send request to llm-gateway
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.gateway_url}/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.gateway_api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        # Parse the gateway response
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Convert to LangChain format
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

    @property
    def _identifying_params(self) -> dict:
        return {
            "model": self.model,
            "gateway_url": self.gateway_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
