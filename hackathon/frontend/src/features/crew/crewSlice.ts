import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

interface CrewState {
  editingEmployeeId: string | null;
  addDialogOpen: boolean;
}

const initialState: CrewState = {
  editingEmployeeId: null,
  addDialogOpen: false,
};

const crewSlice = createSlice({
  name: "crew",
  initialState,
  reducers: {
    openEditDialog(state, action: PayloadAction<string>) {
      state.editingEmployeeId = action.payload;
    },
    closeEditDialog(state) {
      state.editingEmployeeId = null;
    },
    openAddDialog(state) {
      state.addDialogOpen = true;
    },
    closeAddDialog(state) {
      state.addDialogOpen = false;
    },
  },
});

export const { openEditDialog, closeEditDialog, openAddDialog, closeAddDialog } =
  crewSlice.actions;
export default crewSlice.reducer;
