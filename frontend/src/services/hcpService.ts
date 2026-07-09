import { api } from './api';
import { HCPRecord } from '../types';

export const hcpService = {
  async search(query: string): Promise<HCPRecord[]> {
    const { data } = await api.get('/api/hcp/search', { params: { query } });
    return data;
  },
  async getById(id: number): Promise<HCPRecord> {
    const { data } = await api.get(`/api/hcp/${id}`);
    return data;
  },
};
