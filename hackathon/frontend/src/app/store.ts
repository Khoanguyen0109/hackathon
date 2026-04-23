import { configureStore } from "@reduxjs/toolkit";
import { api } from "../services/api";
import storeProfileReducer from "../features/store-profile/storeProfileSlice";
import crewReducer from "../features/crew/crewSlice";
import suggestionReducer from "../features/suggestion/suggestionSlice";
import chatReducer from "../features/chat/chatSlice";
import deploymentReducer from "../features/deployment/deploymentSlice";

export const store = configureStore({
  reducer: {
    [api.reducerPath]: api.reducer,
    storeProfile: storeProfileReducer,
    crew: crewReducer,
    suggestion: suggestionReducer,
    chat: chatReducer,
    deployment: deploymentReducer,
  },
  middleware: (getDefault) => getDefault().concat(api.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
