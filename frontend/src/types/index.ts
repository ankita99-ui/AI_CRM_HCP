export type InteractionType = 'visit' | 'call' | 'email' | 'conference';

export interface HCPRecord {
  id: number;
  doctor_name: string;
  hospital: string;
  speciality: string;
  city?: string | null;
  email?: string | null;
  last_visit?: string | null;
  recent_products: string[];
  history_summary?: string | null;
}

export interface ExtractedInteraction {
  doctor_name: string;
  hospital?: string;
  interaction_type: InteractionType;
  interaction_date?: string | null;
  interaction_time?: string | null;
  discussion_notes: string;
  summary: string;
  products_discussed: string[];
  materials_shared?: string[];
  follow_up_date?: string | null;
  follow_up_actions?: string | null;
  sentiment?: string | null;
  status?: string;
}

export interface InteractionRecord extends ExtractedInteraction {
  id: number;
  hcp_id?: number | null;
  created_at: string;
  updated_at: string;
  attachments: AttachmentRecord[];
}

export interface AttachmentRecord {
  id: number;
  file_name: string;
  file_url: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
}

export interface ChatResponse {
  message: string;
  extracted: ExtractedInteraction;
  next_best_action: string[];
  save_result?: InteractionRecord | null;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  title: string;
  description?: string;
}

export interface DashboardMetrics {
  total_interactions: number;
  pending_follow_ups: number;
  unique_hcps: number;
}
