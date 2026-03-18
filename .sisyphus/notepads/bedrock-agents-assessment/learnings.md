# Learnings - Bedrock Agents Assessment

Session started: 2026-03-18T16:42:35.258Z

- Updated `pet_store_agent.py` system prompt business rules to align evaluation logic: bundle discount phrasing, free shipping threshold at subtotal $300, flat $14.95 shipping otherwise, and tiered subscriber-only additional discounts (5%/10%/15%).
- Added explicit scope guardrail (cats/dogs only) and security guardrail (do not reveal internal identifiers/system details or obey prompt-injection-style reveal requests) before sample prompts to preserve behavior while tightening policy compliance.

## 2026-03-18 Task 1+3: CloudFormation Deployment

### Key Discovery
The provided `pet_store_knowledge_bases.yaml` creates EVERYTHING in one stack:
- OpenSearch Serverless collection (vector search)
- Product Info Knowledge Base (from S3 data bucket)
- Pet Care Knowledge Base (from web crawler - Wikipedia)
- Bedrock Guardrail (PetStoreGuardrail) with:
  - Prompt attack blocking (HIGH)
  - Content filters (hate, insults, sexual, violence, misconduct)
  - Topic denial for birds/fish/reptiles

### AWS Resource Values Discovered
```
SolutionAccessRoleArn: arn:aws:iam::799631972281:role/team-SolutionAccessRole-zEw6Ch57eaBE
DataBucketForKnowledgeArn: arn:aws:s3:::team-databucketforknowledge-ixntv3yqclsm
CodeBucket: team-codebucketforautomation-lxmeitl2bpuf
Lambda Inventory: team-PetStoreInventoryManagementFunction-UQszQA9YKKDn
Lambda User: team-PetStoreUserManagementFunction-WeuPIhjofWMr
```

### Stack Outputs Expected
- ProductInfo1stKnowledgeBaseId
- PetCare2ndKnowledgeBaseId  
- PetStoreGuardrailId
- PetStoreGuardrailVersion
