from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.graphs.state import InteractionGraphState
from app.schemas.email import EmailRequest
from app.tools.edit_interaction_tool import EditInteractionTool
from app.tools.generate_followup_email_tool import GenerateFollowUpEmailTool
from app.tools.log_interaction_tool import LogInteractionTool
from app.tools.next_best_action_tool import NextBestActionTool
from app.tools.search_hcp_tool import SearchHCPTool


def _append_tool(state: InteractionGraphState, tool_name: str) -> list[str]:
    used = list(state.get('tools_used') or [])
    if tool_name not in used:
        used.append(tool_name)
    return used


def build_interaction_graph(session: AsyncSession):
    log_tool = LogInteractionTool(session)
    edit_tool = EditInteractionTool(session)
    search_tool = SearchHCPTool(session)
    next_action_tool = NextBestActionTool(session)
    email_tool = GenerateFollowUpEmailTool()

    async def input_node(state: InteractionGraphState) -> InteractionGraphState:
        state['tools_used'] = state.get('tools_used') or []
        return state

    async def intent_detection(state: InteractionGraphState) -> InteractionGraphState:
        conversation = state.get('latest_user_message', state['conversation']).lower()
        intent = 'log_interaction'
        if any(token in conversation for token in ['search hcp', 'find doctor', 'find hcp', 'search doctor']):
            intent = 'search_hcp'
        elif any(token in conversation for token in ['follow-up email', 'follow up email', 'draft email', 'write email']):
            intent = 'generate_email'
        elif any(token in conversation for token in ['change ', 'update ', 'edit ', 'modify ']):
            intent = 'edit_interaction'
        state['intent'] = intent
        state['tools_used'] = _append_tool(state, 'intent_detection')
        return state

    async def search_hcp_node(state: InteractionGraphState) -> InteractionGraphState:
        query = state.get('doctor') or state.get('latest_user_message', state['conversation'])
        results = await search_tool.run(query)
        state['hcp_results'] = [item.model_dump(mode='json') for item in results]
        state['tools_used'] = _append_tool(state, 'search_hcp')
        return state

    async def entity_extraction(state: InteractionGraphState) -> InteractionGraphState:
        extracted, save_result = await log_tool.run(state['conversation'], save=False)
        state['doctor'] = extracted.doctor_name
        state['interaction'] = extracted.model_dump(mode='json')
        state['products'] = extracted.products_discussed
        state['follow_up'] = str(extracted.follow_up_date) if extracted.follow_up_date else None
        state['status'] = extracted.status
        state['extracted'] = extracted
        state['save_result'] = save_result.model_dump(mode='json') if save_result else None
        state['tools_used'] = _append_tool(state, 'log_interaction')
        return state

    async def summarization(state: InteractionGraphState) -> InteractionGraphState:
        if state.get('extracted'):
            state['summary'] = state['extracted'].summary
        state['tools_used'] = _append_tool(state, 'summarization')
        return state

    async def validation(state: InteractionGraphState) -> InteractionGraphState:
        validation_errors = []
        interaction = state.get('interaction') or {}
        for key in ['doctor_name', 'interaction_type', 'discussion_notes', 'summary']:
            if not interaction.get(key):
                validation_errors.append(f'{key} is required')
        state['validation_errors'] = validation_errors
        state['tools_used'] = _append_tool(state, 'validation')
        return state

    async def next_best_action_node(state: InteractionGraphState) -> InteractionGraphState:
        try:
            state['next_best_action'] = await next_action_tool.run(
                state.get('doctor', ''),
                state.get('products', []),
                state.get('summary', ''),
            )
        except Exception:
            state['next_best_action'] = [
                'Schedule a follow-up meeting in 2 weeks',
                'Send requested clinical materials',
            ]
        state['tools_used'] = _append_tool(state, 'next_best_action')
        return state

    async def generate_email_node(state: InteractionGraphState) -> InteractionGraphState:
        extracted = state.get('extracted')
        if not extracted or extracted.doctor_name in {'', 'Unknown Doctor'}:
            return state
        call_to_action = (
            extracted.follow_up_actions
            or (state.get('next_best_action') or ['Review the discussed evidence and confirm next steps'])[0]
        )
        email = await email_tool.run(
            EmailRequest(
                doctor_name=extracted.doctor_name,
                summary=extracted.summary or extracted.discussion_notes,
                products_discussed=extracted.products_discussed,
                call_to_action=call_to_action,
            )
        )
        state['email_draft'] = email.model_dump(mode='json')
        state['tools_used'] = _append_tool(state, 'generate_followup_email')
        return state

    async def edit_interaction_node(state: InteractionGraphState) -> InteractionGraphState:
        updated = await edit_tool.run(
            state.get('latest_user_message', state['conversation']),
            interaction_id=state.get('interaction_id'),
            doctor_name=state.get('doctor'),
        )
        state['tools_used'] = _append_tool(state, 'edit_interaction')
        if updated:
            state['save_result'] = updated.model_dump(mode='json')
            state['response_message'] = f'✅ Updated interaction #{updated.id} successfully.'
        else:
            state['response_message'] = (
                'I could not find an interaction to update. Please log one first or specify the HCP name.'
            )
        return state

    async def database_save(state: InteractionGraphState) -> InteractionGraphState:
        if state.get('save') and not state.get('validation_errors'):
            extracted, save_result = await log_tool.run(state['conversation'], save=True)
            state['extracted'] = extracted
            state['save_result'] = save_result.model_dump(mode='json') if save_result else None
            state['tools_used'] = _append_tool(state, 'database_save')
        return state

    async def success_node(state: InteractionGraphState) -> InteractionGraphState:
        if state.get('response_message'):
            return state

        intent = state.get('intent', 'log_interaction')
        if intent == 'search_hcp':
            matches = state.get('hcp_results') or []
            if matches:
                names = ', '.join(item.get('doctor_name', '') for item in matches[:5])
                state['response_message'] = f'Found matching HCP records: {names}'
            else:
                state['response_message'] = 'No matching HCP records were found.'
            return state

        if state.get('validation_errors'):
            state['response_message'] = 'I extracted the interaction, but some fields need attention before save.'
            return state

        if state.get('email_draft') and state.get('intent') == 'generate_email':
            subject = state['email_draft'].get('subject', 'Follow-up email draft')
            state['response_message'] = f'✅ Follow-up email draft prepared: **{subject}**'
            return state

        state['response_message'] = (
            '✅ **Interaction logged successfully!** The details (HCP Name, Date, Sentiment, and Materials) '
            'have been automatically populated based on your summary. Would you like me to suggest a '
            'specific follow-up action, such as scheduling a meeting?'
        )
        return state

    def route_intent(state: InteractionGraphState) -> str:
        return state.get('intent', 'log_interaction')

    def after_search_route(state: InteractionGraphState) -> str:
        if state.get('intent') == 'search_hcp':
            return 'success'
        return 'extract'

    def after_email_route(state: InteractionGraphState) -> str:
        if state.get('intent') == 'generate_email':
            return 'success'
        return 'save'

    workflow = StateGraph(InteractionGraphState)
    workflow.add_node('Input Node', input_node)
    workflow.add_node('Intent Detection', intent_detection)
    workflow.add_node('Search HCP', search_hcp_node)
    workflow.add_node('Entity Extraction', entity_extraction)
    workflow.add_node('Summarization', summarization)
    workflow.add_node('Validation', validation)
    workflow.add_node('Next Best Action', next_best_action_node)
    workflow.add_node('Generate Email', generate_email_node)
    workflow.add_node('Edit Interaction', edit_interaction_node)
    workflow.add_node('Database Save', database_save)
    workflow.add_node('Success', success_node)

    workflow.set_entry_point('Input Node')
    workflow.add_edge('Input Node', 'Intent Detection')
    workflow.add_conditional_edges(
        'Intent Detection',
        route_intent,
        {
            'log_interaction': 'Search HCP',
            'edit_interaction': 'Edit Interaction',
            'search_hcp': 'Search HCP',
            'generate_email': 'Entity Extraction',
        },
    )
    workflow.add_conditional_edges(
        'Search HCP',
        after_search_route,
        {
            'success': 'Success',
            'extract': 'Entity Extraction',
        },
    )
    workflow.add_edge('Entity Extraction', 'Summarization')
    workflow.add_edge('Summarization', 'Validation')
    workflow.add_edge('Validation', 'Next Best Action')
    workflow.add_edge('Next Best Action', 'Generate Email')
    workflow.add_conditional_edges(
        'Generate Email',
        after_email_route,
        {
            'success': 'Success',
            'save': 'Database Save',
        },
    )
    workflow.add_edge('Database Save', 'Success')
    workflow.add_edge('Edit Interaction', 'Success')
    workflow.add_edge('Success', END)

    return workflow.compile()
