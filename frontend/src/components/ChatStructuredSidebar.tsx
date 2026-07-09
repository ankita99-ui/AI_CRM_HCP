import { useAppDispatch, useAppSelector } from '../store/hooks';
import { createInteraction } from '../store/slices/interactionSlice';
import { addToast } from '../store/slices/uiSlice';
import { ExtractedPreview } from './ExtractedPreview';

export const ChatStructuredSidebar = () => {
  const dispatch = useAppDispatch();
  const { extracted, nextBestAction } = useAppSelector((state) => state.chat);

  const onSaveExtracted = async () => {
    if (!extracted) return;
    const result = await dispatch(createInteraction(extracted));
    if (createInteraction.fulfilled.match(result)) {
      dispatch(addToast('success', 'Interaction saved', 'Extracted interaction stored successfully.'));
    } else {
      dispatch(addToast('error', 'Save failed', result.error.message));
    }
  };

  return (
    <div className="space-y-5">
      <ExtractedPreview extracted={extracted} />
      {extracted && (
        <button
          type="button"
          onClick={onSaveExtracted}
          className="w-full rounded-2xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          Save Extracted Interaction
        </button>
      )}
      <div className="glass-panel p-5">
        <div className="mb-3 flex items-center gap-2">
          <span className="material-symbols-rounded text-brand-600 dark:text-brand-100">tips_and_updates</span>
          <h3 className="font-semibold">Next Best Actions</h3>
        </div>
        <div className="space-y-3">
          {nextBestAction.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Recommendations will appear after the AI analyzes the conversation.</p>
          ) : (
            nextBestAction.map((item) => (
              <div key={item} className="rounded-2xl border border-slate-200 p-4 text-sm dark:border-slate-700">
                {item}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
