from bedrock_agentcore.runtime import BedrockAgentCoreApp
import json
import pet_store_agent

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    """AgentCore handler function"""
    prompt = payload.get('prompt', 'A new user is asking about the price of Doggy Delights?')
    result = pet_store_agent.process_request(prompt)
    return json.dumps(result)

if __name__ == "__main__":
    app.run()
