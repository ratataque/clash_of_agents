import healthcare_agent

def handler(event, context):
    """Lambda handler function"""
    prompt = event.get('prompt', 'Check coverage for patient MBR_001 for diabetes medication metformin')
    return healthcare_agent.process_request(prompt)
