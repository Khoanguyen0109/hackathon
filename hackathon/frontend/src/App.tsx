import { useMemo } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { buildTheme } from "./app/theme";
import { store } from "./app/store";
import { ColorModeProvider, useColorMode } from "./app/ColorModeContext";
import AppLayout from "./components/AppLayout";
import StoreProfilePage from "./features/store-profile/StoreProfilePage";
import CrewPage from "./features/crew/CrewPage";
import SuggestionPage from "./features/suggestion/SuggestionPage";
import DeploymentPage from "./features/deployment/DeploymentPage";
import SummaryPage from "./features/summary/SummaryPage";
import HistoryPage from "./features/history/HistoryPage";

function ThemedApp() {
  const { mode } = useColorMode();
  const theme = useMemo(() => buildTheme(mode), [mode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<StoreProfilePage />} />
            <Route path="/crew" element={<CrewPage />} />
            <Route path="/suggestion" element={<SuggestionPage />} />
            <Route path="/deploy" element={<DeploymentPage />} />
            <Route path="/summary" element={<SummaryPage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <ColorModeProvider>
        <ThemedApp />
      </ColorModeProvider>
    </Provider>
  );
}
