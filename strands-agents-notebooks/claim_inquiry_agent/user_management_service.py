import os
import json
import boto3
import logging
from strands import tool

logger = logging.getLogger(__name__)

@tool
def get_patient_by_member_id(member_id: str) -> dict:
    """
    Get patient information by member ID.
    
    Args:
        member_id: Patient member ID (e.g., "MBR_001")
    
    Returns:
        JSON string with patient profile and insurance tier name
        
    Sample Response Body:
    {
        "member_id": "MBR_001",
        "name": "Sarah Johnson",
        "email": "sarah.j@healthmail.com",
        "date_of_birth": "1985-06-15",
        "insurance_tier": "Gold Plus",
        "coverage_status": "active",
        "coverage_start_date": "2025-01-01",
        "coverage_end_date": "2025-12-31",
        "last_updated": "2025-11-01T10:30:00Z"
    }
    
    Note: Use get_insurance_tier_details() to get detailed tier information.
    """
    logger.info(f"get_patient_by_member_id called with input: member_id={member_id}")
    
    lambda_client = boto3.client('lambda')
    
    payload = {
        "function": "getPatientByMemberId",
        "parameters": [{"name": "member_id", "value": member_id}]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=os.environ.get('SYSTEM_FUNCTION_1_NAME'),
            Payload=json.dumps(payload)
        )
        
        lambda_response = json.loads(response['Payload'].read())
        actual_data = json.loads(lambda_response['response']['functionResponse']['responseBody']['TEXT']['body'])

        result = {"status": "success", "content": [{"text": json.dumps(actual_data)}]}
        logger.info(f"get_patient_by_member_id returning result: {result}")
        return result
    except Exception as e:
        logger.error(f"get_patient_by_member_id() error: {str(e)}")
        return {"status": "error", "content": [{"text": f"Failed to get patient information: {str(e)}"}]}


@tool
def get_patient_by_email(email: str) -> dict:
    """
    Get patient information by email address.
    
    Args:
        email: Patient email address
    
    Returns:
        JSON string with patient profile and insurance tier name
        
    Sample Response Body:
    {
        "member_id": "MBR_001",
        "name": "Sarah Johnson",
        "email": "sarah.j@healthmail.com",
        "date_of_birth": "1985-06-15",
        "insurance_tier": "Gold Plus",
        "coverage_status": "active",
        "coverage_start_date": "2025-01-01",
        "coverage_end_date": "2025-12-31",
        "last_updated": "2025-11-01T10:30:00Z"
    }
    
    Note: Use get_insurance_tier_details() to get detailed tier information.
    """
    logger.info(f"get_patient_by_email called with input: email={email}")
    
    lambda_client = boto3.client('lambda')
    
    payload = {
        "function": "getPatientByEmail",
        "parameters": [{"name": "email", "value": email}]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=os.environ.get('SYSTEM_FUNCTION_1_NAME'),
            Payload=json.dumps(payload)
        )
        
        lambda_response = json.loads(response['Payload'].read())
        actual_data = json.loads(lambda_response['response']['functionResponse']['responseBody']['TEXT']['body'])
        
        result = {"status": "success", "content": [{"text": json.dumps(actual_data)}]}
        logger.info(f"get_patient_by_email returning result: {result}")
        return result
    except Exception as e:
        logger.error(f"get_patient_by_email() error: {str(e)}")
        return {"status": "error", "content": [{"text": f"Failed to get patient information: {str(e)}"}]}
