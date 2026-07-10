import { FormEvent, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { nanoid } from '@reduxjs/toolkit';
import { useVoiceInput } from '../hooks/useVoiceInput';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { pushMessage, streamChatMessage, clearConversation } from '../store/slices/chatSlice';
import { addToast, resetInteractionForm, toggleDarkMode } from '../store/slices/uiSlice';
import { ChatMessage } from '../types';

const getMessageStyle = (message: ChatMessage) => {
  if (message.role === 'user') {
    return 'border border-slate-200 bg-slate-100 text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100';
  }
  if (
    message.content.includes('✅')
    || message.content.toLowerCase().includes('interaction logged successfully')
    || message.content.toLowerCase().includes('updated interaction')
  ) {
    return 'border border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100';
  }
  return 'border border-sky-200 bg-sky-50 text-slate-800 dark:border-sky-900 dark:bg-sky-950 dark:text-slate-100';
};

export const ChatPanel = () => {
  const dispatch = useAppDispatch();
  const [input, setInput] = useState('');
  const { messages, loading } = useAppSelector((state) => state.chat);
  const darkMode = useAppSelector((state) => state.ui.darkMode);
  const { isListening, toggleListening, supported } = useVoiceInput((transcript) =>
    setInput((current) => [current, transcript].filter(Boolean).join(' ')),
  );

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    dispatch(pushMessage({ id: nanoid(), role: 'user', content: trimmed, createdAt: new Date().toISOString() }));
    const result = await dispatch(streamChatMessage({ content: trimmed }));
    if (streamChatMessage.rejected.match(result)) {
      dispatch(addToast('error', 'Chat failed', result.error.message));
    }
    setInput('');
  };

  const hasConversation = messages.length > 1;

  const onClearChat = () => {
    if (!hasConversation || loading) return;
    dispatch(clearConversation());
    dispatch(resetInteractionForm());
    setInput('');
    dispatch(addToast('info', 'Chat cleared', 'You can start a new interaction log.'));
  };

  return (
    <div className="flex min-h-[720px] flex-col">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#2563eb] text-white">
            <span className="material-symbols-rounded text-base">smart_toy</span>
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">AI Assistant</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Log Interaction details here via chat.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => dispatch(toggleDarkMode())}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            title="Toggle mode"
          >
            <span className="material-symbols-rounded text-sm">{darkMode ? 'light_mode' : 'dark_mode'}</span>
            {darkMode ? 'Light Mode' : 'Dark Mode'}
          </button>
          <button
            type="button"
            onClick={onClearChat}
            disabled={!hasConversation || loading}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            title="Clear chat"
          >
            <span className="material-symbols-rounded text-sm">delete_sweep</span>
            Clear Chat
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto rounded-md border border-slate-300 bg-white p-4 dark:border-slate-600 dark:bg-slate-950">
        <div className="space-y-3">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[92%] rounded-md px-3 py-2 text-sm ${getMessageStyle(message)}`}>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {loading && <p className="text-xs text-slate-500">AI is processing your message...</p>}
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-3 flex items-end gap-2">
        <div className="relative flex-1">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Describe Interaction..."
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 pr-10 text-sm outline-none focus:border-[#2563eb] dark:border-slate-600 dark:bg-slate-900"
          />
          {supported && (
            <button
              type="button"
              onClick={toggleListening}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              title={isListening ? 'Listening...' : 'Voice to text'}
            >
              <span className="material-symbols-rounded text-base">mic</span>
            </button>
          )}
        </div>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex shrink-0 flex-col items-center gap-0.5 disabled:opacity-60"
          aria-label="Log interaction"
        >
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[#2563eb] text-white shadow-sm hover:bg-[#1d4ed8]">
            <span className="material-symbols-rounded text-lg">north</span>
          </span>
          <span className="text-[11px] font-semibold text-[#2563eb]">Log</span>
        </button>
      </form>
    </div>
  );
};
