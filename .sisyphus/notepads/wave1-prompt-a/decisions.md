## Decisions

- Added a dedicated unavailable+pet-advice override in `pet_store_agent.py` prompt sections (`<requirements>`, `<flow_b>`) rather than altering tool logic, to keep behavior driven by orchestrator instructions and preserve existing tool contracts.
- Updated `run_tests.py::test_p` to validate the new contractual output shape for this scenario: `status=Accept`, `customerType=Subscribed`, non-empty `petAdvice`, valid JSON.
