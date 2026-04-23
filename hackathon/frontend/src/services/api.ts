import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export const api = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({ baseUrl: "/" }),
  tagTypes: ["Store", "Station", "Task", "Crew", "Context", "Deployment"],
  endpoints: () => ({}),
});
