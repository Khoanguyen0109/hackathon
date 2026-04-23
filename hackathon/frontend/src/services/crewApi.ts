import { api } from "./api";
import type { Employee, EmployeeCreate, EmployeePatch } from "./types";

export const crewApi = api.injectEndpoints({
  endpoints: (build) => ({
    listCrew: build.query<Employee[], string>({
      query: (storeId) => `/api/v1/stores/${storeId}/crew`,
      providesTags: (_r, _e, storeId) => [{ type: "Crew", id: storeId }],
    }),
    addCrewMember: build.mutation<Employee, { storeId: string; body: EmployeeCreate }>({
      query: ({ storeId, body }) => ({
        url: `/api/v1/stores/${storeId}/crew`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_r, _e, { storeId }) => [{ type: "Crew", id: storeId }],
    }),
    updateCrewMember: build.mutation<Employee, { employeeId: string; storeId: string; body: EmployeePatch }>({
      query: ({ employeeId, body }) => ({
        url: `/api/v1/crew/${employeeId}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: (_r, _e, { storeId }) => [{ type: "Crew", id: storeId }],
    }),
    deleteCrewMember: build.mutation<void, { employeeId: string; storeId: string }>({
      query: ({ employeeId }) => ({
        url: `/api/v1/crew/${employeeId}`,
        method: "DELETE",
      }),
      invalidatesTags: (_r, _e, { storeId }) => [{ type: "Crew", id: storeId }],
    }),
  }),
});

export const {
  useListCrewQuery,
  useAddCrewMemberMutation,
  useUpdateCrewMemberMutation,
  useDeleteCrewMemberMutation,
} = crewApi;
