import { useEffect, useRef, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { createInteraction, setDraft } from '../store/slices/interactionSlice';
import { addToast } from '../store/slices/uiSlice';
import { sendChatMessage } from '../store/slices/chatSlice';
import { useAutoSave } from '../hooks/useAutoSave';
import { useVoiceInput } from '../hooks/useVoiceInput';
import { clearFormDraft, FORM_DRAFT_KEY, getBlankFormValues } from '../utils/formDefaults';
import { buildFormFromExtracted, getMaterialsFromExtracted, getSamplesFromExtracted } from '../utils/buildFormFromExtracted';
import { parseStructuredDiscussionNotes } from '../utils/parseDiscussionNotes';

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

const labelClass = 'mb-1 block text-sm font-medium text-slate-800 dark:text-slate-200';
const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-[#2563eb] dark:border-slate-600 dark:bg-slate-900';

export const StructuredForm = () => {
  const dispatch = useAppDispatch();
  const saving = useAppSelector((state) => state.interactions.saving);
  const extracted = useAppSelector((state) => state.chat.extracted);
  const nextBestAction = useAppSelector((state) => state.chat.nextBestAction);
  const formResetNonce = useAppSelector((state) => state.ui.formResetNonce);
  const prevResetNonce = useRef(formResetNonce);
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
    defaultValues: getBlankFormValues(),
  });

  useAutoSave(FORM_DRAFT_KEY, watch());

  const resetFormToBlank = () => {
    const blank = getBlankFormValues();
    reset(blank);
    setMaterials([]);
    setSamples([]);
    clearFormDraft();
    dispatch(setDraft({}));
  };

  useEffect(() => {
    if (formResetNonce === prevResetNonce.current) return;
    prevResetNonce.current = formResetNonce;
    resetFormToBlank();
  }, [formResetNonce, reset, dispatch]);

  const { isListening, toggleListening, supported } = useVoiceInput((transcript) => {
    const current = getValues('discussion_notes');
    setValue('discussion_notes', [current, transcript].filter(Boolean).join(' '));
  });

  useEffect(() => {
    if (!extracted) return;

    const parsed = parseStructuredDiscussionNotes(extracted.discussion_notes || '');
    const nextValues = buildFormFromExtracted(extracted, nextBestAction);

    reset(nextValues);
    setValue('interaction_date', nextValues.interaction_date, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('interaction_time', nextValues.interaction_time, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('follow_up_date', nextValues.follow_up_date, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('follow_up_actions', nextValues.follow_up_actions, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    localStorage.setItem(FORM_DRAFT_KEY, JSON.stringify(nextValues));

    setMaterials(getMaterialsFromExtracted(extracted, parsed.materials));
    const sampleItems = getSamplesFromExtracted(extracted, parsed.samples);
    setSamples(sampleItems);
    setValue('samples_distributed', sampleItems.join(', '), {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: true,
    });
  }, [extracted, nextBestAction, reset, setValue]);

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
      dispatch(addToast('error', 'Save failed', result.error.message ?? 'Could not save interaction.'));
    }
  };

  const onInvalid = () => {
    dispatch(
      addToast('error', 'Save failed', 'Please check HCP name and topics discussed — both are required.'),
    );
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
    <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="space-y-5">
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
        Products Discussed
        <input
          {...register('products_discussed')}
          className={inputClass}
          placeholder="e.g. Product X, Product Y"
        />
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
