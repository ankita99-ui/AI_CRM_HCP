import { createSlice, nanoid, PayloadAction } from '@reduxjs/toolkit';
import { ToastMessage } from '../../types';

interface UiState {
  activeTab: 'form' | 'chat';
  darkMode: boolean;
  toasts: ToastMessage[];
  formResetNonce: number;
}

const initialState: UiState = {
  activeTab: 'form',
  darkMode: false,
  toasts: [],
  formResetNonce: 0,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setActiveTab(state, action: PayloadAction<'form' | 'chat'>) {
      state.activeTab = action.payload;
    },
    toggleDarkMode(state) {
      state.darkMode = !state.darkMode;
    },
    addToast: {
      reducer(state, action: PayloadAction<ToastMessage>) {
        state.toasts.push(action.payload);
      },
      prepare(type: ToastMessage['type'], title: string, description?: string) {
        return { payload: { id: nanoid(), type, title, description } };
      },
    },
    removeToast(state, action: PayloadAction<string>) {
      state.toasts = state.toasts.filter((toast) => toast.id !== action.payload);
    },
    resetInteractionForm(state) {
      state.formResetNonce += 1;
    },
  },
});

export const { setActiveTab, toggleDarkMode, addToast, removeToast, resetInteractionForm } = uiSlice.actions;
export default uiSlice.reducer;
