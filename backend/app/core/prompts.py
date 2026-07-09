SUMMARIZATION_PROMPT = """
You are an expert life-sciences CRM assistant.
Summarize the interaction in 3 concise bullet points with clinical and commercial relevance.
Capture physician intent, product context, and any clear follow-up request.
"""

ENTITY_EXTRACTION_PROMPT = """
Extract the following entities from the conversation and return strict JSON:
{
  "doctor_name": string,
  "hospital": string,
  "interaction_type": "visit" | "call" | "email" | "conference",
  "interaction_date": string | null,
  "interaction_time": string | null,
  "discussion_notes": string,
  "summary": string,
  "products_discussed": string[],
  "materials_shared": string[],
  "follow_up_date": string | null,
  "follow_up_actions": string,
  "sentiment": string
}
Use ISO date format when possible. Infer interaction type conservatively.
Extract meeting date as YYYY-MM-DD and meeting time as HH:MM in 24-hour format when mentioned.
If the user says "today", "yesterday", or gives a time like "3pm", infer those values.
"""

VALIDATION_PROMPT = """
Validate the extracted HCP interaction record. Return strict JSON:
{
  "is_valid": boolean,
  "errors": string[]
}
The record must include a doctor name, meaningful summary, interaction type, and discussion notes.
"""

JSON_FORMATTING_PROMPT = """
Return only valid JSON. No markdown fences, prose, comments, or explanations.
"""

EMAIL_GENERATION_PROMPT = """
Write a professional follow-up email for a healthcare professional.
Keep the tone evidence-based, concise, and compliant for life sciences communication.
Return strict JSON:
{
  "subject": string,
  "body": string
}
"""
