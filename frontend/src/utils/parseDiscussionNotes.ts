export type ParsedDiscussionNotes = {
  discussion_notes: string;
  attendees: string;
  outcomes: string;
  follow_up_actions: string;
  materials: string;
  samples: string;
};

const stripMarkdown = (value: string) => value.replace(/\*\*/g, '').trim();

export const parseStructuredDiscussionNotes = (raw: string): ParsedDiscussionNotes => {
  if (!raw.trim()) {
    return {
      discussion_notes: '',
      attendees: '',
      outcomes: '',
      follow_up_actions: '',
      materials: '',
      samples: '',
    };
  }

  const topics: string[] = [];
  let attendees = '';
  let outcomes = '';
  let follow_up_actions = '';
  let materials = '';
  let samples = '';

  for (const block of raw.split(/\n\n+/)) {
    const trimmed = stripMarkdown(block);
    if (!trimmed) continue;

    if (/^Attendees:/i.test(trimmed)) {
      attendees = trimmed.replace(/^Attendees:\s*/i, '').trim();
      continue;
    }
    if (/^Outcomes:/i.test(trimmed)) {
      outcomes = trimmed.replace(/^Outcomes:\s*/i, '').trim();
      continue;
    }
    if (/^Follow-up Actions:/i.test(trimmed)) {
      follow_up_actions = trimmed.replace(/^Follow-up Actions:\s*/i, '').trim();
      continue;
    }
    if (/^Materials Shared:/i.test(trimmed)) {
      materials = trimmed.replace(/^Materials Shared:\s*/i, '').trim();
      continue;
    }
    if (/^Samples Distributed:/i.test(trimmed)) {
      samples = trimmed.replace(/^Samples Distributed:\s*/i, '').trim();
      continue;
    }
    if (/^Date:/i.test(trimmed)) {
      continue;
    }

    topics.push(trimmed);
  }

  return {
    discussion_notes: topics.join('\n\n').trim(),
    attendees,
    outcomes,
    follow_up_actions,
    materials,
    samples,
  };
};
