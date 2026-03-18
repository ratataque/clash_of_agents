import json
import pet_store_agent

def handler(event, context):
    """Lambda handler function"""
    prompt = event.get('prompt', 'A new user is asking about the price of Doggy Delights?')
    result = pet_store_agent.process_request(prompt)
    return json.dumps(result)
