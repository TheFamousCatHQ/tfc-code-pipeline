import os
import re
import xml.etree.ElementTree as ET
from typing import Type, TypeVar, Optional, Dict

import httpx
import openai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from logging_utils import get_logger

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
OPENROUTER_X_TITLE = os.getenv("OPENROUTER_X_TITLE", "CodePipeline")
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "https://www.thefamouscat.com")

# Define a generic type for the output model
T = TypeVar('T')

logger = get_logger()


class FileComponentCategory(BaseModel):
    """
    Pydantic model for mapping file paths to component categories.
    """
    mapping: Dict[str, str]


def create_agent(output_type: Type[T], system_prompt: str, model: Optional[str] = None, retries: int = 1, output_retries: Optional[int] = None) -> Agent:
    """
    Create a PydanticAI agent with the specified output type and system prompt using OpenRouter.

    Args:
        output_type: The Pydantic model to use for output
        system_prompt: The system prompt for the agent
        model: The model to use (default: from environment or anthropic/claude-3.5-sonnet)
        retries: Number of retries for validation (default: 1)
        output_retries: Number of retries for output validation (default: None)

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
        retries=retries,
        output_retries=output_retries,
    )


def categorize_files_openrouter(file_paths: list[str], prompt: str, model: str = "google/gemini-2.5-flash-preview") -> \
        dict[str, str]:
    """
    Use OpenRouter via the OpenAI API to categorize file paths into components.

    Args:
        file_paths: List of file paths to categorize.
        prompt: The prompt to send to the LLM.
        model: The model to use (default: gemini-2.5-flash-preview).

    Returns:
        A mapping of file path to component name.
    """
    import json as _json
    openai.api_key = OPENROUTER_API_KEY
    openai.base_url = OPENROUTER_BASE_URL

    file_list_str = "\n".join(f"- {p}" for p in file_paths)
    full_prompt = (
        f"{prompt}\n"
        f"Here is a list of file paths:\n{file_list_str}\n"
        "Please categorize each file path into a high-level component (User Interface, API Services, Core Functionality, Utilities, Data Models, Business Services, Persistence Layer, etc.) "
        "and return a JSON object mapping file path to component name, e.g. {\"src/api/foo.py\": \"API Services\", ...}. "
        "Return only the JSON object."
    )
    logger.info(f"Calling OpenRouter via OpenAI API with model {model} and prompt: {full_prompt}")
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are an expert software architect."},
                  {"role": "user", "content": full_prompt}],
        max_tokens=1024,
        temperature=0.0,
    )
    logger.info(f"OpenRouter response: {response}")
    content = response.choices[0].message.content.strip()
    try:
        # Try to parse the first JSON object in the response
        start = content.find('{')
        end = content.rfind('}') + 1
        json_str = content[start:end]
        mapping = _json.loads(json_str)
        if not isinstance(mapping, dict):
            raise ValueError("Response JSON is not a dict")
        return mapping
    except Exception as e:
        logger.error(f"Failed to parse OpenRouter response as JSON: {e}\nResponse content: {content}")
        return {}


def categorize_files_openai_json(file_paths: list[str], prompt: str, model: str = "gpt-4.1-nano-2025-04-14") -> dict[
    str, str]:
    """
    Use OpenAI GPT-4o to categorize file paths into components, enforcing strict JSON output.

    Args:
        file_paths: List of file paths to categorize.
        prompt: The prompt to send to the LLM.
        model: The model to use (default: gpt-4o).

    Returns:
        A mapping of file path to component name.
    """
    import json as _json
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    file_list_str = "\n".join(f"- {p}" for p in file_paths)
    full_prompt = (
        f"{prompt}\n"
        f"Here is a list of file paths:\n{file_list_str}\n"
        "Please categorize each file path into a high-level component (User Interface, API Services, Core Functionality, Utilities, Data Models, Business Services, Persistence Layer, etc.) "
        "and return a JSON object mapping file path to component name, e.g. {\"src/api/foo.py\": \"API Services\", ...}. "
        "Return only the JSON object."
    )
    logger.debug(f"Calling OpenAI GPT-4o with model {model} and prompt: {full_prompt}")
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are an expert software architect."},
                  {"role": "user", "content": full_prompt}],
        max_tokens=1024,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    logger.debug(f"OpenAI GPT-4o response: {response}")
    content = response.choices[0].message.content.strip()
    try:
        mapping = _json.loads(content)
        if not isinstance(mapping, dict):
            raise ValueError("Response JSON is not a dict")
        return mapping
    except Exception as e:
        logger.error(f"Failed to parse OpenAI GPT-4o response as JSON: {e}\nResponse content: {content}")
        return {}


def fix_cdata_sections(xml_string: str) -> str:
    def replace_cdata(match):
        content = match.group(1)
        # Don't trim valid content - instead properly handle CDATA sections
        # by ensuring they have the correct format
        return f'<![CDATA[{content}]]>'

    # Use a more precise regex pattern that correctly matches CDATA sections
    pattern = r'<!\[CDATA\[(.*?)(?:\]\]>)'
    fixed_xml = re.sub(pattern, replace_cdata, xml_string, flags=re.DOTALL)
    return fixed_xml


def xml_from_string(param: str) -> ET.XML:
    xml_start = param.index("<")
    xml_end = param.rfind(">")
    xml_string = param[xml_start:xml_end + 1]
    xml_string = fix_cdata_sections(xml_string)
    soup = BeautifulSoup(xml_string, "xml")
    xml = ET.fromstring(str(soup))
    return xml


def categorize_files_openrouter_xml(file_paths: list[str], model: str = "google/gemini-2.5-flash-preview") \
        -> Dict[str, str]:
    """
    Use OpenRouter directly to categorize file paths into components, returning XML and parsing it.

    Args:
        file_paths: List of file paths to categorize.
        model: The model to use (default: gemini-2.5-flash-preview).

    Returns:
        A mapping of file path to component name.
    """

    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://www.thefamouscat.com"),
        "X-Title": os.getenv("OPENROUTER_X_TITLE", "CodePipeline"),
        "Content-Type": "application/json"
    }

    file_list_str = "\n".join(f"- {p}" for p in file_paths)
    xml_example = '''<files>\n  <file path="src/api/foo.py">API Services</file>\n  <file path="src/core/bar.py">Core Functionality</file>\n  <file path="src/utils/baz.py">Utilities</file>\n</files>'''
    prompt = (
        f"You are an expert software architect.\n"
        f"Here is a list of file paths:\n{file_list_str}\n"
        "Please categorize each file path into a high-level component (User Interface, API Services, Core Functionality, Utilities, Data Models, Business Services, Persistence Layer, etc.).\n"
        "Return the result as XML in the following format:\n"
        f"{xml_example}\n"
        "Only return the <files> XML, nothing else."
    )

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an expert software architect."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024 * 100,
        "temperature": 0.0
    }

    logger.info(f"Calling OpenRouter with XML prompt for {len(file_paths)} files.")
    with httpx.Client() as client:
        response = client.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=60)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

    # Parse XML
    mapping = {}
    try:
        root = xml_from_string(content)
        for file_elem in root.findall("file"):
            path = file_elem.attrib.get("path")
            component = file_elem.text.strip() if file_elem.text else ""
            if path:
                mapping[path] = component
    except Exception as e:
        logger.error(f"Failed to parse XML response: {e}\nResponse content: {content}", exc_info=True)
    return mapping
