import { createAsyncThunk, createSlice, nanoid, PayloadAction } from '@reduxjs/toolkit';
import { chatService } from '../../services/chatService';
import { ChatMessage, ChatResponse } from '../../types';

export const CHAT_WELCOME_MESSAGE =
  "Log interaction details here (e.g., 'Met an HCP, discussed product efficacy, positive sentiment, shared brochure') or ask for help.";

interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  extracted: ChatResponse['extracted'] | null;
  nextBestAction: string[];
}

const createWelcomeMessage = (): ChatMessage => ({
  id: nanoid(),
  role: 'assistant',
  content: CHAT_WELCOME_MESSAGE,
  createdAt: new Date().toISOString(),
});

const initialState: ChatState = {
  messages: [createWelcomeMessage()],
  loading: false,
  extracted: null,
  nextBestAction: [],
};

export const sendChatMessage = createAsyncThunk(
  'chat/send',
  async (payload: { content: string; save?: boolean }, { getState }) => {
    const history = getState().chat.messages
      .filter((message) => message.content.trim())
      .map((message) => ({ role: message.role, content: message.content }));
    return chatService.send({ ...payload, history });
  },
);
export const streamChatMessage = createAsyncThunk(
  'chat/stream',
  async (payload: { content: string; save?: boolean }, { dispatch, getState }) => {
    const history = getState().chat.messages
      .filter((message) => message.content.trim())
      .map((message) => ({ role: message.role, content: message.content }));
    const assistantId = nanoid();
    dispatch(
      pushMessage({
        id: assistantId,
        role: 'assistant',
        content: '',
        createdAt: new Date().toISOString(),
      }),
    );

    return chatService.stream({ ...payload, history }, (token) => {
      dispatch(appendAssistantToken({ id: assistantId, token }));
    });
  },
);

const normalizeExtracted = (payload: ChatResponse['extracted']): ChatResponse['extracted'] => ({
  ...payload,
  interaction_date: payload.interaction_date ? String(payload.interaction_date).slice(0, 10) : null,
  interaction_time: payload.interaction_time ? String(payload.interaction_time).slice(0, 5) : null,
  follow_up_date: payload.follow_up_date ? String(payload.follow_up_date).slice(0, 10) : null,
  follow_up_actions: payload.follow_up_actions ?? '',
  materials_shared: payload.materials_shared ?? [],
  products_discussed: payload.products_discussed ?? [],
});

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    pushMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload);
    },
    appendAssistantToken(state, action: PayloadAction<{ id: string; token: string }>) {
      const message = state.messages.find((item) => item.id === action.payload.id);
      if (message) {
        message.content += action.payload.token;
      }
    },
    clearConversation(state) {
      state.messages = [createWelcomeMessage()];
      state.extracted = null;
      state.nextBestAction = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendChatMessage.pending, (state) => {
        state.loading = true;
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.loading = false;
        state.messages.push({
          id: nanoid(),
          role: 'assistant',
          content: action.payload.message,
          createdAt: new Date().toISOString(),
        });
        state.extracted = normalizeExtracted(action.payload.extracted);
        state.nextBestAction = action.payload.next_best_action;
      })
      .addCase(sendChatMessage.rejected, (state) => {
        state.loading = false;
      })
      .addCase(streamChatMessage.pending, (state) => {
        state.loading = true;
      })
      .addCase(streamChatMessage.fulfilled, (state, action) => {
        state.loading = false;
        state.extracted = normalizeExtracted(action.payload.extracted);
        state.nextBestAction = action.payload.next_best_action;

        const lastMessage = state.messages[state.messages.length - 1];
        if (lastMessage?.role === 'assistant' && !lastMessage.content.trim() && action.payload.message) {
          lastMessage.content = action.payload.message;
        }
      })
      .addCase(streamChatMessage.rejected, (state) => {
        state.loading = false;
        const lastMessage = state.messages[state.messages.length - 1];
        if (lastMessage?.role === 'assistant' && !lastMessage.content.trim()) {
          state.messages.pop();
        }
      });
  },
});

export const { pushMessage, appendAssistantToken, clearConversation } = chatSlice.actions;
export default chatSlice.reducer;
