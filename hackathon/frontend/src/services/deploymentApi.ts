import { api } from "./api";
import type {
  Deployment,
  DeploymentCreate,
  DeploymentSummary,
  DeploymentComparison,
  AssignedCell,
} from "./types";

export const deploymentApi = api.injectEndpoints({
  endpoints: (build) => ({
    createDeployment: build.mutation<Deployment, DeploymentCreate>({
      query: (body) => ({
        url: "/api/v1/deployments",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Deployment"],
    }),
    listDeployments: build.query<Deployment[], { storeId?: string }>({
      query: ({ storeId }) =>
        storeId
          ? `/api/v1/deployments?store_id=${storeId}`
          : "/api/v1/deployments",
      providesTags: ["Deployment"],
    }),
    getDeployment: build.query<Deployment, string>({
      query: (id) => `/api/v1/deployments/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Deployment", id }],
    }),
    getDeploymentSummary: build.query<DeploymentSummary, string>({
      query: (id) => `/api/v1/deployments/${id}/summary`,
    }),
    getDeploymentComparison: build.query<DeploymentComparison, string>({
      query: (id) => `/api/v1/deployments/${id}/comparison`,
    }),
    updateDeployment: build.mutation<Deployment, { id: string; cells: AssignedCell[] }>({
      query: ({ id, cells }) => ({
        url: `/api/v1/deployments/${id}`,
        method: "PATCH",
        body: { cells },
      }),
      invalidatesTags: (_r, _e, { id }) => [{ type: "Deployment", id }],
    }),
    deleteDeployment: build.mutation<void, string>({
      query: (id) => ({
        url: `/api/v1/deployments/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Deployment"],
    }),
  }),
});

export const {
  useCreateDeploymentMutation,
  useListDeploymentsQuery,
  useGetDeploymentQuery,
  useGetDeploymentSummaryQuery,
  useGetDeploymentComparisonQuery,
  useUpdateDeploymentMutation,
  useDeleteDeploymentMutation,
} = deploymentApi;
