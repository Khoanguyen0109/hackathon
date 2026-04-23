import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import { useListStationsQuery } from "../../services/storeApi";
import type { Employee } from "../../services/types";

const STATION_COLORS: Record<string, { bg: string; bgDark: string; text: string; textDark: string }> = {
  ST_GRILL: { bg: "#FFF3E0", bgDark: "#2A1A05", text: "#E07800", textDark: "#FFB340" },
  ST_FRYER: { bg: "#FFF0EF", bgDark: "#1E0B09", text: "#FF3B30", textDark: "#FF6961" },
  ST_DT: { bg: "#F0F9E8", bgDark: "#0E1C07", text: "#34C759", textDark: "#30D158" },
  ST_COUNTER: { bg: "#EDF4FF", bgDark: "#0D1A2E", text: "#007AFF", textDark: "#3E91FF" },
  ST_ASSEMBLY: { bg: "#F3F0FF", bgDark: "#130F25", text: "#5856D6", textDark: "#7D7AFF" },
  ST_PREP: { bg: "#E8FAF2", bgDark: "#081E14", text: "#00C7BE", textDark: "#63E6BE" },
};

function stationColor(id: string) {
  return STATION_COLORS[id] ?? { bg: "#F2F2F7", bgDark: "#1C1C1E", text: "#8E8E93", textDark: "#8E8E93" };
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

interface CrewCardProps {
  employee: Employee;
  onClick: () => void;
}

export default function CrewCard({ employee, onClick }: CrewCardProps) {
  const { data: stations } = useListStationsQuery();
  const nameMap = new Map(stations?.map((s) => [s.station_id, s.station_name]) ?? []);
  const first = employee.skills[0] ?? "";
  const color = stationColor(first);

  return (
    <Box
      onClick={onClick}
      sx={(t) => {
        const isDark = t.palette.mode === "dark";
        return {
          p: 2,
          borderRadius: "20px",
          border: 1,
          borderColor: "divider",
          cursor: "pointer",
          bgcolor: isDark ? "rgba(44, 44, 46, 0.6)" : "rgba(255, 255, 255, 0.8)",
          backdropFilter: "blur(10px)",
          "&:hover": {
            borderColor: "primary.main",
            boxShadow: isDark
              ? "0 4px 16px rgba(0,0,0,0.3)"
              : "0 4px 16px rgba(0,0,0,0.08)",
            transform: "translateY(-2px)",
          },
          transition: "all 0.2s ease",
        };
      }}
    >
      <Box
        sx={(t) => {
          const isDark = t.palette.mode === "dark";
          return {
            width: 40,
            height: 40,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13,
            fontWeight: 700,
            mb: 1.25,
            bgcolor: isDark ? color.bgDark : color.bg,
            color: isDark ? color.textDark : color.text,
          };
        }}
      >
        {initials(employee.employee_name)}
      </Box>
      <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.75 }}>
        {employee.employee_name}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {employee.skills.map((sk) => {
          const c = stationColor(sk);
          return (
            <Chip
              key={sk}
              label={nameMap.get(sk) ?? sk}
              size="small"
              sx={(t) => {
                const isDark = t.palette.mode === "dark";
                return {
                  bgcolor: isDark ? c.bgDark : c.bg,
                  color: isDark ? c.textDark : c.text,
                  fontSize: 10,
                  height: 22,
                  borderRadius: "12px",
                };
              }}
            />
          );
        })}
      </Box>
    </Box>
  );
}
