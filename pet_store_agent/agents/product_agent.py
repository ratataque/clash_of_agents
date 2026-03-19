"""
Product Agent - Match products from knowledge base and check inventory.
Specialized agent focused on product catalog retrieval and availability.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from strands import Agent
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

PRODUCT_PROMPT = """You are a product matching specialist for a pet store. Your job is to match customer product queries to our catalog.

You will be given:
1. A product query from the customer
2. Retrieved results from our product knowledge base

Your task:
1. Analyze the KB results to find the BEST matching product
2. Extract key product details: product_id, price, name/description
3. Determine if the product is in-scope (dog or cat products ONLY)

**Product Scope Rules:**
- IN SCOPE: Dog products, cat products, pet accessories for dogs/cats
- OUT OF SCOPE: Hamster, bird, reptile, fish products, or anything not for dogs/cats

**Output Format (JSON only, no markdown):**
{
  "match_found": true|false,
  "product_id": "DD006" or null,
  "product_name": "Doggy Delights" or null,
  "price": 54.99 or null,
  "description": "brief description" or null,
  "in_scope": true|false,
  "reason": "explanation for match decision or why out of scope"
}

**Rules:**
- If KB results are empty or score too low: match_found=false
- If product is for hamster/bird/reptile/fish: in_scope=false, match_found=false
- Extract product_id from KB results (look for codes like DD006, BP010, CM001)
- Extract price as float
- If multiple matches, choose the highest score result
- Return ONLY valid JSON

Examples:

Input Query: "Doggy Delights"
KB Results: [{"score": 0.85, "content": "Product: Doggy Delights (DD006), Price: $54.99, Premium dog treats..."}]
Output:
{
  "match_found": true,
  "product_id": "DD006",
  "product_name": "Doggy Delights",
  "price": 54.99,
  "description": "Premium dog treats",
  "in_scope": true,
  "reason": "High confidence match for dog product"
}

Input Query: "hamster food"
KB Results: [{"score": 0.75, "content": "Hamster Munchies, great for hamsters..."}]
Output:
{
  "match_found": false,
  "product_id": null,
  "product_name": null,
  "price": null,
  "description": null,
  "in_scope": false,
  "reason": "Hamster products are out of scope - we only carry dog and cat products"
}

Now analyze:"""


def create_product_agent() -> Agent:
    """
    Create the Product Agent with product matching model.

    Returns:
        Configured Product Agent
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        max_tokens=1024,
        streaming=False,
    )

    agent = Agent(
        model=model,
        system_prompt=PRODUCT_PROMPT,
        tools=[],  # No tools - receives pre-retrieved KB data
    )

    return agent


def match_product(
    product_query: str, kb_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Match product query against KB retrieval results.

    Args:
        product_query: Product search query from customer
        kb_results: List of KB retrieval results with score, content, document_id

    Returns:
        Dict with:
            - match_found: bool
            - product_id: str | None
            - product_name: str | None
            - price: float | None
            - description: str | None
            - in_scope: bool
            - reason: str

    Example:
        kb_results = [{"score": 0.85, "content": "Doggy Delights (DD006)..."}]
        match = match_product("Doggy Delights", kb_results)
    """
    try:
        logger.info(
            f"Product Agent: matching query '{product_query}' against {len(kb_results)} KB results"
        )

        # Format KB results for agent
        kb_text = "\n\n".join(
            [
                f"[Result {i + 1}] Score: {r['score']:.2f}\n{r['content']}"
                for i, r in enumerate(kb_results)
            ]
        )

        if not kb_text.strip():
            kb_text = "No results found in knowledge base."

        prompt = f"Product Query: {product_query}\n\nKB Results:\n{kb_text}"

        agent = create_product_agent()
        response = agent(prompt)

        match_data = json.loads(str(response))

        logger.info(
            f"Product Agent: match_found={match_data.get('match_found')}, in_scope={match_data.get('in_scope')}"
        )
        return match_data

    except json.JSONDecodeError as e:
        logger.error(f"Product Agent: failed to parse JSON response: {str(e)}")
        return {
            "match_found": False,
            "product_id": None,
            "product_name": None,
            "price": None,
            "description": None,
            "in_scope": True,
            "reason": f"Failed to parse product match response: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Product Agent: unexpected error: {str(e)}")
        return {
            "match_found": False,
            "product_id": None,
            "product_name": None,
            "price": None,
            "description": None,
            "in_scope": True,
            "reason": f"Product matching error: {str(e)}",
        }
