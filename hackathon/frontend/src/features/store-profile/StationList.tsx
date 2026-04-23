import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Switch from "@mui/material/Switch";
import Skeleton from "@mui/material/Skeleton";
import { useListStationsQuery } from "../../services/storeApi";

const AREA_COLORS: Record<string, { light: string; dark: string }> = {
  kitchen: { light: "#FFF3E0", dark: "#2A1A05" },
  front: { light: "#EDF4FF", dark: "#0D1A2E" },
  delivery: { light: "#F0F9E8", dark: "#0E1C07" },
};

export default function StationList() {
  const { data: stations, isLoading } = useListStationsQuery();

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} variant="rounded" height={52} />
        ))}
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {stations?.map((s) => (
        <Box
          key={s.station_id}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.25,
            p: "10px 14px",
            borderRadius: "14px",
            border: 1,
            borderColor: "divider",
            "&:hover": { borderColor: "primary.main", boxShadow: 1 },
            transition: "all 0.15s",
          }}
        >
          <Box
            sx={(t) => {
              const colors = AREA_COLORS[s.area.toLowerCase()] ?? { light: "#F2F2F7", dark: "#1C1C1E" };
              return {
                width: 34,
                height: 34,
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 16,
                bgcolor: t.palette.mode === "dark" ? colors.dark : colors.light,
                flexShrink: 0,
              };
            }}
          >
            {s.icon_emoji ?? "📍"}
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {s.station_name}
            </Typography>
            <Typography variant="caption" color="text.disabled">
              {s.area} · {s.positions} positions
            </Typography>
          </Box>
          <Switch defaultChecked size="small" color="success" />
        </Box>
      ))}
    </Box>
  );
}
