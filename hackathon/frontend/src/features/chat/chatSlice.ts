import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { ChatMessage, ChatAction } from "../../services/types";

interface ChatState {
  messages: ChatMessage[];
  inputDraft: string;
  loading: boolean;
}

const initialState: ChatState = {
  messages: [],
  inputDraft: "",
  loading: false,
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload);
    },
    setInputDraft(state, action: PayloadAction<string>) {
      state.inputDraft = action.payload;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.loading = action.payload;
    },
    markActionApplied(
      state,
      action: PayloadAction<{ messageId: string; actionIndex: number }>
    ) {
      const msg = state.messages.find((m) => m.id === action.payload.messageId);
      if (msg?.actions?.[action.payload.actionIndex]) {
        (msg.actions[action.payload.actionIndex] as ChatAction & { applied?: boolean }).applied = true;
      }
    },
    clearChat(state) {
      state.messages = [];
      state.inputDraft = "";
      state.loading = false;
    },
  },
});

export const { addMessage, setInputDraft, setLoading, markActionApplied, clearChat } =
  chatSlice.actions;
export default chatSlice.reducer;
