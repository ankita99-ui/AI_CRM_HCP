import { api } from './api';
import { InteractionRecord } from '../types';

export const interactionService = {
  async list(): Promise<InteractionRecord[]> {
    const { data } = await api.get('/api/interactions');
    return data;
  },
  async create(payload: Record<string, unknown>): Promise<InteractionRecord> {
    const { data } = await api.post('/api/interactions', payload);
    return data;
  },
  async update(id: number, payload: Record<string, unknown>): Promise<InteractionRecord> {
    const { data } = await api.put(`/api/interactions/${id}`, payload);
    return data;
  },
};
