import { api } from "./api";
import type { StaffingRequest, StaffingResponse } from "./types";

export const forecastApi = api.injectEndpoints({
  endpoints: (build) => ({
    generateStaffing: build.mutation<StaffingResponse, StaffingRequest>({
      query: (body) => ({
        url: "/api/v1/forecast/staffing",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const { useGenerateStaffingMutation } = forecastApi;
