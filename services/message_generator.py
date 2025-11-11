from typing import Dict, Optional
import logging
import re

from services.llm_utils import get_llm_candidates


logger = logging.getLogger(__name__)


def clean_message_content(message: str) -> str:
    """
    Remove meta-descriptions and explanatory text from generated messages.
    
    Removes patterns like:
    - "Here's a personalized follow-up email..."
    - "This email re-engages..."
    - "Here's a message that..."
    """
    # Remove common meta-description patterns at the start
    patterns = [
        r'^Here\'s\s+(?:a\s+)?(?:personalized\s+)?(?:follow-up\s+)?email\s+that\s+.*?:\s*',
        r'^This\s+email\s+.*?:\s*',
        r'^Here\'s\s+(?:a\s+)?message\s+that\s+.*?:\s*',
        r'^Here\'s\s+(?:a\s+)?personalized\s+.*?:\s*',
        r'^This\s+personalized\s+.*?:\s*',
    ]
    
    cleaned = message
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove any leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def generate_personalized_message(
    lead_data: Dict,
    campaign_project: str,
    offer_details: Optional[str] = None,
    llm_provider: str = "openai",
) -> str:
    """
    Generate a hyper-personalized message for a lead.

    Falls back between OpenAI -> Ollama automatically.
    """

    # Build prompt components
    lead_summary = lead_data.get("last_conversation_summary", "No previous conversation")
    unit_type = lead_data.get("unit_type", "N/A")
    budget_min = lead_data.get("budget_min")
    budget_max = lead_data.get("budget_max")
    project_enquired = lead_data.get("project_name", "N/A")

    budget_info = ""
    if budget_min or budget_max:
        budget_parts = []
        if budget_min:
            budget_parts.append(f"minimum {budget_min:,.0f}")
        if budget_max:
            budget_parts.append(f"maximum {budget_max:,.0f}")
        budget_info = f"Budget: {', '.join(budget_parts)}"

    prompt = f"""
You are a professional real estate sales associate crafting a personalized follow-up email to a potential buyer.

Use the information below to understand the lead's profile, preferences, and past discussion. Your goal is to re-engage them naturally by showing how {campaign_project} suits their lifestyle, needs, and interests.

Lead Information:
- Name: {lead_data.get('name', 'Valued Customer')}
- Family Size / Lifestyle Context: {lead_data.get('family_size', 'Not specified')}
- Previous Project Enquiry: {project_enquired}
- Unit Type Interest: {unit_type}
- {budget_info}
- Last Conversation Summary: {lead_summary}

Campaign Details:
- Project: {campaign_project}
- Offer Details: {offer_details if offer_details else 'No special offers'}

Write a concise, friendly, and engaging email body (2-3 short paragraphs) that:
1. Naturally builds on their previous interaction or requirements without repeating or thanking for past interest.
2. Highlights how {campaign_project} aligns with their needs (e.g., family size, lifestyle, unit type, budget, amenities, or location).
3. If offer details are provided, include them smoothly near the end before the call to action.
4. Ends with a clear and inviting call to action (e.g., scheduling a site visit, requesting floor plans, or having a quick call).
5. Uses a conversational and professional tone (like a real estate advisor, not a marketing bot).
6. Avoids greetings, closings, or signatures—only generate the email body text.

IMPORTANT: 
- Generate ONLY the email body content. Do NOT include any meta-descriptions, explanations, or introductory text like "Here's a personalized follow-up email..." or "This email re-engages...".
- Start directly with the email content as if you are writing the email itself.
- Do not describe what the email does or who it's for—just write the actual email content.

Focus on *appealing to their motivations* rather than their previous enquiry.
"""


    prefer_order = [llm_provider] if llm_provider else []
    llm_candidates = get_llm_candidates(temperature=0.7, prefer_order=prefer_order)

    errors = []

    for provider, llm in llm_candidates:
        try:
            response = llm.invoke(prompt)
            message = getattr(response, "content", str(response)).strip()
            # Clean any meta-descriptions that might have been included
            message = clean_message_content(message)
            logger.debug("Generated personalized message using %s provider", provider)
            return message
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning("LLM provider %s failed: %s", provider, exc)
            errors.append(f"{provider}: {exc}")
            continue

    logger.error("All LLM providers failed for message generation: %s", "; ".join(errors))

    # Fallback message if all LLMs fail
    offer_section = f"{offer_details}\n\n" if offer_details else ""
    return f"""Dear {lead_data.get('name', 'Valued Customer')},

Based on your interest in {unit_type} units and our previous conversation, we believe {campaign_project} could be a wonderful fit for your needs. The project offers thoughtfully designed spaces that align with your preferences and lifestyle.

{offer_section}We'd love to arrange a quick visit or share more details about the available options that suit your requirements. Please feel free to reach out at your convenience.

Best regards,
Sales Team"""


