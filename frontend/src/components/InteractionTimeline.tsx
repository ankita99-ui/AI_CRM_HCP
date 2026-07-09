import { format } from 'date-fns';
import { useAppSelector } from '../store/hooks';

export const InteractionTimeline = () => {
  const items = useAppSelector((state) => state.interactions.items.slice(0, 5));

  return (
    <section className="glass-panel p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="material-symbols-rounded rounded-2xl bg-slate-100 p-3 text-slate-700 dark:bg-slate-800 dark:text-slate-200">monitoring</span>
        <div>
          <h2 className="text-lg font-semibold">Recent Interactions</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">A quick view of the latest interaction activity and follow-up momentum.</p>
        </div>
      </div>
      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.id} className="flex gap-4">
            <div className="mt-1 h-3 w-3 rounded-full bg-brand-600" />
            <div className="flex-1 rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="flex flex-wrap justify-between gap-2">
                <p className="font-semibold">{item.doctor_name}</p>
                <p className="text-xs text-slate-500">{format(new Date(item.created_at), 'dd MMM yyyy, hh:mm a')}</p>
              </div>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{item.summary}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
