import { useEffect } from 'react';
import { Header } from '../components/Header';
import { StructuredForm } from '../components/StructuredForm';
import { ChatPanel } from '../components/ChatPanel';
import { ToastHost } from '../components/ToastHost';
import { useAppDispatch } from '../store/hooks';
import { fetchRecentHCPs } from '../store/slices/hcpSlice';
import { fetchInteractions } from '../store/slices/interactionSlice';

export const LogInteractionPage = () => {
  const dispatch = useAppDispatch();

  useEffect(() => {
    void dispatch(fetchRecentHCPs());
    void dispatch(fetchInteractions());
  }, [dispatch]);

  return (
    <div className="min-h-screen bg-[#ececec] px-4 py-5 text-slate-900 dark:bg-slate-950 dark:text-slate-100 md:px-6">
      <ToastHost />
      <div className="mx-auto max-w-[1400px]">
        <Header />
        <div className="mt-1 grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <section className="rounded-md border border-slate-300 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <StructuredForm />
          </section>
          <section className="rounded-md border border-slate-300 bg-[#f7f7f7] p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
            <ChatPanel />
          </section>
        </div>
      </div>
    </div>
  );
};
