import { ExtractedInteraction } from '../types';
import { InteractionFormValues } from './formDefaults';
import { parseStructuredDiscussionNotes } from './parseDiscussionNotes';

const VALID_SENTIMENTS = ['positive', 'neutral', 'negative'] as const;

const VALID_INTERACTION_TYPES = ['visit', 'call', 'email', 'conference'] as const;

const normalizeInteractionType = (value?: string): InteractionFormValues['interaction_type'] => {
  const lower = (value || 'visit').toLowerCase();
  if (lower === 'meeting') return 'visit';
  return VALID_INTERACTION_TYPES.includes(lower as InteractionFormValues['interaction_type'])
    ? (lower as InteractionFormValues['interaction_type'])
    : 'visit';
};

const cleanDoctorName = (value?: string) =>
  (value || '')
    .replace(/\s+(today|yesterday|tomorrow)\s*$/i, '')
    .trim();

const toDateInputValue = (value?: string | null) => {
  if (!value) return '';
  const normalized = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(normalized)) {
    return normalized.slice(0, 10);
  }
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toISOString().slice(0, 10);
};

const toTimeInputValue = (value?: string | null) => {
  if (!value) return '';
  const normalized = String(value).trim();
  const twentyFourHour = normalized.match(/^(\d{1,2}):(\d{2})/);
  if (twentyFourHour) {
    return `${twentyFourHour[1].padStart(2, '0')}:${twentyFourHour[2]}`;
  }
  const twelveHour = normalized.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);
  if (!twelveHour) return '';
  let hour = Number(twelveHour[1]);
  const minute = twelveHour[2] ?? '00';
  const meridiem = twelveHour[3].toLowerCase();
  if (meridiem === 'pm' && hour < 12) hour += 12;
  if (meridiem === 'am' && hour === 12) hour = 0;
  return `${String(hour).padStart(2, '0')}:${minute}`;
};

export const buildFormFromExtracted = (
  extracted: ExtractedInteraction,
  nextBestAction: string[] = [],
): InteractionFormValues => {
  const parsed = parseStructuredDiscussionNotes(extracted.discussion_notes || '');
  const sentiment = VALID_SENTIMENTS.includes(
    (extracted.sentiment || 'neutral') as (typeof VALID_SENTIMENTS)[number],
  )
    ? ((extracted.sentiment || 'neutral') as InteractionFormValues['sentiment'])
    : 'neutral';

  return {
    doctor_name:
      extracted.doctor_name && extracted.doctor_name !== 'Unknown Doctor'
        ? cleanDoctorName(extracted.doctor_name)
        : '',
    interaction_type: normalizeInteractionType(extracted.interaction_type),
    interaction_date: toDateInputValue(extracted.interaction_date),
    interaction_time: toTimeInputValue(extracted.interaction_time),
    attendees: parsed.attendees || '',
    products_discussed: extracted.products_discussed?.join(', ') || '',
    discussion_notes: parsed.discussion_notes || extracted.summary || '',
    samples_distributed: parsed.samples || '',
    sentiment,
    outcomes: parsed.outcomes || extracted.summary || '',
    follow_up_actions:
      parsed.follow_up_actions || extracted.follow_up_actions?.trim() || nextBestAction[0] || '',
    follow_up_date: toDateInputValue(extracted.follow_up_date),
    attachments: '',
  };
};

export const getMaterialsFromExtracted = (extracted: ExtractedInteraction, parsedMaterials: string) => {
  if (parsedMaterials) {
    return parsedMaterials.split(',').map((item) => item.trim()).filter(Boolean);
  }
  return (extracted.materials_shared ?? []).filter((item) => item !== 'Samples');
};

export const getSamplesFromExtracted = (extracted: ExtractedInteraction, parsedSamples: string) => {
  if (parsedSamples) {
    return parsedSamples.split(',').map((item) => item.trim()).filter(Boolean);
  }
  return (extracted.materials_shared ?? []).filter((item) => item === 'Samples');
};
