import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { hcpService } from '../../services/hcpService';
import { HCPRecord } from '../../types';

interface HCPState {
  searchResults: HCPRecord[];
  recent: HCPRecord[];
  loading: boolean;
}

const initialState: HCPState = {
  searchResults: [],
  recent: [],
  loading: false,
};

export const searchHCPs = createAsyncThunk('hcp/search', async (query: string) => hcpService.search(query));
export const fetchRecentHCPs = createAsyncThunk('hcp/recent', async () => hcpService.search(''));

const hcpSlice = createSlice({
  name: 'hcp',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(searchHCPs.pending, (state) => {
        state.loading = true;
      })
      .addCase(searchHCPs.fulfilled, (state, action) => {
        state.loading = false;
        state.searchResults = action.payload;
      })
      .addCase(searchHCPs.rejected, (state) => {
        state.loading = false;
      })
      .addCase(fetchRecentHCPs.fulfilled, (state, action) => {
        state.recent = action.payload.slice(0, 4);
      });
  },
});

export default hcpSlice.reducer;
