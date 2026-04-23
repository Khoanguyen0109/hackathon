import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import StorefrontIcon from "@mui/icons-material/Storefront";
import GroupsIcon from "@mui/icons-material/Groups";
import { useFlowNavOverride } from "./FlowNavContext";
import { useColorMode } from "../app/ColorModeContext";

const MAIN_STEPS = [
  { label: "AI suggestion", path: "/" },
  { label: "Deployment chart", path: "/deploy" },
  { label: "Saved charts", path: "/history" },
] as const;

const MORE_ITEMS = [
  { label: "Store profile", path: "/store-profile", icon: <StorefrontIcon fontSize="small" /> },
  { label: "Crew setup", path: "/crew", icon: <GroupsIcon fontSize="small" /> },
] as const;

const MORE_PATHS = new Set(MORE_ITEMS.map((i) => i.path));

interface StepNav {
  backPath?: string;
  backLabel?: string;
  nextPath?: string;
  nextLabel?: string;
  nextVariant?: "primary" | "success";
}

const STEP_NAV: Record<string, StepNav> = {
  "/": { nextPath: "/deploy", nextLabel: "Next: Assign crew" },
  "/deploy": { backPath: "/", nextPath: "/history", nextLabel: "Save deployment chart", nextVariant: "success" },
  "/history": { backPath: "/deploy" },
  "/store-profile": { nextPath: "/crew", nextLabel: "Next: Crew setup" },
  "/crew": { backPath: "/store-profile", nextPath: "/", nextLabel: "Next: AI suggestion" },
};

function mainTabIndex(pathname: string): number | false {
  const idx = MAIN_STEPS.findIndex(
    (s) => pathname === s.path || (s.path !== "/" && pathname.startsWith(s.path + "/"))
  );
  return idx >= 0 ? idx : false;
}

export default function StepperNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const current = mainTabIndex(location.pathname);
  const nav = STEP_NAV[location.pathname] ?? {};
  const { override } = useFlowNavOverride();
  const { mode, toggleColorMode } = useColorMode();

  const [moreAnchor, setMoreAnchor] = useState<null | HTMLElement>(null);
  const moreOpen = Boolean(moreAnchor);
  const isOnMorePage = MORE_PATHS.has(location.pathname as typeof MORE_ITEMS[number]["path"]);

  const nextLabel = override.nextLabel ?? nav.nextLabel;
  const nextVariant = override.nextVariant ?? nav.nextVariant ?? "primary";
  const nextDisabled = override.nextDisabled ?? false;

  const handleNext = () => {
    if (override.onNext) {
      override.onNext();
      return;
    }
    if (nav.nextPath) navigate(nav.nextPath);
  };

  const isLight = mode === "light";

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: isLight
          ? "rgba(255, 255, 255, 0.72)"
          : "rgba(31, 31, 31, 0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Toolbar sx={{ gap: 0, px: { xs: 1, sm: 2.5 }, minHeight: 56 }}>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 700,
            color: "text.primary",
            pr: 2,
            mr: 0.5,
            borderRight: 1,
            borderColor: "divider",
            whiteSpace: "nowrap",
            letterSpacing: "0.3px",
            fontSize: 14,
          }}
        >
          Byte<Box component="span" sx={{ color: "primary.main" }}>Coach</Box>{" "}
          Manager
        </Typography>

        <Tabs
          value={current}
          onChange={(_, v) => navigate(MAIN_STEPS[v].path)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            flex: 1,
            minHeight: 56,
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 500,
              fontSize: 13,
              minHeight: 56,
              px: 1.75,
              color: "text.secondary",
              letterSpacing: "0.2px",
              transition: "color 0.2s ease",
            },
            "& .Mui-selected": {
              color: "primary.main",
              fontWeight: 600,
            },
            "& .MuiTabs-indicator": {
              backgroundColor: "primary.main",
              borderRadius: "2px 2px 0 0",
              height: 3,
            },
          }}
        >
          {MAIN_STEPS.map((s) => (
            <Tab key={s.path} label={s.label} />
          ))}
        </Tabs>

        <Box sx={{ display: "flex", gap: 0.75, alignItems: "center", ml: 1 }}>
          <Tooltip title="More options" arrow>
            <IconButton
              onClick={(e) => setMoreAnchor(e.currentTarget)}
              size="small"
              sx={(t) => ({
                width: 36,
                height: 36,
                borderRadius: "12px",
                bgcolor: isOnMorePage
                  ? "primary.main"
                  : t.palette.mode === "dark"
                    ? "rgba(255, 255, 255, 0.08)"
                    : "rgba(0, 0, 0, 0.04)",
                color: isOnMorePage
                  ? "primary.contrastText"
                  : "text.primary",
                transition: "all 0.3s ease",
                "&:hover": {
                  bgcolor: isOnMorePage
                    ? "primary.dark"
                    : t.palette.mode === "dark"
                      ? "rgba(255, 255, 255, 0.14)"
                      : "rgba(0, 0, 0, 0.08)",
                },
              })}
            >
              <MoreHorizIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
          <Menu
            anchorEl={moreAnchor}
            open={moreOpen}
            onClose={() => setMoreAnchor(null)}
            transformOrigin={{ horizontal: "right", vertical: "top" }}
            anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
            slotProps={{
              paper: {
                sx: {
                  mt: 0.5,
                  minWidth: 180,
                  borderRadius: 2,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
                },
              },
            }}
          >
            {MORE_ITEMS.map((item) => (
              <MenuItem
                key={item.path}
                selected={location.pathname === item.path}
                onClick={() => {
                  navigate(item.path);
                  setMoreAnchor(null);
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText>{item.label}</ListItemText>
              </MenuItem>
            ))}
          </Menu>

          <Tooltip title={isLight ? "Switch to dark mode" : "Switch to light mode"} arrow>
            <IconButton
              onClick={toggleColorMode}
              size="small"
              sx={(t) => ({
                width: 36,
                height: 36,
                borderRadius: "12px",
                bgcolor: t.palette.mode === "dark"
                  ? "rgba(255, 255, 255, 0.08)"
                  : "rgba(0, 0, 0, 0.04)",
                color: "text.primary",
                transition: "all 0.3s ease",
                "&:hover": {
                  bgcolor: t.palette.mode === "dark"
                    ? "rgba(255, 255, 255, 0.14)"
                    : "rgba(0, 0, 0, 0.08)",
                  transform: "rotate(30deg)",
                },
              })}
            >
              {isLight
                ? <DarkModeIcon sx={{ fontSize: 18 }} />
                : <LightModeIcon sx={{ fontSize: 18 }} />
              }
            </IconButton>
          </Tooltip>

          {nav.backPath && (
            <Button
              size="small"
              variant="outlined"
              onClick={() => navigate(nav.backPath!)}
              sx={{
                whiteSpace: "nowrap",
                borderColor: "divider",
                color: "text.secondary",
                "&:hover": {
                  borderColor: "primary.main",
                  color: "primary.main",
                  bgcolor: "primary.light",
                },
              }}
            >
              {nav.backLabel ?? "Back"}
            </Button>
          )}
          {nav.nextPath && (
            <Button
              size="small"
              variant="contained"
              color={nextVariant === "success" ? "success" : "primary"}
              disabled={nextDisabled}
              onClick={handleNext}
              sx={{ whiteSpace: "nowrap" }}
            >
              {nextLabel}
            </Button>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
