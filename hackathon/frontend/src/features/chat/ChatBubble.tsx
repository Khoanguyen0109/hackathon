import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import CheckIcon from "@mui/icons-material/Check";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import PersonRemoveIcon from "@mui/icons-material/PersonRemove";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import type { ChatMessage, ChatAction } from "../../services/types";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { assignEmployee, unassignEmployee } from "../deployment/deploymentSlice";
import { markActionApplied } from "./chatSlice";

function ActionCard({
  action,
  messageId,
  actionIndex,
}: {
  action: ChatAction & { applied?: boolean };
  messageId: string;
  actionIndex: number;
}) {
  const dispatch = useAppDispatch();
  const cells = useAppSelector((s) => s.deployment.cells);
  const [status, setStatus] = useState<"pending" | "applied" | "skipped">(
    action.applied ? "applied" : "pending"
  );
  const [toast, setToast] = useState(false);

  const employeeLabel = action.employee_name || action.employee_id;
  const stationLabel = action.station_name || action.station_id;

  const handleApply = () => {
    if (action.type === "assign") {
      dispatch(
        assignEmployee({
          stationId: action.station_id,
          shift: action.shift,
          employeeId: action.employee_id,
        })
      );
    } else if (action.type === "unassign") {
      dispatch(
        unassignEmployee({
          stationId: action.station_id,
          shift: action.shift,
          employeeId: action.employee_id,
        })
      );
    } else if (action.type === "swap") {
      const cell = cells.find(
        (c) => c.station_id === action.station_id && c.shift === action.shift
      );
      if (cell && cell.assigned_employee_ids.length >= cell.ai_recommended && cell.assigned_employee_ids.length > 0) {
        dispatch(
          unassignEmployee({
            stationId: action.station_id,
            shift: action.shift,
            employeeId: cell.assigned_employee_ids[0],
          })
        );
      }
      dispatch(
        assignEmployee({
          stationId: action.station_id,
          shift: action.shift,
          employeeId: action.employee_id,
        })
      );
    }
    dispatch(markActionApplied({ messageId, actionIndex }));
    setStatus("applied");
    setToast(true);
  };

  const handleSkip = () => {
    setStatus("skipped");
  };

  const icon =
    action.type === "unassign" ? (
      <PersonRemoveIcon sx={{ fontSize: 14 }} />
    ) : action.type === "swap" ? (
      <SwapHorizIcon sx={{ fontSize: 14 }} />
    ) : (
      <PersonAddIcon sx={{ fontSize: 14 }} />
    );

  const typeLabel = action.type === "swap" ? "swap" : action.type;
  const typeColor: "primary" | "warning" | "info" = action.type === "unassign" ? "warning" : action.type === "swap" ? "info" : "primary";

  const toastMessage =
    action.type === "unassign"
      ? `Unassigned ${employeeLabel} from ${stationLabel}`
      : action.type === "swap"
        ? `Swapped ${employeeLabel} into ${stationLabel}`
        : `Assigned ${employeeLabel} to ${stationLabel}`;

  if (status === "skipped") {
    return (
      <Box
        sx={(t) => ({
          mt: 0.75,
          p: 1.25,
          borderRadius: "14px",
          bgcolor: t.palette.mode === "dark" ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)",
          border: 1,
          borderColor: "divider",
          opacity: 0.5,
        })}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
          <Typography sx={{ fontSize: 11, color: "text.secondary", fontStyle: "italic" }}>
            Skipped: {employeeLabel} → {stationLabel}
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <>
      <Box
        sx={(t) => ({
          mt: 0.75,
          p: 1.25,
          borderRadius: "14px",
          bgcolor:
            status === "applied"
              ? t.palette.mode === "dark"
                ? "rgba(48,209,88,0.08)"
                : "success.light"
              : t.palette.mode === "dark"
                ? "rgba(255,255,255,0.04)"
                : "background.paper",
          border: 1,
          borderColor: status === "applied" ? "success.main" : "divider",
          transition: "all 0.2s",
        })}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
          <Chip
            label={typeLabel}
            size="small"
            color={typeColor}
            sx={{ fontSize: 9, height: 20, borderRadius: "10px" }}
          />
          <Typography sx={{ fontSize: 11, fontWeight: 600, flex: 1 }}>
            {employeeLabel} → {stationLabel} ({action.shift})
          </Typography>
        </Box>
        <Typography sx={{ fontSize: 10, color: "text.secondary", mb: 0.75 }}>
          {action.reason}
        </Typography>
        <Box sx={{ display: "flex", gap: 0.75 }}>
          <Button
            size="small"
            variant={status === "applied" ? "outlined" : "contained"}
            color={status === "applied" ? "success" : "primary"}
            disabled={status === "applied"}
            onClick={handleApply}
            startIcon={status === "applied" ? <CheckIcon sx={{ fontSize: 12 }} /> : icon}
            sx={{ fontSize: 10, py: 0.25, px: 1.5, minHeight: 24 }}
          >
            {status === "applied" ? "Applied" : "Apply"}
          </Button>
          {status === "pending" && (
            <Button
              size="small"
              variant="outlined"
              color="inherit"
              onClick={handleSkip}
              sx={{ fontSize: 10, py: 0.25, px: 1.5, minHeight: 24, color: "text.secondary" }}
            >
              Skip
            </Button>
          )}
        </Box>
      </Box>
      <Snackbar open={toast} autoHideDuration={2500} onClose={() => setToast(false)}>
        <Alert severity="success" variant="filled" sx={{ borderRadius: "20px", fontSize: 12 }}>
          {toastMessage}
        </Alert>
      </Snackbar>
    </>
  );
}

export default function ChatBubble({ message }: { message: ChatMessage }) {
  const actions = message.actions ?? [];

  return (
    <Box
      sx={(t) => {
        const isDark = t.palette.mode === "dark";
        const base = {
          maxWidth: "92%",
          px: 1.75,
          py: 1.25,
          borderRadius: "20px",
          fontSize: 12,
          lineHeight: 1.6,
          animation: "oneui-fade-in 0.2s ease",
        };

        if (message.role === "user") {
          return {
            ...base,
            alignSelf: "flex-end",
            background: isDark
              ? "linear-gradient(135deg, #3E91FF 0%, #5BABFF 100%)"
              : "linear-gradient(135deg, #007AFF 0%, #0062CC 100%)",
            color: "white",
            borderBottomRightRadius: 6,
          };
        }
        if (message.role === "ai") {
          return {
            ...base,
            alignSelf: "flex-start",
            bgcolor: isDark ? "rgba(62,145,255,0.08)" : "#EDF4FF",
            border: `1px solid ${isDark ? "rgba(62,145,255,0.15)" : "#B8D4F8"}`,
            color: "text.primary",
            borderBottomLeftRadius: 6,
          };
        }
        return {
          ...base,
          alignSelf: "center",
          bgcolor: isDark ? "rgba(255,255,255,0.04)" : "background.default",
          border: 1,
          borderColor: "divider",
          color: "text.secondary",
          fontSize: 11,
          textAlign: "center" as const,
        };
      }}
    >
      <Typography
        variant="body2"
        sx={{ fontSize: "inherit", lineHeight: "inherit", color: "inherit", whiteSpace: "pre-wrap" }}
      >
        {message.content}
      </Typography>
      {actions.length > 0 && (
        <Box sx={{ mt: 0.5 }}>
          <Typography sx={{ fontSize: 10, fontWeight: 600, color: "text.secondary", mb: 0.25 }}>
            Suggested actions:
          </Typography>
          {actions.map((action, i) => (
            <ActionCard
              key={`${message.id}-action-${i}`}
              action={action}
              messageId={message.id}
              actionIndex={i}
            />
          ))}
        </Box>
      )}
    </Box>
  );
}
