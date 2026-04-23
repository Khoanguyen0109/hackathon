import { api } from "./api";
import type {
  StaffingRequest,
  StaffingResponse,
  CrewAssignmentRequest,
  CrewAssignmentResponse,
} from "./types";

export const forecastApi = api.injectEndpoints({
  endpoints: (build) => ({
    generateStaffing: build.mutation<StaffingResponse, StaffingRequest>({
      query: (body) => ({
        url: "/api/v1/forecast/staffing",
        method: "POST",
        body,
      }),
    }),
    assignCrew: build.mutation<CrewAssignmentResponse, CrewAssignmentRequest>({
      query: (body) => ({
        url: "/api/v1/forecast/crew-assignment",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const { useGenerateStaffingMutation, useAssignCrewMutation } = forecastApi;
