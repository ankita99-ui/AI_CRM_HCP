import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import { InteractionRecord, ExtractedInteraction } from '../../types';
import { interactionService } from '../../services/interactionService';

interface InteractionState {
  items: InteractionRecord[];
  loading: boolean;
  saving: boolean;
  draft: Record<string, unknown>;
}

const initialState: InteractionState = {
  items: [],
  loading: false,
  saving: false,
  draft: {},
};

export const fetchInteractions = createAsyncThunk('interactions/fetch', async () => interactionService.list());
export const createInteraction = createAsyncThunk(
  'interactions/create',
  async (payload: Record<string, unknown> | ExtractedInteraction) => interactionService.create(payload as Record<string, unknown>),
);

const interactionSlice = createSlice({
  name: 'interactions',
  initialState,
  reducers: {
    setDraft(state, action: PayloadAction<Record<string, unknown>>) {
      state.draft = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state) => {
        state.loading = false;
      })
      .addCase(createInteraction.pending, (state) => {
        state.saving = true;
      })
      .addCase(createInteraction.fulfilled, (state, action) => {
        state.saving = false;
        state.items = [action.payload, ...state.items];
      })
      .addCase(createInteraction.rejected, (state) => {
        state.saving = false;
      });
  },
});

export const { setDraft } = interactionSlice.actions;
export default interactionSlice.reducer;
