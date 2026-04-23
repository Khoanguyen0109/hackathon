import { createTheme, type PaletteMode } from "@mui/material/styles";

const oneUiShape = {
  borderRadius: 28,
};

const getDesignTokens = (mode: PaletteMode) => ({
  palette: {
    mode,
    ...(mode === "light"
      ? {
          primary: { main: "#007AFF", light: "#E8F2FF", dark: "#0062CC" },
          secondary: { main: "#5856D6", light: "#F0EFFF", dark: "#3634A3" },
          success: { main: "#34C759", light: "#EEFBF1" },
          warning: { main: "#FF9500", light: "#FFF8EB" },
          error: { main: "#FF3B30", light: "#FFF0EF" },
          background: {
            default: "#F2F2F7",
            paper: "rgba(255, 255, 255, 0.95)",
          },
          text: {
            primary: "#1D1D1D",
            secondary: "#8E8E93",
            disabled: "#AEAEB2",
          },
          divider: "rgba(60, 60, 67, 0.12)",
        }
      : {
          primary: { main: "#3E91FF", light: "#1A2A40", dark: "#5BABFF" },
          secondary: { main: "#7D7AFF", light: "#1E1D3A", dark: "#9B99FF" },
          success: { main: "#30D158", light: "#0D2614" },
          warning: { main: "#FFD60A", light: "#2A2204" },
          error: { main: "#FF453A", light: "#2E0E0C" },
          background: {
            default: "#000000",
            paper: "rgba(31, 31, 31, 0.85)",
          },
          text: {
            primary: "#FFFFFF",
            secondary: "#8E8E93",
            disabled: "#636366",
          },
          divider: "rgba(84, 84, 88, 0.36)",
        }),
  },
});

export function buildTheme(mode: PaletteMode) {
  const tokens = getDesignTokens(mode);
  const isLight = mode === "light";

  return createTheme({
    ...tokens,
    typography: {
      fontFamily:
        "'Inter', -apple-system, 'SF Pro Display', 'Helvetica Neue', sans-serif",
      h5: {
        fontWeight: 700,
        fontSize: "1.25rem",
        letterSpacing: "0.5px",
        textAlign: "center" as const,
      },
      h6: {
        fontWeight: 700,
        fontSize: "1.125rem",
        letterSpacing: "0.3px",
      },
      subtitle1: {
        fontWeight: 600,
        fontSize: "0.9375rem",
        letterSpacing: "0.15px",
      },
      subtitle2: {
        fontSize: "0.6875rem",
        fontWeight: 600,
        textTransform: "uppercase" as const,
        letterSpacing: "0.08em",
        color: tokens.palette.text.secondary,
      },
      body1: {
        fontWeight: 500,
        fontSize: "0.9375rem",
        lineHeight: 1.5,
      },
      body2: {
        fontWeight: 500,
        fontSize: "0.8125rem",
        lineHeight: "20px",
      },
      caption: { fontSize: "0.6875rem", fontWeight: 500 },
    },
    shape: oneUiShape,
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            transition: "background-color 0.3s ease, color 0.3s ease",
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: {
            textTransform: "none" as const,
            fontWeight: 600,
            borderRadius: 24,
            letterSpacing: "0.2px",
          },
          sizeMedium: { padding: "10px 24px", fontSize: "0.8125rem" },
          sizeSmall: { padding: "6px 16px", fontSize: "0.75rem" },
          sizeLarge: { padding: "12px 32px", fontSize: "0.9375rem" },
          contained: {
            "&.MuiButton-colorPrimary": {
              background: isLight
                ? "linear-gradient(135deg, #007AFF 0%, #0062CC 100%)"
                : "linear-gradient(135deg, #3E91FF 0%, #5BABFF 100%)",
              "&:hover": {
                background: isLight
                  ? "linear-gradient(135deg, #0062CC 0%, #004C99 100%)"
                  : "linear-gradient(135deg, #5BABFF 0%, #7DC3FF 100%)",
              },
            },
          },
        },
      },
      MuiCard: {
        defaultProps: { variant: "elevation", elevation: 0 },
        styleOverrides: {
          root: {
            borderRadius: 28,
            padding: "24px",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            background: isLight
              ? "rgba(255, 255, 255, 0.95)"
              : "rgba(31, 31, 31, 0.85)",
            boxShadow: isLight
              ? "0 2px 12px rgba(0, 0, 0, 0.06), 0 1px 4px rgba(0, 0, 0, 0.04)"
              : "0 2px 12px rgba(0, 0, 0, 0.3), 0 1px 4px rgba(0, 0, 0, 0.2)",
            border: isLight
              ? "1px solid rgba(0, 0, 0, 0.04)"
              : "1px solid rgba(255, 255, 255, 0.06)",
            transition: "box-shadow 0.2s ease, transform 0.15s ease",
          },
        },
      },
      MuiCardContent: {
        styleOverrides: {
          root: {
            padding: 0,
            "&:last-child": { paddingBottom: 0 },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            fontWeight: 600,
            borderRadius: 20,
          },
          sizeSmall: { fontSize: "0.625rem", height: 24 },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            borderRadius: 28,
            backdropFilter: "blur(20px)",
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-root": {
              borderRadius: 16,
              "& fieldset": {
                borderColor: isLight
                  ? "rgba(60, 60, 67, 0.12)"
                  : "rgba(84, 84, 88, 0.36)",
              },
            },
          },
        },
      },
      MuiSelect: {
        styleOverrides: {
          root: { borderRadius: 16 },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: { borderRadius: 20 },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: "none" as const,
            fontWeight: 500,
            fontSize: 13,
            letterSpacing: "0.2px",
          },
        },
      },
      MuiTableContainer: {
        styleOverrides: {
          root: { borderRadius: 20, overflow: "hidden" },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: { borderRadius: 12 },
        },
      },
      MuiSkeleton: {
        styleOverrides: {
          root: { borderRadius: 20 },
        },
      },
    },
  });
}

const theme = buildTheme("light");
export default theme;
