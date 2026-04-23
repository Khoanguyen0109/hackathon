import { api } from "./api";
import type { ContextResponse } from "./types";

export const contextApi = api.injectEndpoints({
  endpoints: (build) => ({
    getContext: build.query<ContextResponse, { storeId: string; date: string }>({
      query: ({ storeId, date }) => `/api/v1/context?store_id=${storeId}&date=${date}`,
      providesTags: ["Context"],
    }),
  }),
});

export const { useGetContextQuery, useLazyGetContextQuery } = contextApi;
