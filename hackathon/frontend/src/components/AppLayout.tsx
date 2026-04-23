import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import Box from "@mui/material/Box";
import StepperNav from "./StepperNav";
import { FlowNavProvider } from "./FlowNavContext";
import { useListStoresQuery } from "../services/storeApi";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { selectStore } from "../features/store-profile/storeProfileSlice";

export default function AppLayout() {
  const dispatch = useAppDispatch();
  const selectedStoreId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const { data: stores } = useListStoresQuery();

  useEffect(() => {
    if (!selectedStoreId && stores?.length) {
      dispatch(selectStore(stores[0].store_id));
    }
  }, [stores, selectedStoreId, dispatch]);

  return (
    <FlowNavProvider>
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          bgcolor: "background.default",
          transition: "background-color 0.3s ease",
        }}
      >
        <StepperNav />
        <Box
          component="main"
          sx={{
            flex: 1,
            maxWidth: 1080,
            width: "100%",
            mx: "auto",
            px: { xs: 2, sm: 3 },
            py: 3,
            animation: "oneui-fade-in 0.4s ease-out",
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </FlowNavProvider>
  );
}
