"""
Shared utilities for AWS Lambda invocations.
Centralizes boto3 Lambda client usage and nested response parsing.
"""

import os
import json
import boto3
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def invoke_lambda(
    function_name: str, function_type: str, parameters: list[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Invoke AWS Lambda function and parse the nested response structure.

    Args:
        function_name: Lambda function name or ARN
        function_type: Function identifier (e.g., "getUserById", "getInventory")
        parameters: List of parameter dicts with "name" and "value" keys

    Returns:
        Dict with:
            - status: "success" or "error"
            - data: Parsed response data (if success)
            - error: Error message (if error)

    Example:
        result = invoke_lambda(
            function_name="PetStoreUser",
            function_type="getUserById",
            parameters=[{"name": "user_id", "value": "usr_001"}]
        )
        if result["status"] == "success":
            user_data = result["data"]
    """
    lambda_client = boto3.client("lambda")

    payload = {"function": function_type, "parameters": parameters}

    try:
        logger.info(f"Invoking Lambda {function_name} with function={function_type}")

        response = lambda_client.invoke(
            FunctionName=function_name, Payload=json.dumps(payload)
        )

        lambda_response = json.loads(response["Payload"].read())

        # Parse nested response structure:
        # lambda_response['response']['functionResponse']['responseBody']['TEXT']['body']
        nested_body = (
            lambda_response.get("response", {})
            .get("functionResponse", {})
            .get("responseBody", {})
            .get("TEXT", {})
            .get("body")
        )

        if not nested_body:
            logger.error(
                f"Lambda {function_name} returned unexpected structure: {lambda_response}"
            )
            return {
                "status": "error",
                "error": f"Unexpected Lambda response structure from {function_name}",
            }

        actual_data = json.loads(nested_body)

        logger.info(f"Lambda {function_name} invocation succeeded")
        return {"status": "success", "data": actual_data}

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error from Lambda {function_name}: {str(e)}")
        return {
            "status": "error",
            "error": f"Failed to parse Lambda response: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Lambda {function_name} invocation failed: {str(e)}")
        return {"status": "error", "error": f"Lambda invocation failed: {str(e)}"}


def get_user_by_id(user_id: str) -> Dict[str, Any]:
    """
    Get user information by user ID.

    Args:
        user_id: User ID to look up

    Returns:
        Dict with status and data (user object) or error
    """
    function_name = os.environ.get("SYSTEM_FUNCTION_2_NAME")
    if not function_name:
        return {
            "status": "error",
            "error": "SYSTEM_FUNCTION_2_NAME environment variable not set",
        }

    return invoke_lambda(
        function_name=function_name,
        function_type="getUserById",
        parameters=[{"name": "user_id", "value": user_id}],
    )


def get_user_by_email(user_email: str) -> Dict[str, Any]:
    """
    Get user information by email address.

    Args:
        user_email: User email to look up

    Returns:
        Dict with status and data (user object) or error
    """
    function_name = os.environ.get("SYSTEM_FUNCTION_2_NAME")
    if not function_name:
        return {
            "status": "error",
            "error": "SYSTEM_FUNCTION_2_NAME environment variable not set",
        }

    return invoke_lambda(
        function_name=function_name,
        function_type="getUserByEmail",
        parameters=[{"name": "user_email", "value": user_email}],
    )


def get_inventory(product_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Get inventory information for a product.

    Args:
        product_code: Product code to check (optional)

    Returns:
        Dict with status and data (inventory object) or error
    """
    function_name = os.environ.get("SYSTEM_FUNCTION_1_NAME")
    if not function_name:
        return {
            "status": "error",
            "error": "SYSTEM_FUNCTION_1_NAME environment variable not set",
        }

    parameters = []
    if product_code:
        parameters.append({"name": "product_code", "value": product_code})

    return invoke_lambda(
        function_name=function_name, function_type="getInventory", parameters=parameters
    )
