import json
import logging
import re
from datetime import date, datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.core.prompts import (
    EMAIL_GENERATION_PROMPT,
    ENTITY_EXTRACTION_PROMPT,
    JSON_FORMATTING_PROMPT,
    SUMMARIZATION_PROMPT,
    VALIDATION_PROMPT,
)
from app.schemas.interaction import ExtractedInteraction

logger = logging.getLogger(__name__)
PLACEHOLDER_GROQ_KEYS = {'', 'your_groq_api_key', 'your_real_groq_key', 'changeme'}
DEPRECATED_GROQ_MODELS = {
    'gemma2-9b-it': 'llama-3.1-8b-instant',
    'llama-3.1-70b-versatile': 'llama-3.3-70b-versatile',
}
MATERIAL_WORDS = {
    'brochure', 'brochures', 'leaflet', 'leaflets', 'sample', 'samples',
    'study', 'studies', 'pdf', 'material', 'materials', 'presentation', 'presentations',
}


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = None
        api_key = self.settings.groq_api_key.strip()
        model = DEPRECATED_GROQ_MODELS.get(self.settings.groq_model, self.settings.groq_model)
        if model != self.settings.groq_model:
            logger.warning(
                'Groq model %s is deprecated. Using %s instead.',
                self.settings.groq_model,
                model,
            )
        if api_key and api_key not in PLACEHOLDER_GROQ_KEYS:
            self.client = ChatGroq(api_key=api_key, model=model, temperature=0.2)

    async def stream_summary(self, conversation: str):
        extracted = self._fallback_extract(conversation)
        if not self.client:
            yield self._build_conversational_reply(extracted)
            return

        try:
            async for chunk in self.client.astream([
                SystemMessage(content=SUMMARIZATION_PROMPT),
                HumanMessage(content=conversation),
            ]):
                if chunk.content:
                    yield chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        except Exception as exc:
            logger.warning('Groq streaming failed, using fallback extraction: %s', exc)
            yield self._build_conversational_reply(extracted)

    async def summarize(self, conversation: str) -> str:
        extracted = self._fallback_extract(conversation)
        if not self.client:
            return extracted.summary
        try:
            response = await self.client.ainvoke([
                SystemMessage(content=SUMMARIZATION_PROMPT),
                HumanMessage(content=conversation),
            ])
            return response.content if isinstance(response.content, str) else str(response.content)
        except Exception as exc:
            logger.warning('Groq summarization failed, using fallback extraction: %s', exc)
            return extracted.summary

    async def extract_entities(self, conversation: str) -> ExtractedInteraction:
        if not self.client:
            return self._fallback_extract(conversation)

        try:
            response = await self.client.ainvoke([
                SystemMessage(content=f'{ENTITY_EXTRACTION_PROMPT}\n{JSON_FORMATTING_PROMPT}'),
                HumanMessage(content=conversation),
            ])
            payload = self._parse_json(response.content)
            return ExtractedInteraction(**payload)
        except Exception as exc:
            logger.warning('Groq entity extraction failed, using fallback extraction: %s', exc)
            return self._fallback_extract(conversation)

    async def validate_record(self, record: dict) -> list[str]:
        required_fields = ['doctor_name', 'interaction_type', 'discussion_notes', 'summary']
        errors = [f'{field} is required' for field in required_fields if not record.get(field)]
        if self.client:
            try:
                response = await self.client.ainvoke([
                    SystemMessage(content=f'{VALIDATION_PROMPT}\n{JSON_FORMATTING_PROMPT}'),
                    HumanMessage(content=json.dumps(record)),
                ])
                llm_payload = self._parse_json(response.content)
                errors.extend(llm_payload.get('errors', []))
            except Exception as exc:
                logger.warning('Groq validation failed, using local validation only: %s', exc)
        return list(dict.fromkeys(errors))

    async def generate_email(self, context: dict) -> dict:
        if not self.client:
            subject = f'Follow-up after discussion with {context["doctor_name"]}'
            body = f"Dear Dr. {context['doctor_name'].replace('Dr ', '').strip()},\n\nThank you for your time. As discussed, here is a concise follow-up on {', '.join(context['products_discussed'])}.\n\nKey takeaway: {context['summary']}\n\nNext step: {context['call_to_action']}\n\nBest regards,\nAI CRM Medical Representative"
            return {'subject': subject, 'body': body}

        try:
            response = await self.client.ainvoke([
                SystemMessage(content=f'{EMAIL_GENERATION_PROMPT}\n{JSON_FORMATTING_PROMPT}'),
                HumanMessage(content=json.dumps(context)),
            ])
            return self._parse_json(response.content)
        except Exception as exc:
            logger.warning('Groq email generation failed, using fallback email: %s', exc)
            subject = f'Follow-up after discussion with {context["doctor_name"]}'
            body = f"Dear Dr. {context['doctor_name'].replace('Dr ', '').strip()},\n\nThank you for your time. As discussed, here is a concise follow-up on {', '.join(context['products_discussed'])}.\n\nKey takeaway: {context['summary']}\n\nNext step: {context['call_to_action']}\n\nBest regards,\nAI CRM Medical Representative"
            return {'subject': subject, 'body': body}

    def _parse_json(self, content: object) -> dict:
        if isinstance(content, list):
            content = ''.join(str(item) for item in content)
        if not isinstance(content, str):
            content = str(content)
        content = content.strip().replace('```json', '').replace('```', '')
        return json.loads(content)

    def _extract_doctor_name(self, conversation: str) -> str:
        stop_words = {
            'today', 'yesterday', 'tomorrow', 'next', 'last', 'this',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'the', 'a', 'an', 'with', 'at', 'in', 'on', 'from', 'and', 'about', 'to', 'for', 'who', 'whom', 'regarding',
        }
        name_part = r'([A-Za-z]+(?:[ \t]+[A-Za-z]+){0,2})'
        met_patterns = [
            rf'(?:i[ \t]+)?met[ \t]+with[ \t]+(?:dr\.?|doctor)[ \t]+{name_part}',
            rf'(?:i[ \t]+)?met[ \t]+(?:dr\.?|doctor)[ \t]+{name_part}',
        ]
        met_matches: list[str] = []
        for pattern in met_patterns:
            for match in re.finditer(pattern, conversation, re.IGNORECASE):
                parts = [part for part in match.group(1).split() if part.lower() not in stop_words]
                if parts:
                    met_matches.append(' '.join(part.title() for part in parts[:3]))
        if met_matches:
            return f'Dr. {met_matches[-1]}'

        patterns = [
            rf'(?:dr\.?|doctor)[ \t]+{name_part}',
        ]
        for pattern in patterns:
            match = re.search(pattern, conversation, re.IGNORECASE)
            if match:
                parts = [part for part in match.group(1).split() if part.lower() not in stop_words]
                if not parts:
                    continue
                name = ' '.join(part.title() for part in parts[:3])
                return f'Dr. {name}'
        return 'Unknown Doctor'

    def _build_summary(self, conversation: str, doctor_name: str, products: list[str]) -> str:
        cleaned = conversation.strip()
        if len(cleaned) <= 120:
            return cleaned
        product_text = ', '.join(products) if products else 'the discussion'
        if doctor_name != 'Unknown Doctor':
            return f'Met {doctor_name} and discussed {product_text}.'
        return f'{cleaned[:117]}...'

    def _build_conversational_reply(self, extracted: ExtractedInteraction) -> str:
        if len(extracted.discussion_notes.strip()) < 12:
            return (
                "Thanks for checking in! Tell me about your HCP meeting — who you met, "
                "what you discussed, and any follow-up needed."
            )

        products = ', '.join(extracted.products_discussed) if extracted.products_discussed else 'the discussion'
        follow_up = f' Follow-up noted for {extracted.follow_up_date}.' if extracted.follow_up_date else ''

        if extracted.doctor_name == 'Unknown Doctor':
            return (
                f"Thanks! I've captured your notes about {products}.{follow_up} "
                "Could you also share the HCP name so I can complete the log?"
            )

        return (
            f"Got it! I've logged your meeting with {extracted.doctor_name} "
            f"and noted the discussion on {products}.{follow_up} "
            "Please review the fields on the left and click Save when ready."
        )

    def _fallback_extract(self, conversation: str) -> ExtractedInteraction:
        lower = conversation.lower()
        doctor_name = self._extract_doctor_name(conversation)

        interaction_type = 'visit'
        if 'call' in lower:
            interaction_type = 'call'
        elif 'email' in lower:
            interaction_type = 'email'
        elif 'conference' in lower:
            interaction_type = 'conference'

        products = []
        for known in ['ozempic', 'rybelsus', 'wegovy', 'dupixent', 'jardiance', 'trulicity', 'prodo-x']:
            if known in lower:
                products.append(known.title())
        product_match = re.search(r'product\s+([A-Za-z0-9-]+)', conversation, re.IGNORECASE)
        if product_match and product_match.group(1).lower() not in MATERIAL_WORDS:
            products.append(f'Product {product_match.group(1).title()}')
        if not products and len(conversation.strip()) >= 12 and self._has_specific_discussion(conversation):
            products = ['General Portfolio']

        follow_up = None
        if 'next friday' in lower:
            today = datetime.utcnow().date()
            delta = (4 - today.weekday()) % 7 or 7
            follow_up = today + timedelta(days=delta)
        elif 'monday' in lower:
            today = datetime.utcnow().date()
            delta = (0 - today.weekday()) % 7 or 7
            follow_up = today + timedelta(days=delta)

        meeting_date, meeting_time = self._extract_meeting_datetime(conversation)
        materials = self._extract_materials(conversation)
        sentiment = self._extract_sentiment(conversation) or 'neutral'
        outcome = self._extract_outcome(conversation)
        topic = self._extract_discussion_topic(conversation)
        if outcome:
            summary = outcome
        elif topic:
            summary = topic
        else:
            summary = self._build_summary(conversation, doctor_name, products)
        return ExtractedInteraction(
            doctor_name=doctor_name,
            hospital=self._extract_hospital_from_text(conversation),
            interaction_type=interaction_type,
            interaction_date=meeting_date,
            interaction_time=meeting_time,
            discussion_notes=conversation.strip(),
            summary=summary,
            products_discussed=products,
            materials_shared=materials,
            follow_up_date=follow_up,
            follow_up_actions=self._extract_follow_up_actions(conversation),
            sentiment=sentiment,
            status='validated',
        )

    def _extract_hospital_from_text(self, conversation: str) -> str:
        patterns = [
            r'at\s+([A-Za-z][A-Za-z\s&]+(?:Clinic|Hospital|Center|Care))',
        ]
        for pattern in patterns:
            match = re.search(pattern, conversation, re.IGNORECASE)
            if match:
                return ' '.join(match.group(1).split()).title()
        return ''

    def _extract_meeting_datetime(self, conversation: str) -> tuple[date | None, str | None]:
        lower = conversation.lower()
        today = datetime.now().date()
        meeting_date: date | None = None
        meeting_time: str | None = None

        if re.search(r'\btoday\b', lower):
            meeting_date = today
        elif re.search(r'\byesterday\b', lower):
            meeting_date = today - timedelta(days=1)

        time_match = re.search(r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            meridiem = time_match.group(3)
            if meridiem == 'pm' and hour < 12:
                hour += 12
            if meridiem == 'am' and hour == 12:
                hour = 0
            meeting_time = f'{hour:02d}:{minute:02d}'

        return meeting_date, meeting_time

    def _extract_materials(self, conversation: str) -> list[str]:
        lower = conversation.lower()
        materials: list[str] = []
        patterns = [
            (r'\bclinical\s+stud(?:y|ies)\b', 'Clinical Study'),
            (r'\bshared\s+(?:the\s+)?(?:product\s+)?brochures?\b', 'Brochures'),
            (r'\b(brochures?)\b', 'Brochures'),
            (r'\bshared\s+(?:the\s+)?(?:product\s+)?leaflets?\b', 'Leaflets'),
            (r'\b(leaflets?)\b', 'Leaflets'),
            (r'\b(samples?)\b', 'Samples'),
        ]
        for pattern, label in patterns:
            if re.search(pattern, lower) and label not in materials:
                materials.append(label)
        return materials

    def _extract_sentiment(self, conversation: str) -> str | None:
        lower = conversation.lower()
        negative_signals = [
            'not interested', 'no interest', 'declined', 'decline follow', 'refused',
            'rejected', 'negative sentiment', 'sentiment was negative', 'uninterested', 'not keen',
        ]
        if any(signal in lower for signal in negative_signals):
            return 'negative'
        positive_signals = [
            'positive sentiment', 'sentiment was positive', 'very positive',
            'interested in', 'keen to', 'requested follow', 'positive',
        ]
        if any(signal in lower for signal in positive_signals):
            return 'positive'
        if 'neutral' in lower:
            return 'neutral'
        return None

    def _extract_outcome(self, conversation: str) -> str:
        lower = conversation.lower()
        reply_match = re.search(
            r'(?:doctor|dr\.?|hcp|she|he)\s+(?:replied|said|responded)\s+that\s+(.+?)(?:\.|$)',
            conversation,
            re.IGNORECASE,
        )
        if reply_match:
            reply = reply_match.group(1).strip().rstrip('.')
            if len(reply) >= 8:
                return reply[0].upper() + reply[1:] + '.'
        if 'not interested' in lower and 'declined' in lower:
            return 'HCP is not interested in the product at this time and declined a follow-up discussion.'
        if 'not interested' in lower:
            return 'HCP is not interested in the product at this time.'
        if 'declined' in lower and 'follow' in lower:
            return 'HCP declined a follow-up discussion.'
        concern_match = re.search(
            r'(?:doctor|dr\.?|hcp|he|she)\s+(?:expressed|raised|shared)\s+concerns?\s+about\s+(.+?)(?:\.|,\s*and|\s+and\s+stated|$)',
            conversation,
            re.IGNORECASE,
        )
        if concern_match:
            concern = concern_match.group(1).strip().rstrip('.')
            outcome = f'HCP expressed concerns about {concern}.'
            if 'satisfied' in lower and 'current medication' in lower:
                outcome += ' HCP is satisfied with current medication.'
            if 'no commitment' in lower or 'without any commitment' in lower:
                outcome += ' No commitment for a future meeting.'
            return outcome
        if 'satisfied' in lower and 'current medication' in lower:
            outcome = 'HCP is satisfied with current medication.'
            if 'no commitment' in lower or 'without any commitment' in lower:
                outcome += ' No commitment for a future meeting.'
            return outcome
        return ''

    def _extract_discussion_topic(self, conversation: str) -> str:
        patterns = [
            r'discussed\s+(.+?)(?:\.|,|\band\b|\bthe sentiment\b|\bi shared\b|$)',
            r'talked about\s+(.+?)(?:\.|,|\band\b|\bthe sentiment\b|\bi shared\b|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, conversation, re.IGNORECASE)
            if match:
                topic = match.group(1).strip().rstrip('.')
                if len(topic) >= 4:
                    return topic[0].upper() + topic[1:] + ('.' if not topic.endswith('.') else '')
        return ''

    def _extract_follow_up_actions(self, conversation: str) -> str:
        patterns = [
            r'follow[- ]?up(?: action[s]?)?[:\s]+(.+?)(?:\.|$)',
            r'next step[s]?[:\s]+(.+?)(?:\.|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, conversation, re.IGNORECASE)
            if match:
                action = match.group(1).strip().rstrip('.')
                if len(action) >= 6:
                    return action[0].upper() + action[1:]
        return ''

    def _has_specific_discussion(self, conversation: str) -> bool:
        lower = conversation.lower()
        return any(token in lower for token in ['discuss', 'met', 'visit', 'call', 'product', 'trial', 'ozempic'])
