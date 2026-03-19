import importlib


def handler(event, context):
    """Lambda handler function"""
    prompt = event.get(
        "prompt", "A new user is asking about the price of Doggy Delights?"
    )
    try:
        orchestrator = importlib.import_module("pet_store_agent.orchestrator")
    except ImportError:
        orchestrator = importlib.import_module("orchestrator")
    return orchestrator.process_request(prompt)
