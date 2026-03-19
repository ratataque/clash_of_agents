from bedrock_agentcore.runtime import BedrockAgentCoreApp
from starlette.responses import JSONResponse
import json
import logging

# Configure logging FIRST
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info("===== ENTRYPOINT MODULE LOADING =====")

try:
    import pet_store_agent
    logger.info("✅ pet_store_agent imported successfully")
except Exception as e:
    logger.error(f"❌ FAILED to import pet_store_agent: {e}", exc_info=True)
    raise

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    """AgentCore handler function"""
    payload_keys = list(payload.keys()) if isinstance(payload, dict) else []
    logger.info(f"===== HANDLER CALLED ===== payload keys: {payload_keys}")
    
    try:
        if isinstance(payload, dict):
            prompt = payload.get("prompt") or payload.get("input") or payload.get("message")
        else:
            prompt = None
        if not isinstance(prompt, str) or not prompt.strip():
            prompt = "A new user is asking about the price of Doggy Delights?"
        logger.info(f"Extracted prompt (first 100 chars): {prompt[:100]}")
        
        result = pet_store_agent.process_request(prompt)
        logger.info(f"✅ process_request returned: type={type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'NOT_DICT'}")
        
        # Log the actual result content for debugging
        logger.info(f"RESULT CONTENT: {json.dumps(result, indent=None)}")
        
        if not isinstance(result, dict):
            result = {
                "status": "Error",
                "message": "We are sorry, we are currently experiencing technical difficulties.",
                "customerType": "Guest",
                "items": [],
                "shippingCost": 0.0,
                "petAdvice": "",
                "subtotal": 0.0,
                "additionalDiscount": 0.0,
                "total": 0.0,
            }
        return JSONResponse(content=result, media_type="application/json")
    except Exception as e:
        logger.error(f"❌ HANDLER EXCEPTION: {e}", exc_info=True)
        # Return error response
        return JSONResponse(content={
            "status": "Error",
            "message": "We are sorry, we are currently experiencing technical difficulties.",
            "customerType": "Guest",
            "items": [],
            "shippingCost": 0.0,
            "petAdvice": "",
            "subtotal": 0.0,
            "additionalDiscount": 0.0,
            "total": 0.0
        }, media_type="application/json")

if __name__ == "__main__":
    app.run()
