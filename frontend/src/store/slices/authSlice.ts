import { createSlice } from '@reduxjs/toolkit';

interface AuthState {
  user: { id: number; name: string; email: string } | null;
  token: string | null;
}

const initialState: AuthState = {
  user: { id: 1, name: 'Ava Medical Rep', email: 'ava.rep@aicrm.local' },
  token: 'demo-session-token',
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {},
});

export default authSlice.reducer;
