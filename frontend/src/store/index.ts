import { combineReducers, configureStore } from '@reduxjs/toolkit';
import { nanoid } from '@reduxjs/toolkit';
import storage from 'redux-persist/lib/storage';
import { createMigrate, persistReducer, persistStore } from 'redux-persist';
import authReducer from './slices/authSlice';
import chatReducer, { CHAT_WELCOME_MESSAGE } from './slices/chatSlice';
import hcpReducer from './slices/hcpSlice';
import interactionReducer from './slices/interactionSlice';
import uiReducer from './slices/uiSlice';

const rootReducer = combineReducers({
  auth: authReducer,
  interactions: interactionReducer,
  chat: chatReducer,
  hcp: hcpReducer,
  ui: uiReducer,
});

const migrations = {
  2: (state: ReturnType<typeof rootReducer> | undefined) => {
    if (!state) return state;

    return {
      ...state,
      chat: {
        ...state.chat,
        messages: [
          {
            id: nanoid(),
            role: 'assistant' as const,
            content: CHAT_WELCOME_MESSAGE,
            createdAt: new Date().toISOString(),
          },
        ],
        extracted: null,
        nextBestAction: [],
        loading: false,
      },
    };
  },
  3: (state: ReturnType<typeof rootReducer> | undefined) => {
    if (!state) return state;

    return {
      ...state,
      chat: {
        ...state.chat,
        messages: [
          {
            id: nanoid(),
            role: 'assistant' as const,
            content: CHAT_WELCOME_MESSAGE,
            createdAt: new Date().toISOString(),
          },
        ],
        extracted: null,
        nextBestAction: [],
        loading: false,
      },
    };
  },
  4: (state: ReturnType<typeof rootReducer> | undefined) => {
    if (!state) return state;

    return {
      ...state,
      chat: {
        ...state.chat,
        messages: [
          {
            id: nanoid(),
            role: 'assistant' as const,
            content: CHAT_WELCOME_MESSAGE,
            createdAt: new Date().toISOString(),
          },
        ],
        extracted: null,
        nextBestAction: [],
        loading: false,
      },
    };
  },
  5: (state: ReturnType<typeof rootReducer> | undefined) => {
    if (!state) return state;

    return {
      ...state,
      chat: {
        ...state.chat,
        messages: [
          {
            id: nanoid(),
            role: 'assistant' as const,
            content: CHAT_WELCOME_MESSAGE,
            createdAt: new Date().toISOString(),
          },
        ],
        extracted: null,
        nextBestAction: [],
        loading: false,
      },
    };
  },
};

const persistedReducer = persistReducer(
  {
    key: 'ai-crm-hcp',
    version: 5,
    storage,
    whitelist: ['ui', 'interactions', 'chat'],
    migrate: createMigrate(migrations),
  },
  rootReducer,
);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export const persistor = persistStore(store);
export type RootState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
