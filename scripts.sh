#!/bin/bash
# Development helper scripts for Strands Agent project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment
activate_venv() {
	if [ -d ".venv" ]; then
		source .venv/bin/activate
	else
		echo -e "${RED}Virtual environment not found. Run: python3 -m venv .venv${NC}"
		exit 1
	fi
}

# Install dependencies
install() {
	echo -e "${GREEN}Installing dependencies...${NC}"
	activate_venv
	pip install -r requirements.txt
	echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Test agent locally
test_agent() {
	echo -e "${GREEN}Testing agent locally...${NC}"
	activate_venv
	python agent/agent.py
}

# Run tests
run_tests() {
	echo -e "${GREEN}Running tests...${NC}"
	activate_venv
	pytest "$@"
}

# CDK operations
cdk_synth() {
	echo -e "${GREEN}Synthesizing CDK stacks...${NC}"
	cdk synth
	echo -e "${GREEN}✓ CDK synthesis successful${NC}"
}

cdk_diff() {
	echo -e "${YELLOW}Checking CDK differences...${NC}"
	cdk diff
}

cdk_deploy() {
	echo -e "${GREEN}Deploying CDK stacks...${NC}"
	cdk deploy --all "$@"
}

cdk_destroy() {
	echo -e "${RED}Destroying CDK stacks...${NC}"
	cdk destroy --all "$@"
}

# Check AWS configuration
check_aws() {
	echo -e "${GREEN}Checking AWS configuration...${NC}"

	# Check AWS credentials
	if ! aws sts get-caller-identity &>/dev/null; then
		echo -e "${RED}✗ AWS credentials not configured${NC}"
		echo "Run: aws configure"
		exit 1
	fi

	ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
	REGION=$(aws configure get region)

	echo -e "${GREEN}✓ AWS Account: ${ACCOUNT_ID}${NC}"
	echo -e "${GREEN}✓ AWS Region: ${REGION}${NC}"

	# Check Bedrock model access
	echo -e "${YELLOW}Checking Bedrock model access...${NC}"
	if aws bedrock list-foundation-models --region us-west-2 &>/dev/null; then
		echo -e "${GREEN}✓ Bedrock API accessible${NC}"
	else
		echo -e "${RED}✗ Bedrock API not accessible${NC}"
		echo "Enable model access in AWS Console → Bedrock → Model access"
	fi
}

# View logs
logs() {
	LOG_GROUP="/aws/strands-agent/clash-of-agents"
	echo -e "${GREEN}Tailing CloudWatch logs: ${LOG_GROUP}${NC}"
	aws logs tail "${LOG_GROUP}" --follow
}

# Get stack outputs
outputs() {
	STACK_NAME="${1:-ClashOfAgents-AgentCoreStack}"
	echo -e "${GREEN}Stack outputs for: ${STACK_NAME}${NC}"
	aws cloudformation describe-stacks \
		--stack-name "${STACK_NAME}" \
		--query 'Stacks[0].Outputs' \
		--output table
}

# Clean up
clean() {
	echo -e "${YELLOW}Cleaning build artifacts...${NC}"
	rm -rf cdk.out .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Show help
show_help() {
	cat <<EOF
${GREEN}Strands Agent Development Helper${NC}

Usage: ./scripts.sh <command> [options]

Commands:
  install           Install Python dependencies
  test-agent        Test agent locally
  test [args]       Run pytest with optional arguments
  
  cdk-synth         Synthesize CDK stacks
  cdk-diff          Show CDK stack differences
  cdk-deploy [args] Deploy CDK stacks
  cdk-destroy       Destroy CDK stacks
  
  check-aws         Verify AWS configuration
  logs              Tail CloudWatch logs
  outputs [stack]   Show CloudFormation stack outputs
  clean             Clean build artifacts
  
  help              Show this help message

Examples:
  ./scripts.sh install
  ./scripts.sh test-agent
  ./scripts.sh test tests/unit/
  ./scripts.sh cdk-deploy
  ./scripts.sh logs
  ./scripts.sh outputs ClashOfAgents-SecurityStack

EOF
}

# Main command dispatcher
case "${1:-help}" in
install)
	install
	;;
test-agent)
	test_agent
	;;
test)
	shift
	run_tests "$@"
	;;
cdk-synth)
	cdk_synth
	;;
cdk-diff)
	cdk_diff
	;;
cdk-deploy)
	shift
	cdk_deploy "$@"
	;;
cdk-destroy)
	shift
	cdk_destroy "$@"
	;;
check-aws)
	check_aws
	;;
logs)
	logs
	;;
outputs)
	shift
	outputs "$@"
	;;
clean)
	clean
	;;
help | --help | -h)
	show_help
	;;
*)
	echo -e "${RED}Unknown command: $1${NC}"
	show_help
	exit 1
	;;
esac
