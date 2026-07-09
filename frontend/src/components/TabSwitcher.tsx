import { motion } from 'framer-motion';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { setActiveTab } from '../store/slices/uiSlice';

export const TabSwitcher = () => {
  const dispatch = useAppDispatch();
  const activeTab = useAppSelector((state) => state.ui.activeTab);

  return (
    <div className="glass-panel relative flex gap-2 p-2">
      {['form', 'chat'].map((tab) => (
        <button
          key={tab}
          onClick={() => dispatch(setActiveTab(tab as 'form' | 'chat'))}
          className={`relative z-10 flex-1 rounded-2xl px-4 py-3 text-sm font-semibold capitalize transition ${
            tab === activeTab ? 'text-white' : 'text-slate-600 dark:text-slate-300'
          }`}
        >
          {tab === activeTab && (
            <motion.div
              layoutId="active-tab"
              className="absolute inset-0 rounded-2xl bg-brand-600 shadow-lg"
            />
          )}
          <span className="relative z-10 text-inherit">{tab === 'form' ? 'Structured Form' : 'Conversational Chat'}</span>
        </button>
      ))}
    </div>
  );
};
