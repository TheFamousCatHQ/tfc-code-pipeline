#!/usr/bin/env python3
"""
Module to validate a MASTER_COMPLEXITY_REPORT.json against its schema.
If validation fails, uses OpenRouter with gpt-4o-mini to fix the JSON.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Optional, Tuple

import jsonschema
import requests

# Set up logging
logger = logging.getLogger(__name__)

# Create a handler that writes to stderr
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        The loaded JSON data.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    logger.debug(f"Loading JSON file: {file_path}")
    with open(file_path, 'r') as f:
        return json.load(f)


def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate JSON data against a JSON schema.

    Args:
        data: The JSON data to validate.
        schema: The JSON schema.

    Returns:
        A tuple containing:
            - A boolean indicating whether validation was successful.
            - An error message if validation failed, None otherwise.
    """
    logger.info("Validating JSON data against schema...")
    try:
        jsonschema.validate(instance=data, schema=schema)
        logger.info("Validation successful!")
        return True, None
    except jsonschema.exceptions.ValidationError as e:
        logger.warning(f"Validation failed: {str(e)}")
        return False, str(e)
    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}")
        return False, f"Unexpected error during validation: {str(e)}"


def fix_json_with_openrouter(
    json_data: Dict[str, Any], 
    schema: Dict[str, Any], 
    error_message: str,
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Use OpenRouter API to fix the JSON data using gpt-4o-mini.

    Args:
        json_data: The invalid JSON data.
        schema: The JSON schema.
        error_message: The validation error message.
        api_key: OpenRouter API key. If None, tries to get from OPENROUTER_API_KEY env var.

    Returns:
        The fixed JSON data if successful, None otherwise.
    """
    logger.info("Attempting to fix JSON using OpenRouter API with gpt-4o-mini...")
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.error("No OpenRouter API key provided. Set OPENROUTER_API_KEY environment variable.")
            return None

    # Create the prompt
    prompt = f"""
I have a JSON object that fails validation against this schema:

```json
{json.dumps(schema, indent=2)}
```

The validation error is:
{error_message}

Here is the current JSON content:

```json
{json.dumps(json_data, indent=2)}
```

Please fix the JSON to make it conform to the schema.
Return only the fixed JSON with no additional explanation.
"""

    # Call OpenRouter API
    logger.info("Sending request to OpenRouter API...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openrouter/gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        logger.debug(f"Received response from OpenRouter: {result}")
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            
            # Try to parse the JSON from the response
            try:
                fixed_json = json.loads(content)
                logger.info("Successfully parsed fixed JSON from OpenRouter response")
                return fixed_json
            except json.JSONDecodeError:
                # Try to extract JSON if it's wrapped in markdown code blocks
                logger.debug("Failed to parse JSON directly, trying to extract from markdown")
                json_start = content.find("```json")
                if json_start != -1:
                    json_start += 7  # Skip ```json
                    json_end = content.find("```", json_start)
                    if json_end != -1:
                        json_str = content[json_start:json_end].strip()
                        try:
                            fixed_json = json.loads(json_str)
                            logger.info("Successfully extracted and parsed JSON from markdown code block")
                            return fixed_json
                        except json.JSONDecodeError:
                            logger.error("Failed to parse JSON extracted from markdown")
                            pass
                
                logger.error(f"Could not parse JSON from OpenRouter response")
                logger.debug(f"Raw response content: {content}")
                return None
        else:
            logger.error(f"Unexpected response format from OpenRouter")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling OpenRouter API: {e}")
        return None


def validate_and_fix_complexity_report(
    report_path: str, 
    schema_path: str, 
    output_path: Optional[str] = None,
    api_key: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Validate a complexity report against its schema and fix it if needed.

    Args:
        report_path: Path to the complexity report JSON file.
        schema_path: Path to the JSON schema file.
        output_path: Path to save the fixed JSON file. If None, overwrites the original.
        api_key: OpenRouter API key. If None, tries to get from OPENROUTER_API_KEY env var.

    Returns:
        A tuple containing:
            - A boolean indicating whether the operation was successful.
            - The path to the fixed file if successful, error message if not.
    """
    logger.info(f"Validating complexity report: {report_path}")
    logger.info(f"Using schema: {schema_path}")
    
    try:
        # Load the report and schema
        logger.info("Loading report and schema files...")
        report_data = load_json_file(report_path)
        schema_data = load_json_file(schema_path)
        
        # Validate against schema
        logger.info("Validating report against schema...")
        is_valid, error_message = validate_against_schema(report_data, schema_data)
        
        if is_valid:
            logger.info(f"Report is valid according to the schema")
            return True, report_path
        
        logger.warning(f"Validation failed: {error_message}")
        
        # Fix the JSON using OpenRouter
        logger.info("Attempting to fix the report using OpenRouter...")
        fixed_json = fix_json_with_openrouter(report_data, schema_data, error_message, api_key)
        
        if fixed_json is None:
            logger.error("Failed to fix the JSON using OpenRouter API")
            return False, "Failed to fix the JSON using OpenRouter API"
        
        # Validate the fixed JSON
        logger.info("Validating fixed JSON...")
        is_fixed_valid, fixed_error = validate_against_schema(fixed_json, schema_data)
        
        if not is_fixed_valid:
            logger.error(f"Fixed JSON still fails validation: {fixed_error}")
            return False, f"Fixed JSON still fails validation: {fixed_error}"
        
        # Save the fixed JSON
        if output_path is None:
            output_path = report_path
        
        logger.info(f"Saving fixed JSON to: {output_path}")
        with open(output_path, 'w') as f:
            json.dump(fixed_json, f, indent=2)
        
        logger.info("Successfully validated and fixed the complexity report")
        return True, output_path
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        return False, f"File not found: {str(e)}"
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {str(e)}")
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"


def main() -> int:
    """Command-line interface for validating and fixing complexity reports.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate a MASTER_COMPLEXITY_REPORT.json against its schema.")
    parser.add_argument("--report", required=True, help="Path to the MASTER_COMPLEXITY_REPORT.json file")
    parser.add_argument("--schema", default="master_complexity_report_schema.json", 
                        help="Path to the JSON schema file (default: master_complexity_report_schema.json)")
    parser.add_argument("--output", help="Path to save the fixed JSON file (default: overwrites the original)")
    parser.add_argument("--api-key", help="OpenRouter API key (default: uses OPENROUTER_API_KEY env var)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    success, result = validate_and_fix_complexity_report(
        args.report, 
        args.schema, 
        args.output,
        args.api_key
    )
    
    if success:
        logger.info(f"Success! Report saved to: {result}")
        return 0
    else:
        logger.error(f"Error: {result}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
