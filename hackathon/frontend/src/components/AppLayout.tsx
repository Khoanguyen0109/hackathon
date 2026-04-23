import { Outlet } from "react-router-dom";
import Box from "@mui/material/Box";
import StepperNav from "./StepperNav";
import { FlowNavProvider } from "./FlowNavContext";

export default function AppLayout() {
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
