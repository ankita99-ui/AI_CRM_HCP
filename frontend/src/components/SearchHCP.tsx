import { ChangeEvent, useState } from 'react';
import { motion } from 'framer-motion';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { searchHCPs } from '../store/slices/hcpSlice';

export const SearchHCP = () => {
  const dispatch = useAppDispatch();
  const { searchResults, loading } = useAppSelector((state) => state.hcp);
  const [query, setQuery] = useState('');

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextValue = event.target.value;
    setQuery(nextValue);
    dispatch(searchHCPs(nextValue));
  };

  return (
    <section className="glass-panel p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="material-symbols-rounded rounded-2xl bg-brand-50 p-3 text-brand-600 dark:bg-brand-500/10 dark:text-brand-100">search</span>
        <div>
          <h2 className="text-lg font-semibold">Search HCP</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Search by doctor name, hospital, city, or specialty.</p>
        </div>
      </div>

      <div className="relative">
        <input
          value={query}
          onChange={onChange}
          placeholder="Find Dr Amit Sharma or Sunshine Hospital"
          className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12 text-sm outline-none ring-0 transition focus:border-brand-400 focus:bg-white dark:border-slate-700 dark:bg-slate-950 dark:focus:bg-slate-900"
        />
        <span className="material-symbols-rounded absolute right-4 top-3 text-slate-400">manage_search</span>
      </div>

      <div className="mt-4 space-y-3">
        {loading && <p className="text-sm text-slate-500">Searching HCP records...</p>}
        {!loading && searchResults.slice(0, 3).map((hcp) => (
          <motion.div
            key={hcp.id}
            layout
            className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">{hcp.doctor_name}</h3>
                <p className="text-sm text-slate-500">{hcp.speciality} ? {hcp.hospital}</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {hcp.recent_products.join(', ') || 'No recent products'}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
};
