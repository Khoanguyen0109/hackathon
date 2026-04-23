import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { StaffingResponse } from "../../services/types";

export default function AiSummaryBanner({ staffing }: { staffing: StaffingResponse }) {
  const totalRec = staffing.cells.reduce((s, c) => s + c.ai_recommended, 0);
  const factors = staffing.context.factors;
  const deltas = staffing.context.channel_multipliers;

  const rushCells = staffing.cells.filter((c) => c.rush_hour?.is_rush);
  const rushLabels = [...new Set(rushCells.map((c) => c.rush_hour?.label).filter(Boolean))];
  const totalRushUplift = rushCells.reduce((s, c) => s + (c.rush_hour?.staff_uplift ?? 0), 0);

  return (
    <Box
      sx={(t) => {
        const isDark = t.palette.mode === "dark";
        return {
          mt: 2,
          p: 2.5,
          background: isDark
            ? "linear-gradient(135deg, rgba(62,145,255,0.08) 0%, rgba(125,122,255,0.08) 100%)"
            : "linear-gradient(135deg, #EDF4FF 0%, #F3F0FF 100%)",
          border: 1,
          borderColor: isDark ? "rgba(62,145,255,0.2)" : "#B8D4F8",
          borderRadius: "20px",
        };
      }}
    >
      <Typography
        variant="body2"
        sx={{
          fontWeight: 700,
          mb: 0.75,
          display: "flex",
          alignItems: "center",
          gap: 0.75,
          color: "primary.main",
        }}
      >
        {"◆"} AI reasoning summary
      </Typography>
      <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
        <strong>{staffing.day_of_week} {staffing.date}</strong> —{" "}
        {factors.map((f) => f.label).join(", ")}. Total recommended:{" "}
        <strong>{totalRec} staff-slots</strong> across 3 shifts.
      </Typography>

      {rushLabels.length > 0 && (
        <Box
          sx={(t) => {
            const isDark = t.palette.mode === "dark";
            return {
              mt: 1.25,
              p: 1.5,
              borderRadius: "16px",
              background: isDark
                ? "rgba(255,149,0,0.08)"
                : "linear-gradient(135deg, #FFF7ED 0%, #FFFBEB 100%)",
              border: `1px solid ${isDark ? "rgba(255,149,0,0.2)" : "#FDBA74"}`,
              display: "flex",
              alignItems: "center",
              gap: 1,
            };
          }}
        >
          <Typography variant="body2" sx={{ fontSize: 16 }}>{"🔥"}</Typography>
          <Box>
            <Typography
              variant="body2"
              sx={(t) => ({
                fontWeight: 700,
                color: t.palette.mode === "dark" ? "#FFB340" : "#C2410C",
                fontSize: 12,
              })}
            >
              Rush-hour impact: {rushLabels.join(" & ")}
            </Typography>
            <Typography
              variant="caption"
              sx={(t) => ({
                color: t.palette.mode === "dark" ? "#D4A574" : "#92400E",
                lineHeight: 1.5,
              })}
            >
              {totalRushUplift} extra staff-slots added across rush-hour shifts.
              Stagger breaks and pre-prep to handle peak throughput.
            </Typography>
          </Box>
        </Box>
      )}

      <Box sx={{ display: "flex", gap: 1.5, mt: 1.25, flexWrap: "wrap" }}>
        {Object.entries(deltas).map(([ch, val]) => (
          <Box
            key={ch}
            sx={(t) => {
              const isDark = t.palette.mode === "dark";
              return {
                fontSize: 11,
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                px: 1.5,
                py: 0.5,
                borderRadius: "12px",
                bgcolor: isDark ? "rgba(255,255,255,0.06)" : "background.paper",
                border: 1,
                borderColor: "divider",
                fontWeight: 600,
                backdropFilter: "blur(10px)",
              };
            }}
          >
            {ch}
            <Box
              component="span"
              sx={{
                color: val > 0 ? "success.main" : val < 0 ? "error.main" : "text.disabled",
                ml: 0.25,
              }}
            >
              {val > 0 ? "+" : ""}{(val * 100).toFixed(0)}%
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
