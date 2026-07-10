import re
from datetime import date, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.schemas.interaction import ExtractedInteraction, InteractionRead, InteractionUpdate
from app.services.interaction_service import InteractionService
from app.services.llm_service import LLMService


class EditInteractionTool:
    """LangGraph tool: update an existing interaction from natural-language instructions."""

    def __init__(self, session: AsyncSession):
        self.service = InteractionService(session)
        self.session = session
        self.llm_service = LLMService()

    def clean_doctor_name(self, doctor_name: str | None) -> str | None:
        if not doctor_name:
            return None
        cleaned = re.sub(
            r'\s+(today|yesterday|tomorrow|next|last|this|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*$',
            '',
            doctor_name,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned or doctor_name

    def _normalize_doctor_search(self, doctor_name: str) -> str:
        cleaned = self.clean_doctor_name(doctor_name) or doctor_name
        return re.sub(r'^dr\.?\s*', '', cleaned, flags=re.IGNORECASE).strip()

    def _normalize_doctor_value(self, value: str) -> str:
        cleaned = self.clean_doctor_name(value) or value
        stripped = re.sub(r'^dr\.?\s*', '', cleaned, flags=re.IGNORECASE).strip()
        return f'Dr. {stripped.title()}' if stripped else cleaned

    def _clean_value(self, value: str) -> str:
        return value.strip().strip('"').strip("'").strip().rstrip('.')

    def _extract_to_value(self, instruction: str, field_pattern: str) -> str | None:
        match = re.search(
            rf'(?:change|update|set)\s+(?:the\s+)?(?:{field_pattern})\s+to\s+(.+)$',
            instruction,
            re.IGNORECASE,
        )
        return self._clean_value(match.group(1)) if match else None

    def _extract_follow_up_action(self, instruction: str) -> str | None:
        patterns = [
            r'(?:change|update|set)\s+follow[- ]?up action(?:s)?\s+to\s+(.+)$',
            r'add\s+follow[- ]?up action(?:s)?\s+(.+)$',
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return self._clean_value(match.group(1))
        return None

    def _extract_note_addition(self, instruction: str) -> str | None:
        suffix_match = re.search(
            r'(.+?)\s+please add that to (?:the )?(?:interaction|notes)\.?$',
            instruction,
            re.IGNORECASE,
        )
        if suffix_match:
            return self._clean_value(suffix_match.group(1))

        patterns = [
            r'add to (?:the )?(?:interaction|notes|discussion notes|topics discussed):?\s+(.+)$',
            r'add this to (?:the )?(?:interaction|notes):?\s+(.+)$',
            r'please add (?:this )?to (?:the )?(?:interaction|notes):?\s+(.+)$',
            r'also mention (?:that )?(.+)$',
            r'please also note (?:that )?(.+)$',
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return self._clean_value(match.group(1))
        return None

    def _extract_product_change(self, instruction: str) -> tuple[str | None, list[str] | None]:
        swap_match = re.search(
            r'(?:change|update|replace)\s+(?:the\s+)?(?:product\s+)?(.+?)\s+to\s+(?:product\s+)?(.+)$',
            instruction,
            re.IGNORECASE,
        )
        if swap_match:
            old_product = self._clean_value(swap_match.group(1))
            new_product = self._clean_value(swap_match.group(2))
            old_product = re.sub(r'^product\s+', '', old_product, flags=re.IGNORECASE).strip()
            new_product = re.sub(r'^product\s+', '', new_product, flags=re.IGNORECASE).strip()
            if old_product and new_product:
                return old_product, [new_product]

        list_match = re.search(r'(?:change|update|set)\s+products?\s+to\s+(.+)$', instruction, re.IGNORECASE)
        if list_match:
            products = [self._clean_value(item) for item in list_match.group(1).split(',')]
            products = [item for item in products if item]
            return None, products or None

        single_match = re.search(r'(?:change|update|set)\s+product\s+to\s+(.+)$', instruction, re.IGNORECASE)
        if single_match:
            product = self._clean_value(single_match.group(1))
            return None, [product] if product else None

        return None, None

    def _replace_text(self, text: str, old: str, new: str) -> str:
        if not text.strip() or not old.strip():
            return text
        return re.sub(re.escape(old), new, text, count=1, flags=re.IGNORECASE)

    def _merge_follow_up_actions(self, discussion_notes: str, follow_up_actions: str) -> str:
        if not follow_up_actions:
            return discussion_notes

        if 'Follow-up Actions:' in discussion_notes:
            return re.sub(
                r'Follow-up Actions:\s*.*',
                f'Follow-up Actions: {follow_up_actions}',
                discussion_notes,
                flags=re.IGNORECASE | re.DOTALL,
            )

        separator = '\n\n' if discussion_notes.strip() else ''
        return f'{discussion_notes.strip()}{separator}Follow-up Actions: {follow_up_actions}'.strip()

    def _extract_follow_up_actions_from_notes(self, discussion_notes: str, follow_up_date: date | None) -> str:
        match = re.search(r'Follow-up Actions:\s*(.+)', discussion_notes, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        if follow_up_date:
            return f'Follow-up visit on {follow_up_date.strftime("%A, %d %B %Y")}'
        return ''

    def _parse_follow_up_date(self, instruction: str) -> date | None:
        lower = instruction.lower()
        target = lower.split(' to ', 1)[1] if ' to ' in lower else lower
        today = datetime.now().date()

        weekdays = {
            'monday': 0,
            'tuesday': 1,
            'wednesday': 2,
            'thursday': 3,
            'friday': 4,
            'saturday': 5,
            'sunday': 6,
        }
        for day_name, day_index in weekdays.items():
            if day_name in target:
                delta = (day_index - today.weekday()) % 7 or 7
                return today + timedelta(days=delta)

        if 'tomorrow' in target:
            return today + timedelta(days=1)
        if 'next week' in target:
            return today + timedelta(days=7)
        return None

    def _extract_name_correction(self, instruction: str, conversation: str = '') -> str | None:
        explicit_patterns = [
            r'(?:change|update|correct|fix)\s+(?:the\s+)?name(?:\s+to)?\s+(?:to\s+)?(?:dr\.?\s*)?(.+)$',
            r'(?:change|update|correct|fix)\s+(?:the\s+)?(?:doctor|hcp)\s+name\s+to\s+(?:dr\.?\s*)?(.+)$',
            r'name\s+should\s+be\s+(?:dr\.?\s*)?(.+)$',
        ]
        for pattern in explicit_patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                value = self._clean_value(match.group(1))
                if value and value.lower() not in {'name', 'doctor', 'hcp'}:
                    return self._normalize_doctor_value(value)

        if re.search(r'(?:change|update|correct|fix)\s+(?:the\s+)?name\b', instruction, re.IGNORECASE):
            for text in (conversation, instruction):
                candidate = self.llm_service._extract_doctor_name(text)
                if candidate != 'Unknown Doctor':
                    return self.clean_doctor_name(candidate)

        if re.search(
            r'\b(?:why|not|wrong|incorrect)\b.*\b(?:dr\.?|doctor)\b',
            instruction,
            re.IGNORECASE,
        ):
            candidate = self.llm_service._extract_doctor_name(conversation or instruction)
            if candidate != 'Unknown Doctor':
                return self.clean_doctor_name(candidate)

        return None

    def resolve_doctor_name(
        self,
        instruction: str,
        conversation: str = '',
        doctor_name: str | None = None,
    ) -> str | None:
        corrected_name = self._extract_name_correction(instruction, conversation)
        if corrected_name:
            return corrected_name

        explicit_doctor = self._extract_to_value(instruction, r'doctor name|hcp name|doctor|hcp')
        if explicit_doctor:
            return self._normalize_doctor_value(explicit_doctor)

        if doctor_name and doctor_name not in {'', 'Unknown Doctor'}:
            return self.clean_doctor_name(doctor_name)

        for text in (instruction, conversation):
            if not text.strip():
                continue
            candidate = self.llm_service._extract_doctor_name(text)
            if candidate != 'Unknown Doctor':
                return self.clean_doctor_name(candidate)
        return None

    def has_editable_changes(self, instruction: str) -> bool:
        lowered = instruction.lower()
        return any(
            token in lowered
            for token in [
                'follow-up date',
                'follow up date',
                'follow-up action',
                'follow up action',
                'sentiment',
                'interaction type',
                'summary',
                'outcomes',
                'notes',
                'topics discussed',
                'discussion notes',
                'doctor name',
                'hcp name',
                'change the name',
                'change name',
                'correct the name',
                'wrong doctor',
                'not dr',
                'why dr',
                ' product ',
                'products ',
                'add to the interaction',
                'add this to the interaction',
                'please add this to the interaction',
                'also mention',
                'please also note',
            ]
        )

    def apply_instruction_to_extracted(self, extracted: ExtractedInteraction, instruction: str) -> ExtractedInteraction:
        follow_up_date = self._parse_follow_up_date(instruction)
        interaction_type = self._extract_to_value(instruction, r'interaction type')
        sentiment = self._extract_to_value(instruction, r'sentiment')
        summary = self._extract_to_value(instruction, r'summary|outcomes?')
        notes = self._extract_to_value(instruction, r'notes|discussion notes|topics discussed')
        note_addition = self._extract_note_addition(instruction)
        follow_up_action = self._extract_follow_up_action(instruction)
        doctor_name = self._extract_name_correction(instruction) or self._extract_to_value(
            instruction, r'doctor name|hcp name|doctor|hcp'
        )
        old_product, replacement_products = self._extract_product_change(instruction)

        if doctor_name:
            extracted.doctor_name = self._normalize_doctor_value(doctor_name)

        if follow_up_date:
            extracted.follow_up_date = follow_up_date
            if not follow_up_action:
                extracted.follow_up_actions = (
                    f'Follow-up visit on {follow_up_date.strftime("%A, %d %B %Y")}'
                )

        if interaction_type:
            normalized_type = interaction_type.lower()
            if normalized_type == 'meeting':
                normalized_type = 'visit'
            if normalized_type in {'visit', 'call', 'email', 'conference'}:
                extracted.interaction_type = normalized_type

        if sentiment and sentiment.lower() in {'positive', 'neutral', 'negative'}:
            extracted.sentiment = sentiment.lower()

        if notes:
            extracted.discussion_notes = notes
            if not summary:
                extracted.summary = notes
        elif note_addition:
            separator = ' ' if extracted.discussion_notes.strip() else ''
            extracted.discussion_notes = f'{extracted.discussion_notes.strip()}{separator}{note_addition}'.strip()
            if extracted.summary:
                extracted.summary = f'{extracted.summary.strip()}{separator}{note_addition}'.strip()
            else:
                extracted.summary = extracted.discussion_notes

        if summary:
            extracted.summary = summary

        if follow_up_action:
            extracted.follow_up_actions = follow_up_action

        if replacement_products:
            if old_product:
                current_products = extracted.products_discussed or ([old_product] if old_product else [])
                replaced = False
                next_products: list[str] = []
                replace_target = old_product
                for item in current_products:
                    if old_product.lower() in item.lower() and not replaced:
                        next_products.extend(replacement_products)
                        replace_target = item
                        replaced = True
                    else:
                        next_products.append(item)
                extracted.products_discussed = next_products or replacement_products
                extracted.discussion_notes = self._replace_text(
                    extracted.discussion_notes,
                    replace_target,
                    replacement_products[0],
                )
                extracted.summary = self._replace_text(
                    extracted.summary,
                    replace_target,
                    replacement_products[0],
                )
                extracted.follow_up_actions = self._replace_text(
                    extracted.follow_up_actions,
                    replace_target,
                    replacement_products[0],
                )
            else:
                extracted.products_discussed = replacement_products

        if extracted.follow_up_actions:
            extracted.discussion_notes = self._merge_follow_up_actions(
                extracted.discussion_notes,
                extracted.follow_up_actions,
            )

        if not extracted.summary:
            extracted.summary = extracted.discussion_notes

        return extracted

    def describe_update(self, extracted: ExtractedInteraction, instruction: str) -> str:
        changed: list[str] = []
        lowered = instruction.lower()
        if 'follow-up date' in lowered or 'follow up date' in lowered:
            changed.append(
                f'follow-up date **{extracted.follow_up_date.strftime("%d-%m-%Y")}**'
                if extracted.follow_up_date
                else 'follow-up date'
            )
        if 'follow-up action' in lowered or 'follow up action' in lowered:
            changed.append('follow-up actions')
        if 'sentiment' in lowered and extracted.sentiment:
            changed.append(f'sentiment **{extracted.sentiment}**')
        if 'interaction type' in lowered:
            changed.append(f'interaction type **{extracted.interaction_type}**')
        if any(token in lowered for token in ['product ', 'products ']) and extracted.products_discussed:
            changed.append(f'products **{", ".join(extracted.products_discussed)}**')
        if any(token in lowered for token in ['summary', 'outcomes']):
            changed.append('summary')
        if any(token in lowered for token in ['notes', 'discussion notes', 'topics discussed']):
            changed.append('notes')
        if any(
            token in lowered
            for token in ['add to the interaction', 'add this to the interaction', 'please add this to the interaction', 'also mention', 'please also note']
        ):
            changed.append('notes')
        if any(token in lowered for token in ['doctor name', 'hcp name', 'doctor', 'hcp']) and extracted.doctor_name:
            changed.append(f'HCP **{extracted.doctor_name}**')
        if any(
            token in lowered
            for token in ['change the name', 'change name', 'correct the name', 'wrong doctor', 'not dr', 'why dr']
        ) and extracted.doctor_name:
            changed.append(f'HCP **{extracted.doctor_name}**')
        if not changed:
            changed.append('the interaction draft')
        return ', '.join(changed)

    def to_extracted(self, interaction: InteractionRead) -> ExtractedInteraction:
        follow_up_actions = self._extract_follow_up_actions_from_notes(
            interaction.discussion_notes,
            interaction.follow_up_date,
        )
        return ExtractedInteraction(
            doctor_name=interaction.doctor_name,
            hospital=interaction.hospital or '',
            interaction_type=interaction.interaction_type,
            discussion_notes=interaction.discussion_notes,
            summary=interaction.summary,
            products_discussed=interaction.products_discussed,
            follow_up_date=interaction.follow_up_date,
            follow_up_actions=follow_up_actions,
            sentiment=interaction.sentiment,
            status='logged',
        )

    def _to_update_payload(self, extracted: ExtractedInteraction) -> InteractionUpdate:
        return InteractionUpdate(
            doctor_name=extracted.doctor_name or None,
            interaction_type=extracted.interaction_type or None,
            discussion_notes=self._merge_follow_up_actions(
                extracted.discussion_notes,
                extracted.follow_up_actions,
            ) or None,
            products_discussed=extracted.products_discussed,
            follow_up_date=extracted.follow_up_date,
            summary=(extracted.summary or extracted.discussion_notes or None),
            sentiment=extracted.sentiment,
        )

    async def _resolve_interaction_id(self, interaction_id: int | None, doctor_name: str | None) -> int | None:
        if interaction_id:
            return interaction_id

        if doctor_name:
            search_name = self._normalize_doctor_search(doctor_name)
            stmt = (
                select(Interaction)
                .join(HCP, HCP.id == Interaction.hcp_id)
                .where(HCP.doctor_name.ilike(f'%{search_name}%'))
                .order_by(desc(Interaction.created_at))
                .limit(1)
            )
            interaction = (await self.session.scalars(stmt)).first()
            return interaction.id if interaction else None

        stmt = select(Interaction).order_by(desc(Interaction.created_at)).limit(1)
        latest = (await self.session.scalars(stmt)).first()
        return latest.id if latest else None

    async def run(
        self,
        instruction: str,
        interaction_id: int | None = None,
        doctor_name: str | None = None,
        conversation: str = '',
    ) -> InteractionRead | None:
        resolved_doctor = self.resolve_doctor_name(instruction, conversation, doctor_name)
        resolved_id = await self._resolve_interaction_id(interaction_id, resolved_doctor)
        if not resolved_id:
            return None

        current = await self.service.get_interaction(resolved_id)
        extracted = self.to_extracted(current)
        updated_extracted = self.apply_instruction_to_extracted(extracted, instruction)
        payload = self._to_update_payload(updated_extracted)
        return await self.service.update_interaction(resolved_id, payload)
