import { useEffect, useMemo, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { createInteraction, setDraft } from '../store/slices/interactionSlice';
import { addToast } from '../store/slices/uiSlice';
import { sendChatMessage } from '../store/slices/chatSlice';
import { loadAutoSaved, useAutoSave } from '../hooks/useAutoSave';
import { useVoiceInput } from '../hooks/useVoiceInput';

const formSchema = z.object({
  doctor_name: z.string().min(2, 'HCP name is required'),
  interaction_type: z.enum(['visit', 'call', 'email', 'conference']),
  interaction_date: z.string().optional(),
  interaction_time: z.string().optional(),
  attendees: z.string().optional(),
  discussion_notes: z.string().min(10, 'Topics discussed are required'),
  products_discussed: z.string().optional(),
  samples_distributed: z.string().optional(),
  sentiment: z.enum(['positive', 'neutral', 'negative']),
  outcomes: z.string().optional(),
  follow_up_actions: z.string().optional(),
  follow_up_date: z.string().optional(),
  attachments: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

const now = new Date();
const defaultDate = now.toISOString().slice(0, 10);
const defaultTime = now.toTimeString().slice(0, 5);

const defaultValues: FormValues = {
  doctor_name: '',
  interaction_type: 'visit',
  interaction_date: defaultDate,
  interaction_time: defaultTime,
  attendees: '',
  discussion_notes: '',
  products_discussed: '',
  samples_distributed: '',
  sentiment: 'neutral',
  outcomes: '',
  follow_up_actions: '',
  follow_up_date: '',
  attachments: '',
};

const labelClass = 'mb-1 block text-sm font-medium text-slate-800 dark:text-slate-200';
const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-[#2563eb] dark:border-slate-600 dark:bg-slate-900';

const toDateInputValue = (value?: string | null) => {
  if (!value) return null;
  const normalized = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(normalized)) {
    return normalized.slice(0, 10);
  }
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().slice(0, 10);
};

const toTimeInputValue = (value?: string | null) => {
  if (!value) return null;
  const normalized = String(value).trim();
  const twentyFourHour = normalized.match(/^(\d{1,2}):(\d{2})/);
  if (twentyFourHour) {
    return `${twentyFourHour[1].padStart(2, '0')}:${twentyFourHour[2]}`;
  }
  const twelveHour = normalized.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);
  if (!twelveHour) return null;
  let hour = Number(twelveHour[1]);
  const minute = twelveHour[2] ?? '00';
  const meridiem = twelveHour[3].toLowerCase();
  if (meridiem === 'pm' && hour < 12) hour += 12;
  if (meridiem === 'am' && hour === 12) hour = 0;
  return `${String(hour).padStart(2, '0')}:${minute}`;
};

export const StructuredForm = () => {
  const dispatch = useAppDispatch();
  const saving = useAppSelector((state) => state.interactions.saving);
  const extracted = useAppSelector((state) => state.chat.extracted);
  const nextBestAction = useAppSelector((state) => state.chat.nextBestAction);
  const persistedDraft = useMemo(() => loadAutoSaved('interaction-form-draft', defaultValues), []);
  const [materials, setMaterials] = useState<string[]>([]);
  const [samples, setSamples] = useState<string[]>([]);

  const {
    register,
    handleSubmit,
    getValues,
    watch,
    reset,
    setValue,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: persistedDraft,
  });

  useAutoSave('interaction-form-draft', watch());

  const { isListening, toggleListening, supported } = useVoiceInput((transcript) => {
    const current = getValues('discussion_notes');
    setValue('discussion_notes', [current, transcript].filter(Boolean).join(' '));
  });

  useEffect(() => {
    if (!extracted) return;

    const current = getValues();
    const nextDate = toDateInputValue(extracted.interaction_date) ?? current.interaction_date;
    const nextTime = toTimeInputValue(extracted.interaction_time) ?? current.interaction_time;
    const nextFollowUpDate = toDateInputValue(extracted.follow_up_date) ?? current.follow_up_date ?? '';
    const nextFollowUpActions =
      extracted.follow_up_actions?.trim() ||
      (nextBestAction.length ? nextBestAction.join('\n') : '') ||
      current.follow_up_actions;

    const nextValues: FormValues = {
      ...current,
      doctor_name:
        extracted.doctor_name && extracted.doctor_name !== 'Unknown Doctor'
          ? extracted.doctor_name
          : current.doctor_name,
      discussion_notes: extracted.summary || extracted.discussion_notes || current.discussion_notes,
      interaction_type: extracted.interaction_type,
      interaction_date: nextDate,
      interaction_time: nextTime,
      products_discussed: extracted.products_discussed.join(', '),
      follow_up_date: nextFollowUpDate,
      follow_up_actions: nextFollowUpActions,
      sentiment: extracted.sentiment ?? current.sentiment,
      outcomes: extracted.summary || extracted.discussion_notes || current.outcomes,
    };

    reset(nextValues);
    setValue('interaction_date', nextDate, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('interaction_time', nextTime, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('follow_up_date', nextFollowUpDate, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('follow_up_actions', nextFollowUpActions, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    localStorage.setItem('interaction-form-draft', JSON.stringify(nextValues));

    const shared = extracted.materials_shared ?? [];
    const materialItems = shared.filter((item) => item !== 'Samples');
    const sampleItems = shared.filter((item) => item === 'Samples');
    setMaterials(materialItems);
    if (sampleItems.length) {
      setSamples(sampleItems);
      setValue('samples_distributed', sampleItems.join(', '), {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });
    }
  }, [extracted, nextBestAction, getValues, reset, setValue]);

  const onSubmit = async (values: FormValues) => {
    const discussionNotes = [
      values.discussion_notes,
      values.attendees ? `Attendees: ${values.attendees}` : '',
      materials.length ? `Materials Shared: ${materials.join(', ')}` : '',
      values.samples_distributed ? `Samples Distributed: ${values.samples_distributed}` : '',
      values.outcomes ? `Outcomes: ${values.outcomes}` : '',
      values.follow_up_actions ? `Follow-up Actions: ${values.follow_up_actions}` : '',
      values.interaction_date ? `Date: ${values.interaction_date} ${values.interaction_time ?? ''}`.trim() : '',
    ]
      .filter(Boolean)
      .join('\n\n');

    const payload = {
      doctor_name: values.doctor_name,
      interaction_type: values.interaction_type,
      discussion_notes: discussionNotes,
      products_discussed: values.products_discussed
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      follow_up_date: values.follow_up_date || undefined,
      sentiment: values.sentiment,
      summary: values.outcomes || values.discussion_notes,
      attachments: values.attachments
        ? values.attachments.split(',').map((item) => ({ file_name: item.trim(), file_url: item.trim() }))
        : [],
    };

    dispatch(setDraft(payload));
    const result = await dispatch(createInteraction(payload));
    if (createInteraction.fulfilled.match(result)) {
      dispatch(addToast('success', 'Interaction saved', 'The HCP interaction was stored successfully.'));
    } else {
      dispatch(addToast('error', 'Save failed', result.error.message));
    }
  };

  const onVoiceSummarize = async () => {
    const values = getValues();
    const result = await dispatch(
      sendChatMessage({
        content: `Doctor: ${values.doctor_name}
Interaction Type: ${values.interaction_type}
Notes: ${values.discussion_notes}
Products: ${values.products_discussed}
Follow-up Date: ${values.follow_up_date}`,
        save: false,
      }),
    );
    if (sendChatMessage.fulfilled.match(result)) {
      dispatch(addToast('success', 'AI summary ready', 'Voice note summary has been applied to the form.'));
    }
  };

  const addMaterial = () => {
    const value = window.prompt('Enter material name');
    if (!value?.trim()) return;
    setMaterials((current) => [...current, value.trim()]);
  };

  const addSample = () => {
    const value = window.prompt('Enter sample name');
    if (!value?.trim()) return;
    const next = [...samples, value.trim()];
    setSamples(next);
    setValue('samples_distributed', next.join(', '));
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <h2 className="mb-4 text-[1.35rem] font-bold text-slate-900 dark:text-white">Log HCP Interaction</h2>

      <div className="grid gap-4 md:grid-cols-2">
        <label className={labelClass}>
          HCP Name
          <input {...register('doctor_name')} className={inputClass} placeholder="Search or select HCP..." />
          {errors.doctor_name && <span className="mt-1 block text-xs text-rose-500">{errors.doctor_name.message}</span>}
        </label>

        <label className={labelClass}>
          Interaction Type
          <select {...register('interaction_type')} className={inputClass}>
            <option value="visit">Meeting</option>
            <option value="call">Call</option>
            <option value="email">Email</option>
            <option value="conference">Conference</option>
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className={labelClass}>
          Date
          <Controller
            name="interaction_date"
            control={control}
            render={({ field }) => (
              <input {...field} value={field.value ?? ''} type="date" className={inputClass} />
            )}
          />
        </label>
        <label className={labelClass}>
          Time
          <Controller
            name="interaction_time"
            control={control}
            render={({ field }) => (
              <input {...field} value={field.value ?? ''} type="time" className={inputClass} />
            )}
          />
        </label>
      </div>

      <label className={labelClass}>
        Attendees
        <input {...register('attendees')} className={inputClass} placeholder="Enter names or search..." />
      </label>

      <label className={labelClass}>
        Topics Discussed
        <div className="relative">
          <textarea
            {...register('discussion_notes')}
            rows={5}
            className={`${inputClass} resize-y pr-10`}
            placeholder="Enter key discussion points..."
          />
          {supported && (
            <button
              type="button"
              onClick={toggleListening}
              className="absolute bottom-3 right-3 text-slate-400 hover:text-slate-600"
              title={isListening ? 'Listening...' : 'Voice to text'}
            >
              <span className="material-symbols-rounded text-lg">mic</span>
            </button>
          )}
        </div>
        {errors.discussion_notes && <span className="mt-1 block text-xs text-rose-500">{errors.discussion_notes.message}</span>}
        <button
          type="button"
          onClick={onVoiceSummarize}
          className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-[#2563eb] dark:text-slate-300"
        >
          <span className="material-symbols-rounded text-sm">auto_awesome</span>
          Summarize from Voice Note (Requires Consent)
        </button>
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-md border border-slate-300 p-3 dark:border-slate-600">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200">Materials Shared</span>
            <button type="button" onClick={addMaterial} className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-[#2563eb]">
              <span className="material-symbols-rounded text-sm">search</span>
              Search/Add
            </button>
          </div>
          <p className="text-xs italic text-slate-500">{materials.length ? materials.join(', ') : 'No materials added.'}</p>
        </div>

        <div className="rounded-md border border-slate-300 p-3 dark:border-slate-600">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200">Samples Distributed</span>
            <button type="button" onClick={addSample} className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-[#2563eb]">
              <span className="material-symbols-rounded text-sm">medication</span>
              Add Sample
            </button>
          </div>
          <p className="text-xs italic text-slate-500">{samples.length ? samples.join(', ') : 'No samples added.'}</p>
        </div>
      </div>

      <fieldset>
        <legend className={`${labelClass} mb-2`}>Observed/Inferred HCP Sentiment</legend>
        <div className="flex flex-wrap gap-5 text-sm">
          {[
            { value: 'positive', label: 'Positive', emoji: '🙂' },
            { value: 'neutral', label: 'Neutral', emoji: '😐' },
            { value: 'negative', label: 'Negative', emoji: '🙁' },
          ].map((option) => (
            <label key={option.value} className="inline-flex items-center gap-2">
              <span>{option.emoji}</span>
              <input type="radio" value={option.value} {...register('sentiment')} className="accent-[#2563eb]" />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className={labelClass}>
        Outcomes
        <textarea {...register('outcomes')} rows={3} className={`${inputClass} resize-y`} placeholder="Key outcomes or agreements..." />
      </label>

      <label className={labelClass}>
        Follow-up Actions
        <textarea
          {...register('follow_up_actions')}
          rows={3}
          className={`${inputClass} resize-y`}
          placeholder="Enter next steps or tasks..."
        />
      </label>

      <label className={labelClass}>
        Follow-up Date
        <Controller
          name="follow_up_date"
          control={control}
          render={({ field }) => (
            <input {...field} value={field.value ?? ''} type="date" className={inputClass} />
          )}
        />
      </label>

      <div>
        <p className="mb-2 text-sm font-medium text-slate-800 dark:text-slate-200">AI Suggested Follow-ups:</p>
        <div className="space-y-1">
          {(nextBestAction.length ? nextBestAction : [
            'Schedule follow-up meeting in 2 weeks',
            'Send OncoBoost Phase III PDF',
            'Add Dr. Sharma to advisory board invite list',
          ]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setValue('follow_up_actions', [getValues('follow_up_actions'), item].filter(Boolean).join('\n'))}
              className="block text-left text-sm text-[#2563eb] hover:underline"
            >
              + {item}
            </button>
          ))}
        </div>
      </div>

      <input type="hidden" {...register('products_discussed')} />
      <input type="hidden" {...register('samples_distributed')} />
      <input type="hidden" {...register('attachments')} />

      <div className="flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4 dark:border-slate-700">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-md bg-[#2563eb] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1d4ed8] disabled:opacity-70"
        >
          <span className="material-symbols-rounded text-base">save</span>
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </form>
  );
};
