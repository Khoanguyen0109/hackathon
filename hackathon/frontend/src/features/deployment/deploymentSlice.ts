import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { AssignedCell } from "../../services/types";

interface DeploymentState {
  cells: AssignedCell[];
  savedDeploymentId: string | null;
}

const initialState: DeploymentState = {
  cells: [],
  savedDeploymentId: null,
};

const deploymentSlice = createSlice({
  name: "deployment",
  initialState,
  reducers: {
    initCells(state, action: PayloadAction<AssignedCell[]>) {
      state.cells = action.payload;
      state.savedDeploymentId = null;
    },
    assignEmployee(
      state,
      action: PayloadAction<{ stationId: string; shift: string; employeeId: string }>
    ) {
      const { stationId, shift, employeeId } = action.payload;
      const cell = state.cells.find(
        (c) => c.station_id === stationId && c.shift === shift
      );
      if (cell && !cell.assigned_employee_ids.includes(employeeId)) {
        cell.assigned_employee_ids.push(employeeId);
      }
    },
    unassignEmployee(
      state,
      action: PayloadAction<{ stationId: string; shift: string; employeeId: string }>
    ) {
      const { stationId, shift, employeeId } = action.payload;
      const cell = state.cells.find(
        (c) => c.station_id === stationId && c.shift === shift
      );
      if (cell) {
        cell.assigned_employee_ids = cell.assigned_employee_ids.filter(
          (id) => id !== employeeId
        );
      }
    },
    setSavedDeploymentId(state, action: PayloadAction<string>) {
      state.savedDeploymentId = action.payload;
    },
  },
});

export const { initCells, assignEmployee, unassignEmployee, setSavedDeploymentId } =
  deploymentSlice.actions;
export default deploymentSlice.reducer;
