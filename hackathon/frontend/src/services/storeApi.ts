import { api } from "./api";
import type { Store, Station, Task } from "./types";

export const storeApi = api.injectEndpoints({
  endpoints: (build) => ({
    listStores: build.query<Store[], void>({
      query: () => "/api/v1/stores",
      providesTags: ["Store"],
    }),
    getStore: build.query<Store, string>({
      query: (id) => `/api/v1/stores/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Store", id }],
    }),
    listStations: build.query<Station[], void>({
      query: () => "/api/v1/stations",
      providesTags: ["Station"],
    }),
    listTasks: build.query<Task[], void>({
      query: () => "/api/v1/tasks",
      providesTags: ["Task"],
    }),
  }),
});

export const {
  useListStoresQuery,
  useGetStoreQuery,
  useListStationsQuery,
  useListTasksQuery,
} = storeApi;
