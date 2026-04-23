import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { StaffingResponse, ContextResponse } from "../../services/types";

interface SuggestionState {
  targetDate: string;
  context: ContextResponse | null;
  staffing: StaffingResponse | null;
  generating: boolean;
  chatOpen: boolean;
}

const today = new Date().toISOString().slice(0, 10);

const initialState: SuggestionState = {
  targetDate: today,
  context: null,
  staffing: null,
  generating: false,
  chatOpen: false,
};

const suggestionSlice = createSlice({
  name: "suggestion",
  initialState,
  reducers: {
    setTargetDate(state, action: PayloadAction<string>) {
      state.targetDate = action.payload;
      state.staffing = null;
    },
    setContext(state, action: PayloadAction<ContextResponse>) {
      state.context = action.payload;
    },
    setStaffing(state, action: PayloadAction<StaffingResponse>) {
      state.staffing = action.payload;
      state.generating = false;
    },
    setGenerating(state, action: PayloadAction<boolean>) {
      state.generating = action.payload;
    },
    toggleChat(state) {
      state.chatOpen = !state.chatOpen;
    },
    setChatOpen(state, action: PayloadAction<boolean>) {
      state.chatOpen = action.payload;
    },
  },
});

export const { setTargetDate, setContext, setStaffing, setGenerating, toggleChat, setChatOpen } =
  suggestionSlice.actions;
export default suggestionSlice.reducer;
