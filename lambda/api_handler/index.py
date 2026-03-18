"""
Lambda handler for API Gateway requests
"""
import json
import os
from typing import Dict, Any
from agent import create_agent


# Initialize agent once (Lambda container reuse)
agent = None


def get_agent():
    """Lazy initialization of agent"""
    global agent
    if agent is None:
        agent = create_agent()
    return agent


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway proxy integration.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway proxy response
    """
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        user_message = body.get("message", "")
        
        if not user_message:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Missing 'message' in request body"}),
            }
        
        # Get or initialize agent
        agent_instance = get_agent()
        
        # Process request
        response = agent_instance(user_message)
        
        # Return response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "message": response.message,
                "timestamp": context.get_remaining_time_in_millis(),
            }),
        }
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Internal server error"}),
        }
