import { ExtractedInteraction } from '../types';

interface Props {
  extracted: ExtractedInteraction | null;
}

export const ExtractedPreview = ({ extracted }: Props) => {
  if (!extracted) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 p-5 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
        AI extracted information will appear here before saving.
      </div>
    );
  }

  const rows = [
    ['HCP Name', extracted.doctor_name],
    ['Hospital/Clinic', extracted.hospital || 'Not provided'],
    ['Meeting Date', extracted.interaction_date || 'Not provided'],
    ['Meeting Time', extracted.interaction_time || 'Not provided'],
    ['Interaction Type', extracted.interaction_type],
    ['Discussion Summary', extracted.summary],
    ['Products', extracted.products_discussed.join(', ')],
    ['Follow-up Date', extracted.follow_up_date || 'Not provided'],
    ['Sentiment', extracted.sentiment || 'Neutral'],
  ];

  return (
    <div className="rounded-3xl border border-brand-100 bg-brand-50/70 p-5 dark:border-brand-500/20 dark:bg-brand-500/10">
      <div className="mb-4 flex items-center gap-2">
        <span className="material-symbols-rounded text-brand-600 dark:text-brand-100">auto_awesome</span>
        <h3 className="font-semibold text-brand-700 dark:text-brand-100">Extracted Interaction Details</h3>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-2xl bg-white/80 p-4 dark:bg-slate-900/70">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{label}</p>
            <p className="mt-2 text-sm text-slate-700 dark:text-slate-100">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
