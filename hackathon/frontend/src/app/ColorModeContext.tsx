import { createContext, useContext, useState, useMemo, useCallback, type ReactNode } from "react";
import useMediaQuery from "@mui/material/useMediaQuery";
import type { PaletteMode } from "@mui/material/styles";

interface ColorModeContextValue {
  mode: PaletteMode;
  toggleColorMode: () => void;
}

const ColorModeContext = createContext<ColorModeContextValue>({
  mode: "light",
  toggleColorMode: () => {},
});

export function useColorMode() {
  return useContext(ColorModeContext);
}

export function ColorModeProvider({ children }: { children: ReactNode }) {
  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");
  const [manualMode, setManualMode] = useState<PaletteMode | null>(null);

  const mode: PaletteMode = manualMode ?? (prefersDark ? "dark" : "light");

  const toggleColorMode = useCallback(() => {
    setManualMode((prev) => {
      const current = prev ?? (prefersDark ? "dark" : "light");
      return current === "light" ? "dark" : "light";
    });
  }, [prefersDark]);

  const value = useMemo(() => ({ mode, toggleColorMode }), [mode, toggleColorMode]);

  return (
    <ColorModeContext.Provider value={value}>
      {children}
    </ColorModeContext.Provider>
  );
}
