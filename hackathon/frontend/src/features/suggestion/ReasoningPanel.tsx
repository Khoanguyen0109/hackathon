import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Collapse from "@mui/material/Collapse";
import type { ReasonRow } from "../../services/types";

interface ReasoningPanelProps {
  open: boolean;
  rows: ReasonRow[];
}

export default function ReasoningPanel({ open, rows }: ReasoningPanelProps) {
  return (
    <Collapse in={open}>
      <Box
        sx={(t) => ({
          mt: 1,
          p: 1.5,
          bgcolor: t.palette.mode === "dark" ? "rgba(255,255,255,0.04)" : "background.default",
          border: 1,
          borderColor: "divider",
          borderRadius: "16px",
        })}
      >
        {rows.map((r, i) => (
          <Box
            key={i}
            sx={{
              display: "flex",
              gap: 1,
              alignItems: "flex-start",
              py: 0.5,
              ...(i < rows.length - 1 && {
                borderBottom: "1px solid",
                borderColor: "divider",
                pb: 0.75,
                mb: 0.25,
              }),
            }}
          >
            <Typography sx={{ flexShrink: 0, width: 18, textAlign: "center", fontSize: 12 }}>
              {r.icon}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, minWidth: 70, flexShrink: 0 }}>
              {r.label}
            </Typography>
            <Typography variant="caption" sx={{ flex: 1, lineHeight: 1.5 }}>
              {r.value}
            </Typography>
          </Box>
        ))}
      </Box>
    </Collapse>
  );
}
