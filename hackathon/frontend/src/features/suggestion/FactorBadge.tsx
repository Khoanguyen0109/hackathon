import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { ContextFactor } from "../../services/types";

const KIND_STYLES: Record<string, { bg: string; bgDark: string; border: string; borderDark: string; accent: string; accentDark: string }> = {
  weather: { bg: "#EDF4FF", bgDark: "#0D1A2E", border: "#B8D4F8", borderDark: "#1A3550", accent: "#007AFF", accentDark: "#3E91FF" },
  event: { bg: "#FFF8ED", bgDark: "#1E1704", border: "#F2D899", borderDark: "#3D2E0A", accent: "#E07800", accentDark: "#FFB340" },
  promo: { bg: "#FFF0EF", bgDark: "#1E0B09", border: "#F5C0BA", borderDark: "#3D1A14", accent: "#FF3B30", accentDark: "#FF6961" },
  holiday: { bg: "#F3F0FF", bgDark: "#130F25", border: "#D0C9F5", borderDark: "#2A224A", accent: "#5856D6", accentDark: "#7D7AFF" },
  day_of_week: { bg: "#F0F9E8", bgDark: "#0E1C07", border: "#BEE0A0", borderDark: "#1C3A0F", accent: "#34C759", accentDark: "#30D158" },
};

function fmtDelta(v: number) {
  if (v > 0) return `+${(v * 100).toFixed(0)}%`;
  if (v < 0) return `${(v * 100).toFixed(0)}%`;
  return "0%";
}

function deltaColor(v: number, mode: "light" | "dark") {
  if (v > 0) return mode === "light" ? "#34C759" : "#30D158";
  if (v < 0) return mode === "light" ? "#FF3B30" : "#FF453A";
  return "#8E8E93";
}

export default function FactorBadge({ factor }: { factor: ContextFactor }) {
  const style = KIND_STYLES[factor.kind] ?? KIND_STYLES.event;

  return (
    <Box
      sx={(t) => {
        const isDark = t.palette.mode === "dark";
        return {
          borderRadius: "20px",
          border: `1px solid ${isDark ? style.borderDark : style.border}`,
          bgcolor: isDark ? style.bgDark : style.bg,
          p: 2,
          width: 220,
          minWidth: 200,
          display: "flex",
          flexDirection: "column",
          gap: 0.5,
          transition: "transform 0.15s ease, box-shadow 0.2s ease",
          "&:hover": {
            transform: "translateY(-2px)",
            boxShadow: isDark
              ? "0 4px 16px rgba(0,0,0,0.3)"
              : "0 4px 16px rgba(0,0,0,0.08)",
          },
        };
      }}
    >
      <Typography
        variant="body2"
        sx={(t) => ({
          fontWeight: 700,
          color: t.palette.mode === "dark"
            ? style.accentDark
            : style.accent,
          display: "flex",
          alignItems: "center",
          gap: 0.75,
          mb: 0.25,
        })}
      >
        {factor.label}
      </Typography>

      {factor.probability != null && (
        <Row label="Probability" value={`${(factor.probability * 100).toFixed(0)}%`} bold />
      )}
      {factor.time_window && <Row label="Time" value={factor.time_window} />}
      <Row label="Delivery" value={fmtDelta(factor.impact_delivery)} delta={factor.impact_delivery} />
      <Row label="Dine-in" value={fmtDelta(factor.impact_dinein)} delta={factor.impact_dinein} />
      {factor.impact_drivethrough !== 0 && (
        <Row label="Drive-through" value={fmtDelta(factor.impact_drivethrough)} delta={factor.impact_drivethrough} />
      )}
      <Row label="Source" value={factor.source.replace(/_/g, " ")} />

      {factor.note && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mt: 0.5, lineHeight: 1.45, fontStyle: "italic", fontSize: 11 }}
        >
          {factor.note}
        </Typography>
      )}
    </Box>
  );
}

function Row({
  label,
  value,
  delta,
  bold,
}: {
  label: string;
  value: string;
  delta?: number;
  bold?: boolean;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        py: 0.25,
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: 11 }}>
        {label}
      </Typography>
      <Typography
        variant="caption"
        sx={(t) => ({
          fontWeight: bold ? 700 : 600,
          color:
            delta != null
              ? deltaColor(delta, t.palette.mode as "light" | "dark")
              : "text.primary",
          fontSize: bold ? 12 : 11,
        })}
      >
        {value}
      </Typography>
    </Box>
  );
}
