import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import KeyboardDoubleArrowRightIcon from "@mui/icons-material/KeyboardDoubleArrowRight";
import KeyboardDoubleArrowLeftIcon from "@mui/icons-material/KeyboardDoubleArrowLeft";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { initCells, setSavedDeploymentId } from "./deploymentSlice";
import { useListCrewQuery } from "../../services/crewApi";
import { useCreateDeploymentMutation } from "../../services/deploymentApi";
import DeploymentGrid from "./DeploymentGrid";
import CrewPool from "./CrewPool";
import ChatPanel from "../chat/ChatPanel";
import { useFlowNavOverride } from "../../components/FlowNavContext";
import FactorBadge from "../suggestion/FactorBadge";

const SIDEBAR_WIDTH = 380;

export default function DeploymentPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const staffing = useAppSelector((s) => s.suggestion.staffing);
  const cells = useAppSelector((s) => s.deployment.cells);
  const { data: crew } = useListCrewQuery(storeId ?? "", { skip: !storeId });
  const [createDeploy, { isLoading: saving }] = useCreateDeploymentMutation();
  const [toast, setToast] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { setOverride, clearOverride } = useFlowNavOverride();

  useEffect(() => {
    if (staffing && cells.length === 0) {
      dispatch(
        initCells(
          staffing.cells.map((c) => ({
            station_id: c.station_id,
            shift: c.shift,
            ai_recommended: c.ai_recommended,
            assigned_employee_ids: [],
          }))
        )
      );
    }
  }, [staffing, cells.length, dispatch]);

  const handleSave = useCallback(async () => {
    if (!storeId || !staffing) return;
    try {
      const result = await createDeploy({
        store_id: storeId,
        date: staffing.date,
        cells,
        source_staffing_model: staffing.model_used,
      }).unwrap();
      dispatch(setSavedDeploymentId(result.deployment_id));
      setToast(true);
      setTimeout(() => navigate("/summary"), 800);
    } catch {
      /* handled by RTK Query error */
    }
  }, [storeId, staffing, cells, createDeploy, dispatch, navigate]);

  useEffect(() => {
    setOverride({
      nextLabel: "Save deployment chart",
      nextVariant: "success",
      nextDisabled: saving,
      onNext: handleSave,
    });
    return () => clearOverride();
  }, [saving, handleSave, setOverride, clearOverride]);

  if (!staffing) {
    return (
      <Box sx={{ py: 8, textAlign: "center" }}>
        <Typography color="text.secondary">No AI suggestion generated yet. Go back to generate one.</Typography>
      </Box>
    );
  }

  const totalRec = cells.reduce((s, c) => s + c.ai_recommended, 0);
  const totalAssigned = cells.reduce((s, c) => s + c.assigned_employee_ids.length, 0);
  const uniqueCrew = new Set(cells.flatMap((c) => c.assigned_employee_ids)).size;
  const gaps = totalRec - totalAssigned;

  return (
    <Box sx={{ display: "flex", gap: 0, height: "calc(100vh - 80px)" }}>
      {/* ─── Main area ─── */}
      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Header bar */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2, flexShrink: 0 }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.3 }}>
              Deployment chart
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
              {staffing.day_of_week} {staffing.date}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1.5, alignItems: "center" }}>
            <StatPill label="Assigned" value={`${totalAssigned}/${totalRec}`} color="primary.main" />
            <StatPill label="Crew" value={uniqueCrew} color="text.primary" />
            {gaps > 0 && <StatPill label="Gaps" value={gaps} color="warning.main" />}
            {!sidebarOpen && (
              <Tooltip title="Open sidebar" arrow>
                <IconButton
                  size="small"
                  onClick={() => setSidebarOpen(true)}
                  sx={(t) => ({
                    width: 36,
                    height: 36,
                    borderRadius: "12px",
                    bgcolor: t.palette.mode === "dark" ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.04)",
                  })}
                >
                  <KeyboardDoubleArrowLeftIcon sx={{ fontSize: 18 }} />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>

        {/* Context factors — compact inline strip */}
        <Box sx={{ display: "flex", gap: 1.5, mb: 2, flexShrink: 0, overflowX: "auto", pb: 0.5 }}>
          {staffing.context.factors.map((f, i) => (
            <FactorBadge key={i} factor={f} />
          ))}
        </Box>

        {/* Deployment grid — scrollable */}
        <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pb: 2 }}>
          <DeploymentGrid cells={cells} staffingCells={staffing.cells} crew={crew ?? []} />
          <Box sx={{ mt: 1.5, display: "flex", gap: 1.5, alignItems: "center", flexWrap: "wrap" }}>
            <LegendItem label="AI recommendation" />
            <Chip label="✓ met" size="small" color="success" variant="outlined" sx={{ fontSize: 10 }} />
            <Chip label="⚠ short" size="small" color="warning" variant="outlined" sx={{ fontSize: 10 }} />
          </Box>
        </Box>
      </Box>

      {/* ─── Sidebar ─── */}
      <Box
        sx={{
          width: sidebarOpen ? SIDEBAR_WIDTH : 0,
          flexShrink: 0,
          overflow: "hidden",
          transition: "width 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          display: { xs: "none", md: "block" },
        }}
      >
        <Box
          sx={{
            width: SIDEBAR_WIDTH,
            height: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 2,
            pl: 2,
          }}
        >
          {/* Sidebar header with collapse */}
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Typography variant="body2" sx={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 0.75 }}>
              <Box component="span" sx={{ color: "primary.main" }}>◆</Box> AI + Crew
            </Typography>
            <Tooltip title="Collapse sidebar" arrow>
              <IconButton size="small" onClick={() => setSidebarOpen(false)} sx={{ width: 28, height: 28 }}>
                <KeyboardDoubleArrowRightIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          </Box>

          {/* Crew pool — compact */}
          <Box sx={{ flexShrink: 0, maxHeight: "35%", overflow: "auto" }}>
            <CrewPool crew={crew ?? []} cells={cells} />
          </Box>

          {/* AI Chat — fills remaining space */}
          <Box sx={{ flex: 1, minHeight: 0 }}>
            <ChatPanel fill />
          </Box>
        </Box>
      </Box>

      <Snackbar open={toast} autoHideDuration={3000} onClose={() => setToast(false)}>
        <Alert severity="success" variant="filled" sx={{ borderRadius: "20px" }}>Deployment chart saved!</Alert>
      </Snackbar>
    </Box>
  );
}

function StatPill({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <Box
      sx={(t) => ({
        display: "flex",
        alignItems: "center",
        gap: 0.75,
        px: 1.5,
        py: 0.5,
        borderRadius: "12px",
        bgcolor: t.palette.mode === "dark" ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
        border: 1,
        borderColor: "divider",
      })}
    >
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500, fontSize: 11 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 700, color, fontSize: 13 }}>
        {value}
      </Typography>
    </Box>
  );
}

function LegendItem({ label }: { label: string }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, fontSize: 12, color: "text.secondary" }}>
      <Box
        sx={(t) => ({
          width: 24,
          height: 16,
          borderRadius: "6px",
          bgcolor: t.palette.mode === "dark" ? "rgba(62,145,255,0.1)" : "#EDF4FF",
          border: `1px solid ${t.palette.mode === "dark" ? "rgba(62,145,255,0.2)" : "#B8D4F8"}`,
        })}
      />
      {label}
    </Box>
  );
}
