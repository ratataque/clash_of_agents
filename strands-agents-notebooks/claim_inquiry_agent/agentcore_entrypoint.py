from bedrock_agentcore.runtime import BedrockAgentCoreApp
import healthcare_agent

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    """AgentCore handler function"""
    prompt = payload.get('prompt', 'Check coverage for patient MBR_001 for diabetes medication metformin')
    return healthcare_agent.process_request(prompt)

if __name__ == "__main__":
    app.run()
