import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { toggleDarkMode } from '../store/slices/uiSlice';

export const Header = () => {
  const dispatch = useAppDispatch();
  const darkMode = useAppSelector((state) => state.ui.darkMode);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  return (
    <div className="flex justify-end">
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={() => dispatch(toggleDarkMode())}
        className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
      >
        <span className="material-symbols-rounded text-base">{darkMode ? 'light_mode' : 'dark_mode'}</span>
        {darkMode ? 'Light Mode' : 'Dark Mode'}
      </motion.button>
    </div>
  );
};
