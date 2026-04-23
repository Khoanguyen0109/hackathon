import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import { useListStationsQuery } from "../../services/storeApi";
import type { Employee, AssignedCell } from "../../services/types";

interface CrewPoolProps {
  crew: Employee[];
  cells: AssignedCell[];
}

export default function CrewPool({ crew, cells }: CrewPoolProps) {
  const { data: stations } = useListStationsQuery();
  const nameMap = new Map(stations?.map((s) => [s.station_id, s.station_name]) ?? []);
  const assignedIds = new Set(cells.flatMap((c) => c.assigned_employee_ids));
  const available = crew.filter((e) => !assignedIds.has(e.employee_id));
  const assigned = crew.filter((e) => assignedIds.has(e.employee_id));

  return (
    <Card>
      <CardContent>
        <Typography variant="subtitle2" sx={{ mb: 1.5 }}>Crew pool</Typography>

        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.75 }}>
          Available ({available.length})
        </Typography>
        {available.length === 0 ? (
          <Typography variant="caption" color="text.disabled">All crew assigned</Typography>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, mb: 2 }}>
            {available.map((e) => (
              <Box
                key={e.employee_id}
                sx={(t) => ({
                  p: 1.25,
                  borderRadius: "14px",
                  border: 1,
                  borderColor: "divider",
                  bgcolor: t.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.01)",
                  "&:hover": {
                    borderColor: "primary.main",
                    bgcolor: t.palette.mode === "dark" ? "rgba(62,145,255,0.04)" : "rgba(0,122,255,0.02)",
                  },
                  transition: "all 0.15s",
                })}
              >
                <Typography variant="caption" sx={{ fontWeight: 600 }}>{e.employee_name}</Typography>
                <Box sx={{ display: "flex", gap: 0.5, mt: 0.5, flexWrap: "wrap" }}>
                  {e.skills.map((sk) => (
                    <Chip key={sk} label={nameMap.get(sk) ?? sk} size="small" sx={{ fontSize: 9, height: 20, borderRadius: "10px" }} />
                  ))}
                </Box>
              </Box>
            ))}
          </Box>
        )}

        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.75 }}>
          Assigned ({assigned.length})
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
          {assigned.map((e) => (
            <Chip
              key={e.employee_id}
              label={e.employee_name}
              size="small"
              color="success"
              variant="outlined"
              sx={{ fontSize: 10, height: 24 }}
            />
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}
