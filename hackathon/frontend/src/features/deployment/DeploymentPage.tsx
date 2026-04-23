import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { initCells, setSavedDeploymentId } from "./deploymentSlice";
import { useListCrewQuery } from "../../services/crewApi";
import { useCreateDeploymentMutation } from "../../services/deploymentApi";
import Button from "@mui/material/Button";
import DeploymentGrid from "./DeploymentGrid";
import CrewPool from "./CrewPool";
import ChatPanel from "../chat/ChatPanel";
import { useFlowNavOverride } from "../../components/FlowNavContext";
import FactorBadge from "../suggestion/FactorBadge";

export default function DeploymentPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const staffing = useAppSelector((s) => s.suggestion.staffing);
  const cells = useAppSelector((s) => s.deployment.cells);
  const { data: crew } = useListCrewQuery(storeId ?? "", { skip: !storeId });
  const [createDeploy, { isLoading: saving }] = useCreateDeploymentMutation();
  const [toast, setToast] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
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

  return (
    <Box>
      <Box sx={{ mb: 3, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Box>
          <Typography variant="h6" sx={{ textAlign: "left" }}>Deployment chart — assign crew</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            AI suggestions are shown in blue. Click <strong>+ assign</strong> to add crew members to each slot.
          </Typography>
        </Box>
        <Button
          variant={chatOpen ? "contained" : "outlined"}
          color="primary"
          size="small"
          onClick={() => setChatOpen((v) => !v)}
          startIcon={<Box component="span" sx={{ fontWeight: 700 }}>◆</Box>}
        >
          AI Assistant
        </Button>
      </Box>

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
            <Typography sx={{ fontSize: 14 }}>📅</Typography>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {staffing.day_of_week} {staffing.date}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
            {staffing.context.factors.map((f, i) => (
              <FactorBadge key={i} factor={f} />
            ))}
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ display: "flex", gap: 2, flexWrap: { xs: "wrap", md: "nowrap" } }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <DeploymentGrid cells={cells} staffingCells={staffing.cells} crew={crew ?? []} />
        </Box>
        <Box sx={{ width: { xs: "100%", md: 240 }, flexShrink: 0 }}>
          <CrewPool crew={crew ?? []} cells={cells} />
        </Box>
        {chatOpen && (
          <Box sx={{ width: { xs: "100%", md: 360 }, flexShrink: 0, transition: "all 0.3s" }}>
            <ChatPanel />
          </Box>
        )}
      </Box>

      <Box sx={{ mt: 2, display: "flex", gap: 1.5, alignItems: "center", flexWrap: "wrap" }}>
        <LegendItem label="AI recommendation" />
        <Chip label="✓ met" size="small" color="success" variant="outlined" sx={{ fontSize: 10 }} />
        <Chip label="⚠ short" size="small" color="warning" variant="outlined" sx={{ fontSize: 10 }} />
      </Box>

      <Snackbar open={toast} autoHideDuration={3000} onClose={() => setToast(false)}>
        <Alert severity="success" variant="filled" sx={{ borderRadius: "20px" }}>Deployment chart saved!</Alert>
      </Snackbar>
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
