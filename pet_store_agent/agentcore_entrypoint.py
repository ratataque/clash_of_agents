from bedrock_agentcore.runtime import BedrockAgentCoreApp
import importlib

app = BedrockAgentCoreApp()


@app.entrypoint
def handler(payload):
    """AgentCore handler function"""
    prompt = payload.get(
        "prompt", "A new user is asking about the price of Doggy Delights?"
    )
    try:
        orchestrator = importlib.import_module("pet_store_agent.orchestrator")
    except ImportError:
        orchestrator = importlib.import_module("orchestrator")
    return orchestrator.process_request(prompt)


if __name__ == "__main__":
    app.run()
