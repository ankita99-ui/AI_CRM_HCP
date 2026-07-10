export const FORM_DRAFT_KEY = 'interaction-form-draft';

export type InteractionFormValues = {
  doctor_name: string;
  interaction_type: 'visit' | 'call' | 'email' | 'conference';
  interaction_date: string;
  interaction_time: string;
  attendees: string;
  discussion_notes: string;
  products_discussed: string;
  samples_distributed: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  outcomes: string;
  follow_up_actions: string;
  follow_up_date: string;
  attachments: string;
};

export const getBlankFormValues = (): InteractionFormValues => ({
  doctor_name: '',
  interaction_type: 'visit',
  interaction_date: '',
  interaction_time: '',
  attendees: '',
  discussion_notes: '',
  products_discussed: '',
  samples_distributed: '',
  sentiment: 'neutral',
  outcomes: '',
  follow_up_actions: '',
  follow_up_date: '',
  attachments: '',
});

export const clearFormDraft = () => {
  localStorage.removeItem(FORM_DRAFT_KEY);
};
