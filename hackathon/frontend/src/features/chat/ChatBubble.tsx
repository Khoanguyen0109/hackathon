import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CheckIcon from "@mui/icons-material/Check";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import PersonRemoveIcon from "@mui/icons-material/PersonRemove";
import type { ChatMessage, ChatAction } from "../../services/types";
import { useAppDispatch } from "../../app/hooks";
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
  const [applied, setApplied] = useState(!!action.applied);

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
    }
    dispatch(markActionApplied({ messageId, actionIndex }));
    setApplied(true);
  };

  const icon = action.type === "unassign" ? <PersonRemoveIcon sx={{ fontSize: 14 }} /> : <PersonAddIcon sx={{ fontSize: 14 }} />;

  return (
    <Box
      sx={(t) => ({
        mt: 0.75,
        p: 1.25,
        borderRadius: "14px",
        bgcolor: applied
          ? (t.palette.mode === "dark" ? "rgba(48,209,88,0.08)" : "success.light")
          : (t.palette.mode === "dark" ? "rgba(255,255,255,0.04)" : "background.paper"),
        border: 1,
        borderColor: applied ? "success.main" : "divider",
        transition: "all 0.2s",
      })}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
        <Chip
          label={action.type}
          size="small"
          color={action.type === "assign" ? "primary" : "warning"}
          sx={{ fontSize: 9, height: 20, borderRadius: "10px" }}
        />
        <Typography sx={{ fontSize: 11, fontWeight: 600, flex: 1 }}>
          {action.employee_name || action.employee_id} → {action.station_name || action.station_id} ({action.shift})
        </Typography>
      </Box>
      <Typography sx={{ fontSize: 10, color: "text.secondary", mb: 0.75 }}>
        {action.reason}
      </Typography>
      <Button
        size="small"
        variant={applied ? "outlined" : "contained"}
        color={applied ? "success" : "primary"}
        disabled={applied}
        onClick={handleApply}
        startIcon={applied ? <CheckIcon sx={{ fontSize: 12 }} /> : icon}
        sx={{ fontSize: 10, py: 0.25, px: 1.5, minHeight: 24 }}
      >
        {applied ? "Applied" : "Apply"}
      </Button>
    </Box>
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
