import { useEffect, useCallback } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import Skeleton from "@mui/material/Skeleton";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { setStaffing, setGenerating, toggleChat } from "./suggestionSlice";
import { useGenerateStaffingMutation, useAssignCrewMutation } from "../../services/forecastApi";
import { initCells } from "../deployment/deploymentSlice";
import { useNavigate } from "react-router-dom";
import DateContextBar from "./DateContextBar";
import StaffingGrid from "./StaffingGrid";
import AiSummaryBanner from "./AiSummaryBanner";
import ChatPanel from "../chat/ChatPanel";
import { useFlowNavOverride } from "../../components/FlowNavContext";

export default function SuggestionPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const { targetDate, staffing, generating, chatOpen } = useAppSelector((s) => s.suggestion);
  const [generate, { error }] = useGenerateStaffingMutation();
  const [assignCrew, { isLoading: assigning }] = useAssignCrewMutation();
  const { setOverride, clearOverride } = useFlowNavOverride();

  const handleAssignCrew = useCallback(async () => {
    if (!storeId || !targetDate || !staffing) return;
    try {
      const result = await assignCrew({
        store_id: storeId,
        date: targetDate,
        staffing_cells: staffing.cells,
      }).unwrap();
      dispatch(initCells(result.cells));
    } catch {
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
    navigate("/deploy");
  }, [storeId, targetDate, staffing, assignCrew, dispatch, navigate]);

  useEffect(() => {
    if (assigning) {
      setOverride({ nextLabel: "Assigning crew...", nextDisabled: true });
    } else if (staffing) {
      setOverride({ onNext: handleAssignCrew, nextLabel: "Next: Assign crew", nextDisabled: false });
    } else {
      setOverride({ nextDisabled: true });
    }
    return () => clearOverride();
  }, [staffing, assigning, handleAssignCrew, setOverride, clearOverride]);

  const handleGenerate = async () => {
    if (!storeId || !targetDate) return;
    dispatch(setGenerating(true));
    try {
      const result = await generate({ store_id: storeId, date: targetDate, demo_mode: true }).unwrap();
      dispatch(setStaffing(result));
    } catch {
      dispatch(setGenerating(false));
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ textAlign: "left" }}>AI staffing suggestion</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Select a target date. The system fetches external context, then the AI suggests headcounts per station per shift.
        </Typography>
      </Box>

      <DateContextBar />

      {!staffing && !generating && (
        <Box>
          <Alert
            severity="info"
            icon={<Box component="span" sx={{ color: "primary.main", fontSize: 14, fontWeight: 700 }}>◆</Box>}
            sx={{ mb: 2.5 }}
          >
            AI will factor in external events, weather, holidays, and promotions to generate optimal staffing recommendations.
          </Alert>
          <Box sx={{ textAlign: "center", py: 4 }}>
            <Button
              variant="contained"
              color="primary"
              size="large"
              onClick={handleGenerate}
              disabled={!storeId || !targetDate}
              startIcon={<Box component="span">◆</Box>}
              sx={{ px: 5 }}
            >
              Generate staffing suggestion
            </Button>
          </Box>
        </Box>
      )}

      {generating && (
        <Box sx={{ textAlign: "center", py: 5 }}>
          <Box sx={{ display: "flex", justifyContent: "center", gap: 1, mb: 2 }}>
            {[0, 1, 2].map((i) => (
              <Box
                key={i}
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  bgcolor: "primary.main",
                  animation: "oneui-pulse 1.2s ease-in-out infinite",
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </Box>
          <Typography variant="body2" color="text.secondary">
            Analysing store context + external factors...
          </Typography>
          <Box sx={{ mt: 3 }}>
            <Skeleton variant="rounded" height={300} sx={{ maxWidth: 700, mx: "auto", borderRadius: "20px" }} />
          </Box>
        </Box>
      )}

      {assigning && (
        <Box sx={{ textAlign: "center", py: 5 }}>
          <Box sx={{ display: "flex", justifyContent: "center", gap: 1, mb: 2 }}>
            {[0, 1, 2].map((i) => (
              <Box
                key={i}
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  bgcolor: "success.main",
                  animation: "oneui-pulse 1.2s ease-in-out infinite",
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </Box>
          <Typography variant="body2" color="text.secondary">
            AI is assigning crew to stations...
          </Typography>
          <Box sx={{ mt: 3 }}>
            <Skeleton variant="rounded" height={300} sx={{ maxWidth: 700, mx: "auto", borderRadius: "20px" }} />
          </Box>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to generate suggestion. Is the API server running on localhost:8000?
        </Alert>
      )}

      {staffing && (
        <>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
            <Alert
              severity="success"
              sx={{ flex: 1, mr: 1, py: 0.5 }}
              icon={<Box component="span" sx={{ color: "success.main" }}>✓</Box>}
            >
              Suggestion generated in {(staffing.generation_ms / 1000).toFixed(1)}s · Model: {staffing.model_used} ·{" "}
              <strong>Click any cell for reasoning</strong>
            </Alert>
            <Button
              variant={chatOpen ? "contained" : "outlined"}
              color="primary"
              size="small"
              onClick={() => dispatch(toggleChat())}
              startIcon={<Box component="span" sx={{ fontWeight: 700 }}>◆</Box>}
            >
              Chat with AI
            </Button>
          </Box>

          <Box sx={{ display: "flex", gap: 0 }}>
            <Box sx={{ flex: 1, minWidth: 0, transition: "all 0.3s" }}>
              <StaffingGrid cells={staffing.cells} />
              <AiSummaryBanner staffing={staffing} />
            </Box>
            {chatOpen && (
              <Box sx={{ width: 360, flexShrink: 0, ml: 2, transition: "all 0.3s" }}>
                <ChatPanel />
              </Box>
            )}
          </Box>
        </>
      )}
    </Box>
  );
}
