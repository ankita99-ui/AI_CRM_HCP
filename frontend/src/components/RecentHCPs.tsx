import { useAppSelector } from '../store/hooks';

export const RecentHCPs = () => {
  const recent = useAppSelector((state) => state.hcp.recent);

  return (
    <section className="glass-panel p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="material-symbols-rounded rounded-2xl bg-slate-100 p-3 text-slate-700 dark:bg-slate-800 dark:text-slate-200">history</span>
        <div>
          <h2 className="text-lg font-semibold">Recent HCPs</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Fast access to the physicians you interacted with most recently.</p>
        </div>
      </div>
      <div className="space-y-3">
        {recent.map((hcp) => (
          <div key={hcp.id} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-semibold">{hcp.doctor_name}</p>
                <p className="text-sm text-slate-500">{hcp.speciality}</p>
              </div>
              <span className="text-xs text-slate-500">{hcp.last_visit ?? 'No visit yet'}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
