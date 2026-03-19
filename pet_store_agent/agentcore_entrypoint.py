from bedrock_agentcore.runtime import BedrockAgentCoreApp
import pet_store_agent
import json

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    """AgentCore handler function"""
    prompt = payload.get('prompt', 'A new user is asking about the price of Doggy Delights?')
    result = pet_store_agent.process_request(prompt)
    # Ensure runtime always returns a JSON object, not a JSON string.
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"status": "Error", "message": "We are sorry for the technical difficulties..."}
    return result

if __name__ == "__main__":
    app.run()
