from sqlalchemy.ext.asyncio import AsyncSession

from app.graphs.interaction_graph import build_interaction_graph
from app.schemas.chat import ChatHistoryMessage
from app.schemas.interaction import ExtractedInteraction
from app.services.conversation_assistant import ConversationAssistantService


class InteractionOrchestrator:
    """LangGraph-powered orchestrator for the HCP interaction assistant."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.graph = build_interaction_graph(session)
        self.assistant = ConversationAssistantService(session)

    async def process(
        self,
        content: str,
        history: list[ChatHistoryMessage] | None = None,
        save: bool = False,
        draft: ExtractedInteraction | None = None,
        interaction_id: int | None = None,
    ) -> dict:
        history = history or []
        conversation = self.assistant._build_conversation(history, content)

        if self.assistant._is_greeting_only(content):
            reply = (
                "Log interaction details here (e.g., 'Met an HCP, discussed product efficacy, "
                "positive sentiment, shared brochure') or ask for help."
            )
            return self._result(reply, self.assistant._empty_draft(), [], None)

        graph_state = await self.graph.ainvoke(
            {
                'conversation': conversation,
                'latest_user_message': self.assistant._latest_user_message(conversation),
                'content': content,
                'save': save,
                'current_extracted': draft.model_dump(mode='json') if draft else None,
                'interaction_id': interaction_id,
                'doctor': draft.doctor_name if draft and draft.doctor_name not in {'', 'Unknown Doctor'} else None,
            }
        )

        extracted = graph_state.get('extracted') or self.assistant._empty_draft()
        if isinstance(extracted, dict):
            extracted = ExtractedInteraction(**extracted)

        self.assistant._apply_defaults(extracted)
        missing = self.assistant._missing_fields(extracted)
        awaiting_confirmation = self.assistant._awaiting_confirmation(history)

        if (self.assistant._is_confirmation(content) or save) and awaiting_confirmation and not missing:
            saved = await self.assistant._save_interaction(extracted)
            reply = '✅ Interaction logged successfully.'
            extracted.status = 'logged'
            return self._result(reply, extracted, [], saved)

        next_actions = graph_state.get('next_best_action') or []

        if graph_state.get('intent') == 'edit_interaction':
            extracted = graph_state.get('extracted') or extracted
            if isinstance(extracted, dict):
                extracted = ExtractedInteraction(**extracted)
            self.assistant._apply_defaults(extracted)
            reply = graph_state.get('response_message') or 'Interaction update completed.'
            return self._result(reply, extracted, next_actions, graph_state.get('save_result'))

        if graph_state.get('intent') == 'search_hcp':
            reply = graph_state.get('response_message') or 'No matching HCP records were found.'
            return self._result(reply, extracted, next_actions, None)

        if next_actions and not extracted.follow_up_actions and extracted.sentiment != 'negative':
            extracted.follow_up_actions = next_actions[0]
        elif extracted.sentiment == 'negative' and not extracted.follow_up_actions:
            extracted.follow_up_actions = (
                'No immediate follow-up; document HCP decline and revisit only if new evidence emerges.'
            )

        if not missing and graph_state.get('intent') != 'search_hcp':
            reply = graph_state.get('response_message') or self.assistant._build_success_reply(extracted)
            extracted.status = 'populated'
            return self._result(reply, extracted, next_actions, graph_state.get('save_result'))

        if graph_state.get('intent') == 'generate_email' and graph_state.get('email_draft'):
            reply = graph_state.get('response_message') or 'Follow-up email draft prepared.'
            return self._result(reply, extracted, next_actions, None)

        reply = self.assistant._build_missing_field_reply(extracted, missing)
        extracted.status = 'draft'
        return self._result(reply, extracted, next_actions, None)

    async def run(self, conversation: str, save: bool = False) -> dict:
        return await self.graph.ainvoke({'conversation': conversation, 'save': save})

    def _result(self, message: str, extracted: ExtractedInteraction, next_best_action: list[str], save_result) -> dict:
        return {
            'message': message,
            'interaction': extracted.model_dump(mode='json'),
            'next_best_action': next_best_action,
            'save_result': save_result.model_dump(mode='json') if hasattr(save_result, 'model_dump') else save_result,
            'response_message': message,
        }
