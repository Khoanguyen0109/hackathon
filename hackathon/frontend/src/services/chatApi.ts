import { api } from "./api";
import type { ChatRequest, ChatResponse } from "./types";

export const chatApi = api.injectEndpoints({
  endpoints: (build) => ({
    sendChatMessage: build.mutation<ChatResponse, ChatRequest>({
      query: (body) => ({
        url: "/api/v1/chat",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const { useSendChatMessageMutation } = chatApi;
