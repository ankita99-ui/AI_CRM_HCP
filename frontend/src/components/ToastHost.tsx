import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { removeToast } from '../store/slices/uiSlice';

export const ToastHost = () => {
  const dispatch = useAppDispatch();
  const toasts = useAppSelector((state) => state.ui.toasts);

  useEffect(() => {
    const timers = toasts.map((toast) =>
      window.setTimeout(() => {
        dispatch(removeToast(toast.id));
      }, 3200),
    );

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [dispatch, toasts]);

  return (
    <div className="pointer-events-none fixed right-5 top-5 z-50 flex w-full max-w-sm flex-col gap-3">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="pointer-events-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-soft dark:border-slate-700 dark:bg-slate-900"
          >
            <p className="font-semibold">{toast.title}</p>
            {toast.description && <p className="mt-1 text-sm text-slate-500">{toast.description}</p>}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};
