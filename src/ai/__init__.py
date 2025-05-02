import logging
import os
from typing import Type, TypeVar, Optional

import httpx
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

load_dotenv()

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# API Endpoints
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Model Configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "google/gemini-2.5-flash-preview")
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1024"))
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0"))

# OpenRouter Configuration
OPENROUTER_X_TITLE = os.getenv("OPENROUTER_X_TITLE", "UsualSuspects")
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "https://www.thefamouscat.com")

# Define a generic type for the output model
T = TypeVar('T')

logger = logging.getLogger(__name__)


def create_agent(output_type: Type[T], system_prompt: str, model: Optional[str] = None) -> Agent:
    """
    Create a PydanticAI agent with the specified output type and system prompt using OpenRouter.

    Args:
        output_type: The Pydantic model to use for output
        system_prompt: The system prompt for the agent
        model: The model to use (default: from environment or anthropic/claude-3.5-sonnet)

    Returns:
        A configured PydanticAI agent
    """
    # Use the specified model or get from environment
    model_name = model or DEFAULT_MODEL

    # Create a custom HTTP client with the required headers
    # Create headers for OpenRouter
    headers = {}
    if OPENROUTER_HTTP_REFERER:
        # OpenRouter expects 'HTTP-Referer' and 'Referer' headers
        headers["HTTP-Referer"] = OPENROUTER_HTTP_REFERER
    if OPENROUTER_X_TITLE:
        # OpenRouter expects 'X-Title' header
        headers["X-Title"] = OPENROUTER_X_TITLE

    # Log the headers for debugging
    logger.info(f"OpenRouter headers for create_agent: {headers}")

    # Create a custom HTTP client with default headers
    http_client = httpx.AsyncClient(headers=headers)

    # Create the OpenAI provider with the custom HTTP client
    provider = OpenAIProvider(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        http_client=http_client
    )

    # Create OpenAI model with OpenRouter provider
    openai_model = OpenAIModel(model_name, provider=provider)

    # Create and return the agent
    return Agent(
        openai_model,
        model_settings=ModelSettings(
            max_tokens=DEFAULT_MAX_TOKENS,
            temperature=DEFAULT_TEMPERATURE
        ),
        output_type=output_type,
        system_prompt=system_prompt,
    )
