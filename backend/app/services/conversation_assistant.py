import re
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import ChatHistoryMessage
from app.schemas.interaction import ExtractedInteraction
from app.services.hcp_service import HCPService
from app.services.interaction_service import InteractionService
from app.services.llm_service import LLMService
from app.tools.next_best_action_tool import NextBestActionTool

MATERIAL_WORDS = {
    'brochure', 'brochures', 'leaflet', 'leaflets', 'sample', 'samples',
    'study', 'studies', 'pdf', 'material', 'materials', 'presentation', 'presentations',
}

GREETING_PATTERNS = (
    r'^(hi|hello|hey|hii|hola|good morning|good afternoon|good evening)[!.?\s]*$',
)
CONFIRM_PATTERNS = (
    r'^(yes|y|confirm|confirmed|correct|log it|save|proceed|ok|okay|looks good|go ahead)([!.?\s].*)?$',
)

FIELD_QUESTIONS = {
    'HCP Name': 'Who was the healthcare professional you met?',
    'Hospital/Clinic': 'Which hospital or clinic was the meeting at?',
    'Meeting Date & Time': 'When did you meet the HCP? Please share the date and time of the interaction.',
    'Interaction Type': 'What type of interaction was it — visit, call, email, or conference?',
    'Products Discussed': 'Which products or therapies did you discuss?',
    'Discussion Summary': 'Could you share a brief summary of what was discussed?',
}


class ConversationAssistantService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm_service = LLMService()
        self.next_action_tool = NextBestActionTool(session)

    async def process(
        self,
        content: str,
        history: list[ChatHistoryMessage] | None = None,
        save: bool = False,
    ) -> dict:
        history = history or []
        conversation = self._build_conversation(history, content)

        if self._is_greeting_only(content):
            reply = (
                "Log interaction details here (e.g., 'Met an HCP, discussed product efficacy, "
                "positive sentiment, shared brochure') or ask for help."
            )
            return self._result(reply, self._empty_draft(), [], None)

        extracted = await self._extract_from_conversation(conversation)
        self._apply_defaults(extracted)
        missing = self._missing_fields(extracted)
        awaiting_confirmation = self._awaiting_confirmation(history)

        if (self._is_confirmation(content) or save) and awaiting_confirmation and not missing:
            saved = await self._save_interaction(extracted)
            reply = '✅ Interaction logged successfully.'
            extracted.status = 'logged'
            return self._result(reply, extracted, [], saved)

        if not missing:
            reply = self._build_success_reply(extracted)
            extracted.status = 'populated'
            try:
                next_actions = await self.next_action_tool.run(
                    extracted.doctor_name,
                    extracted.products_discussed,
                    extracted.summary,
                )
            except Exception:
                next_actions = self._default_follow_up_actions(extracted)
            if next_actions and not extracted.follow_up_actions and extracted.sentiment != 'negative':
                extracted.follow_up_actions = next_actions[0]
            elif extracted.sentiment == 'negative' and not extracted.follow_up_actions:
                extracted.follow_up_actions = 'No immediate follow-up; document HCP decline and revisit only if new evidence emerges.'
            return self._result(reply, extracted, next_actions, None)

        reply = self._build_missing_field_reply(extracted, missing)
        extracted.status = 'draft'
        return self._result(reply, extracted, [], None)

    async def stream_reply(self, content: str, history: list[ChatHistoryMessage] | None = None, save: bool = False):
        result = await self.process(content, history, save)
        yield result['message']

    async def _extract_from_conversation(self, conversation: str) -> ExtractedInteraction:
        latest_user_message = self._latest_user_message(conversation)
        extracted = await self.llm_service.extract_entities(latest_user_message)
        extracted.summary = await self.llm_service.summarize(latest_user_message)
        extracted.hospital = self._extract_hospital(latest_user_message) or extracted.hospital
        extracted.discussion_notes = self._build_discussion_notes(conversation)
        regex_doctor = self.llm_service._extract_doctor_name(latest_user_message)
        if regex_doctor and regex_doctor != 'Unknown Doctor':
            extracted.doctor_name = regex_doctor
        elif extracted.doctor_name in {'', 'Unknown Doctor'}:
            extracted.doctor_name = regex_doctor
        if not extracted.products_discussed:
            extracted.products_discussed = []
        if extracted.products_discussed == ['General Portfolio'] and not self._has_known_product(latest_user_message):
            extracted.products_discussed = []
        meeting_date, meeting_time = self._extract_meeting_datetime(latest_user_message)
        if meeting_date:
            extracted.interaction_date = meeting_date
        if meeting_time:
            extracted.interaction_time = meeting_time
        regex_materials = self._extract_materials(latest_user_message)
        llm_materials = extracted.materials_shared or []
        extracted.materials_shared = list(dict.fromkeys(regex_materials + llm_materials))
        extracted.sentiment = self._extract_sentiment(latest_user_message) or extracted.sentiment
        outcome = self._extract_outcome(latest_user_message)
        topic = self._extract_discussion_topic(latest_user_message)
        if outcome:
            extracted.summary = outcome
        elif topic:
            extracted.summary = topic
        if not extracted.products_discussed:
            extracted.products_discussed = self._extract_products_from_text(latest_user_message)
        follow_up_date = self._extract_follow_up_date(latest_user_message)
        if follow_up_date:
            extracted.follow_up_date = follow_up_date
        follow_up_actions = self._extract_follow_up_actions(latest_user_message)
        if extracted.sentiment == 'negative':
            extracted.follow_up_actions = (
                'No immediate follow-up; document HCP decline and revisit only if new evidence emerges.'
            )
        elif follow_up_actions:
            extracted.follow_up_actions = follow_up_actions
        elif any(signal in latest_user_message.lower() for signal in ['no commitment', 'without any commitment']):
            extracted.follow_up_actions = 'No immediate follow-up; revisit only if new safety or efficacy data becomes available.'
        return extracted

    async def _save_interaction(self, extracted: ExtractedInteraction):
        hcp_service = HCPService(self.session)
        await hcp_service.get_or_create_hcp(extracted.doctor_name, extracted.hospital)
        if extracted.interaction_date:
            date_time_note = f'Meeting Date: {extracted.interaction_date}'
            if extracted.interaction_time:
                date_time_note += f' {extracted.interaction_time}'
            extracted.discussion_notes = f'{date_time_note}\n\n{extracted.discussion_notes}'.strip()
        extracted.status = 'logged'
        return await InteractionService(self.session).create_interaction(extracted)

    def _build_conversation(self, history: list[ChatHistoryMessage], content: str) -> str:
        lines: list[str] = []
        for message in history:
            role = 'User' if message.role == 'user' else 'Assistant'
            if message.content.strip():
                lines.append(f'{role}: {message.content.strip()}')
        lines.append(f'User: {content.strip()}')
        return '\n'.join(lines)

    def _is_greeting_only(self, content: str) -> bool:
        normalized = re.sub(r'[^\w\s]', '', content.lower()).strip()
        if not normalized:
            return False
        return any(re.fullmatch(pattern, normalized) for pattern in GREETING_PATTERNS) or normalized in {'hi', 'hey', 'hii'}

    def _is_confirmation(self, content: str) -> bool:
        normalized = content.lower().strip().rstrip('.!')
        return any(re.fullmatch(pattern, normalized) for pattern in CONFIRM_PATTERNS)

    def _awaiting_confirmation(self, history: list[ChatHistoryMessage]) -> bool:
        for message in reversed(history):
            if message.role == 'assistant':
                return 'reply **yes** to log the interaction' in message.content.lower()
        return False

    def _latest_user_message(self, conversation: str) -> str:
        user_lines = [
            line.removeprefix('User:').strip()
            for line in conversation.splitlines()
            if line.startswith('User:')
        ]
        meaningful = [line for line in user_lines if line and not self._is_greeting_only(line)]
        return meaningful[-1] if meaningful else conversation.strip()

    def _apply_defaults(self, extracted: ExtractedInteraction) -> None:
        now = datetime.now()
        if not extracted.interaction_date and extracted.doctor_name and extracted.doctor_name != 'Unknown Doctor':
            extracted.interaction_date = now.date()
        if extracted.interaction_date and not extracted.interaction_time:
            extracted.interaction_time = now.strftime('%H:%M')
        if not extracted.interaction_type:
            extracted.interaction_type = 'visit'

    def _missing_fields(self, extracted: ExtractedInteraction) -> list[str]:
        missing: list[str] = []
        if not extracted.doctor_name or extracted.doctor_name == 'Unknown Doctor':
            missing.append('HCP Name')
        has_summary = bool(extracted.summary and len(extracted.summary.strip()) >= 8)
        has_notes = bool(extracted.discussion_notes and len(extracted.discussion_notes.strip()) >= 12)
        if not has_summary and not has_notes:
            missing.append('Discussion Summary')
        return missing

    def _build_success_reply(self, extracted: ExtractedInteraction) -> str:
        return (
            '✅ **Interaction logged successfully!** The details (HCP Name, Date, Sentiment, and Materials) '
            'have been automatically populated based on your summary. Would you like me to suggest a '
            'specific follow-up action, such as scheduling a meeting?'
        )

    def _build_missing_field_reply(self, extracted: ExtractedInteraction, missing: list[str]) -> str:
        if len(extracted.discussion_notes.strip()) < 12:
            return FIELD_QUESTIONS[missing[0]]

        acknowledged = []
        if extracted.doctor_name and extracted.doctor_name != 'Unknown Doctor':
            acknowledged.append(f"HCP: {extracted.doctor_name}")
        if extracted.hospital:
            acknowledged.append(f"Location: {extracted.hospital}")
        if extracted.interaction_date:
            time_text = f" at {extracted.interaction_time}" if extracted.interaction_time else ''
            acknowledged.append(f"Meeting: {extracted.interaction_date}{time_text}")
        if extracted.products_discussed:
            acknowledged.append(f"Products: {', '.join(extracted.products_discussed)}")

        prefix = f"Thanks! I've noted {'; '.join(acknowledged)}. " if acknowledged else 'Thanks for the update. '
        return prefix + FIELD_QUESTIONS[missing[0]]

    def _build_confirmation_summary(self, extracted: ExtractedInteraction) -> str:
        follow_up = extracted.follow_up_date or 'Not provided'
        meeting_time = extracted.interaction_time or 'Not provided'
        meeting_date = extracted.interaction_date or 'Not provided'
        return (
            "Here's what I captured:\n\n"
            f"• HCP Name: {extracted.doctor_name}\n"
            f"• Hospital/Clinic: {extracted.hospital}\n"
            f"• Meeting Date: {meeting_date}\n"
            f"• Meeting Time: {meeting_time}\n"
            f"• Interaction Type: {extracted.interaction_type.title()}\n"
            f"• Products Discussed: {', '.join(extracted.products_discussed)}\n"
            f"• Discussion Summary: {extracted.summary}\n"
            f"• Follow-up Date: {follow_up}\n\n"
            'Does this look correct? Reply **yes** to log the interaction.'
        )

    def _build_discussion_notes(self, conversation: str) -> str:
        user_lines = [
            line.removeprefix('User:').strip()
            for line in conversation.splitlines()
            if line.startswith('User:')
        ]
        meaningful = [line for line in user_lines if not self._is_greeting_only(line)]
        return ' '.join(meaningful) if meaningful else conversation.strip()

    def _extract_hospital(self, conversation: str) -> str:
        patterns = [
            r'at\s+([A-Za-z][A-Za-z\s&]+(?:Clinic|Hospital|Center|Care))',
            r'(?:hospital|clinic)\s*(?:was|:)?\s*([A-Za-z][A-Za-z\s&]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, conversation, re.IGNORECASE)
            if match:
                return ' '.join(match.group(1).split()).title()
        return ''

    def _has_known_product(self, conversation: str) -> bool:
        lower = conversation.lower()
        return any(
            product in lower
            for product in ['ozempic', 'rybelsus', 'wegovy', 'dupixent', 'jardiance', 'trulicity']
        )

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
            (r'\b(presentations?)\b', 'Presentation'),
            (r'\b(pdfs?)\b', 'PDF'),
            (r'\b(detailing aids?)\b', 'Detailing Aid'),
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

    def _extract_products_from_text(self, conversation: str) -> list[str]:
        products: list[str] = []
        product_match = re.search(r'product\s+([A-Za-z0-9-]+)', conversation, re.IGNORECASE)
        if product_match and product_match.group(1).lower() not in MATERIAL_WORDS:
            products.append(f'Product {product_match.group(1).title()}')
        for known in ['ozempic', 'rybelsus', 'wegovy', 'dupixent', 'jardiance', 'trulicity', 'prodo-x']:
            if known in conversation.lower():
                products.append(known.title())
        return products

    def _default_follow_up_actions(self, extracted: ExtractedInteraction) -> list[str]:
        if extracted.sentiment == 'negative':
            return ['No immediate follow-up; document HCP decline and revisit only if new evidence emerges.']
        actions = []
        if extracted.products_discussed:
            actions.append(f'Schedule follow-up meeting on {extracted.products_discussed[0]}')
        if extracted.follow_up_date:
            actions.append(f'Follow up on {extracted.follow_up_date}')
        actions.append('Send requested materials and confirm receipt')
        return actions[:3]

    def _extract_follow_up_date(self, conversation: str) -> date | None:
        lower = conversation.lower()
        today = datetime.now().date()

        if 'tomorrow' in lower:
            return today + timedelta(days=1)
        if 'next friday' in lower:
            delta = (4 - today.weekday()) % 7 or 7
            return today + timedelta(days=delta)
        if 'next monday' in lower:
            delta = (0 - today.weekday()) % 7 or 7
            return today + timedelta(days=delta)
        if 'next week' in lower or 'in a week' in lower:
            return today + timedelta(days=7)
        if 'in 2 weeks' in lower or 'two weeks' in lower:
            return today + timedelta(days=14)

        numeric_date = re.search(r'follow[- ]?up(?: on| by)?\s+(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', lower)
        if numeric_date:
            day, month, year = numeric_date.groups()
            year_value = int(year)
            if year_value < 100:
                year_value += 2000
            return date(year_value, int(month), int(day))

        iso_date = re.search(r'follow[- ]?up(?: on| by)?\s+(\d{4})-(\d{2})-(\d{2})', lower)
        if iso_date:
            return date(int(iso_date.group(1)), int(iso_date.group(2)), int(iso_date.group(3)))
        return None

    def _extract_follow_up_actions(self, conversation: str) -> str:
        lower = conversation.lower()
        if any(signal in lower for signal in ['not interested', 'declined', 'no interest', 'refused follow']):
            return ''
        if 'no commitment' in lower or 'without any commitment' in lower:
            return ''
        patterns = [
            r'follow[- ]?up(?: action[s]?)?[:\s]+(.+?)(?:\.|$)',
            r'next step[s]?[:\s]+(.+?)(?:\.|$)',
            r'(schedule\s+(?:a\s+)?(?:follow[- ]?up|meeting).+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, conversation, re.IGNORECASE)
            if match:
                action = match.group(1).strip().rstrip('.')
                if len(action) >= 6:
                    return action[0].upper() + action[1:]
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
        else:
            numeric_date = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', conversation)
            if numeric_date:
                day, month, year = numeric_date.groups()
                year_value = int(year)
                if year_value < 100:
                    year_value += 2000
                meeting_date = date(year_value, int(month), int(day))
            else:
                iso_date = re.search(r'(\d{4})-(\d{2})-(\d{2})', conversation)
                if iso_date:
                    meeting_date = date(int(iso_date.group(1)), int(iso_date.group(2)), int(iso_date.group(3)))

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
        else:
            twenty_four_hour = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', conversation)
            if twenty_four_hour:
                meeting_time = f'{int(twenty_four_hour.group(1)):02d}:{twenty_four_hour.group(2)}'
            elif 'this morning' in lower:
                meeting_time = '09:00'
            elif 'this afternoon' in lower:
                meeting_time = '14:00'
            elif 'this evening' in lower:
                meeting_time = '18:00'

        return meeting_date, meeting_time

    def _empty_draft(self) -> ExtractedInteraction:
        return ExtractedInteraction(
            doctor_name='',
            hospital='',
            interaction_type='visit',
            interaction_date=None,
            interaction_time=None,
            discussion_notes='',
            summary='',
            products_discussed=[],
            materials_shared=[],
            follow_up_date=None,
            follow_up_actions='',
            sentiment='neutral',
            status='draft',
        )

    def _result(self, message: str, extracted: ExtractedInteraction, next_best_action: list[str], save_result) -> dict:
        return {
            'message': message,
            'interaction': extracted.model_dump(mode='json'),
            'next_best_action': next_best_action,
            'save_result': save_result.model_dump(mode='json') if save_result else None,
            'response_message': message,
        }
