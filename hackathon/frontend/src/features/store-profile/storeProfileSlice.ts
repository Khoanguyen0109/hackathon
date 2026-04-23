import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

interface StoreProfileState {
  selectedStoreId: string | null;
}

const initialState: StoreProfileState = {
  selectedStoreId: null,
};

const storeProfileSlice = createSlice({
  name: "storeProfile",
  initialState,
  reducers: {
    selectStore(state, action: PayloadAction<string>) {
      state.selectedStoreId = action.payload;
    },
  },
});

export const { selectStore } = storeProfileSlice.actions;
export default storeProfileSlice.reducer;
