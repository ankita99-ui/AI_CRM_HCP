import { api } from './api';
import { ChatMessage, ChatResponse } from '../types';

type ChatPayload = {
  content: string;
  history?: Array<Pick<ChatMessage, 'role' | 'content'>>;
  save?: boolean;
};

export const chatService = {
  async send(payload: ChatPayload): Promise<ChatResponse> {
    const { data } = await api.post('/api/chat', payload);
    return data;
  },
  async stream(payload: ChatPayload, onToken: (token: string) => void): Promise<ChatResponse> {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
      let message = 'Streaming request failed';
      try {
        const errorBody = await response.json() as { detail?: string | Array<{ msg?: string }> };
        if (Array.isArray(errorBody.detail)) {
          message = errorBody.detail.map((item) => item.msg).filter(Boolean).join(', ') || message;
        } else if (typeof errorBody.detail === 'string') {
          message = errorBody.detail;
        }
      } catch {
        // Keep default message when error body is not JSON.
      }
      throw new Error(message);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalPayload: ChatResponse | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';

      for (const event of events) {
        const line = event.trim().replace(/^data:\s*/, '');
        if (!line) continue;
        const parsed = JSON.parse(line) as { type: string; content?: string } & ChatResponse;
        if (parsed.type === 'token' && parsed.content) {
          onToken(parsed.content);
        }
        if (parsed.type === 'complete') {
          finalPayload = {
            message: parsed.message,
            extracted: parsed.extracted,
            next_best_action: parsed.next_best_action,
            save_result: parsed.save_result,
          };
        }
      }
    }

    if (!finalPayload) {
      throw new Error('Streaming completed without a final payload');
    }

    return finalPayload;
  },
  async generateEmail(payload: Record<string, unknown>): Promise<{ subject: string; body: string }> {
    const { data } = await api.post('/api/email', payload);
    return data;
  },
  async nextAction(payload: Record<string, unknown>): Promise<{ recommendations: string[] }> {
    const { data } = await api.post('/api/next-action', payload);
    return data;
  },
};
