import os
import json
import boto3
import logging
from strands import tool

logger = logging.getLogger(__name__)


@tool
def get_insurance_tier_details(tier_name: str) -> dict:
    """
    Get detailed insurance tier/plan information including copays, deductibles, and coverage.
    
    Args:
        tier_name: Insurance tier name. Supports ACA tier names (e.g., "Gold", "Silver")
                   and legacy names (e.g., "Gold Plus", "Silver Standard")
    
    Returns:
        JSON string with comprehensive ACA-compliant tier information
        
    Sample Response Body:
    {
        "tier_name": "Gold",
        "plan_name": "Comprehensive Health Gold",
        "actuarial_value": "80%",
        "financial_structure": {
            "annual_deductible": 1500.00,
            "out_of_pocket_max": 8700.00,
            "coinsurance_patient_responsibility": "20%"
        },
        "copay_structure": {
            "generic_prescription": 15.00,
            "specialty_prescription": 150.00
        },
        "prior_authorization_required": ["specialty_drugs", "imaging_mri"]
    }
    
    Note: Legacy tier names are automatically mapped to ACA tiers.
    """
    logger.info(f"get_insurance_tier_details called with input: tier_name={tier_name}")
    
    lambda_client = boto3.client('lambda')
    
    payload = {
        "function": "getInsuranceTierDetails",
        "parameters": [{"name": "tier_name", "value": tier_name}]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=os.environ.get('SYSTEM_FUNCTION_2_NAME'),
            Payload=json.dumps(payload)
        )

        lambda_response = json.loads(response['Payload'].read())
        actual_data = json.loads(lambda_response['response']['functionResponse']['responseBody']['TEXT']['body'])
        
        result = {"status": "success", "content": [{"text": json.dumps(actual_data)}]}
        logger.info(f"get_insurance_tier_details returning result: {result}")
        return result
    except Exception as e:
        logger.error(f"get_insurance_tier_details() error: {str(e)}")
        return {"status": "error", "content": [{"text": f"Failed to get insurance tier details: {str(e)}"}]}


@tool
def check_prior_authorization(tier_name: str, service_type: str, service_name: str = None) -> dict:
    """
    Check if prior authorization is required for a specific service or medication.
    
    Args:
        tier_name: Insurance tier name (e.g., "Gold", "Silver", or legacy names)
        service_type: Type of service (e.g., "specialty_drugs", "imaging_mri", "surgery_elective")
        service_name: Optional specific name of drug/procedure (e.g., "Jardiance")
    
    Returns:
        JSON string with prior authorization status and tier-specific requirements
        
    Sample Response Body:
    {
        "tier_name": "Silver",
        "service_type": "specialty_drugs",
        "service_name": "Jardiance",
        "prior_auth_required": true,
        "matched_rule": "specialty_drugs",
        "tier_prior_auth_list": ["specialty_drugs", "imaging_mri", "imaging_ct"],
        "message": "Prior authorization IS REQUIRED for specialty_drugs (Jardiance)"
    }
    
    Note: Prior authorization requirements vary by tier (Platinum has fewest, Bronze has most).
    """
    logger.info(f"check_prior_authorization called: tier={tier_name}, service={service_type}, name={service_name}")
    
    lambda_client = boto3.client('lambda')
    
    parameters = [
        {"name": "tier_name", "value": tier_name},
        {"name": "service_type", "value": service_type}
    ]
    if service_name:
        parameters.append({"name": "service_name", "value": service_name})
    
    payload = {"function": "checkPriorAuthorization", "parameters": parameters}
    
    try:
        response = lambda_client.invoke(
            FunctionName=os.environ.get('SYSTEM_FUNCTION_2_NAME'),
            Payload=json.dumps(payload)
        )
        
        lambda_response = json.loads(response['Payload'].read())
        actual_data = json.loads(lambda_response['response']['functionResponse']['responseBody']['TEXT']['body'])
        
        result = {"status": "success", "content": [{"text": json.dumps(actual_data)}]}
        logger.info(f"check_prior_authorization returning result: {result}")
        return result
    except Exception as e:
        logger.error(f"check_prior_authorization() error: {str(e)}")
        return {"status": "error", "content": [{"text": f"Failed to check prior authorization: {str(e)}"}]}
