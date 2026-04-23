import { useState, useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Collapse from "@mui/material/Collapse";
import Tooltip from "@mui/material/Tooltip";
import Avatar from "@mui/material/Avatar";
import LinearProgress from "@mui/material/LinearProgress";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import SearchIcon from "@mui/icons-material/Search";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { useListStationsQuery } from "../../services/storeApi";
import type { Employee, AssignedCell, Shift } from "../../services/types";

const AVATAR_COLORS = [
  "#007AFF", "#5856D6", "#FF9500", "#34C759", "#FF2D55",
  "#AF52DE", "#FF6482", "#00C7BE", "#30B0C7", "#A2845E",
];

const SHIFT_CONFIG: { key: Shift; label: string; abbr: string; color: string }[] = [
  { key: "Morning", label: "Morning", abbr: "M", color: "#FF9500" },
  { key: "Afternoon", label: "Afternoon", abbr: "A", color: "#007AFF" },
  { key: "Evening", label: "Evening", abbr: "E", color: "#5856D6" },
];

function avatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function initials(name: string): string {
  return name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
}

function stationAssignment(emp: Employee, cells: AssignedCell[]): { station: string; shift: Shift } | null {
  for (const c of cells) {
    if (c.assigned_employee_ids.includes(emp.employee_id)) {
      return { station: c.station_id, shift: c.shift };
    }
  }
  return null;
}

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
  const [expanded, setExpanded] = useState(true);
  const [search, setSearch] = useState("");

  const filteredAvailable = useMemo(() => {
    if (!search.trim()) return available;
    const q = search.toLowerCase();
    return available.filter(
      (e) =>
        e.employee_name.toLowerCase().includes(q) ||
        e.skills.some((sk) => (nameMap.get(sk) ?? sk).toLowerCase().includes(q))
    );
  }, [available, search, nameMap]);

  const totalSlots = cells.reduce((s, c) => s + c.ai_recommended, 0);
  const filledSlots = cells.reduce((s, c) => s + c.assigned_employee_ids.length, 0);
  const pct = totalSlots > 0 ? Math.round((filledSlots / totalSlots) * 100) : 0;

  return (
    <Card sx={{ overflow: "hidden" }}>
      <CardContent sx={{ p: "12px 14px !important" }}>
        {/* Header */}
        <Box
          onClick={() => setExpanded((v) => !v)}
          sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer" }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            <Typography sx={{ fontWeight: 700, fontSize: 12 }}>Crew</Typography>
            <Box sx={{ display: "flex", gap: 0.375 }}>
              <Chip
                label={`${available.length} free`}
                size="small"
                color={available.length > 0 ? "primary" : "default"}
                variant={available.length > 0 ? "filled" : "outlined"}
                sx={{ fontSize: 9, height: 18, borderRadius: "9px", "& .MuiChip-label": { px: 0.75 } }}
              />
              <Chip
                label={`${assigned.length} placed`}
                size="small"
                color="success"
                variant="outlined"
                sx={{ fontSize: 9, height: 18, borderRadius: "9px", "& .MuiChip-label": { px: 0.75 } }}
              />
            </Box>
          </Box>
          <IconButton size="small" sx={{ width: 22, height: 22 }}>
            {expanded ? <ExpandLessIcon sx={{ fontSize: 14 }} /> : <ExpandMoreIcon sx={{ fontSize: 14 }} />}
          </IconButton>
        </Box>

        {/* Coverage progress bar */}
        <Box sx={{ mt: 1, mb: expanded ? 1 : 0 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9 }}>
              Coverage
            </Typography>
            <Typography variant="caption" sx={{ fontSize: 9, fontWeight: 600, color: pct >= 100 ? "success.main" : "warning.main" }}>
              {filledSlots}/{totalSlots} slots ({pct}%)
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={Math.min(pct, 100)}
            color={pct >= 100 ? "success" : pct >= 60 ? "primary" : "warning"}
            sx={{ height: 4, borderRadius: 2, bgcolor: (t) => t.palette.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" }}
          />
        </Box>

        <Collapse in={expanded}>
          {/* Search */}
          {crew.length > 4 && (
            <TextField
              size="small"
              fullWidth
              placeholder="Filter crew..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ fontSize: 14, color: "text.disabled" }} />
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                mb: 1,
                "& .MuiOutlinedInput-root": { borderRadius: "10px", fontSize: 11, height: 30 },
                "& .MuiOutlinedInput-input": { py: 0.5 },
              }}
            />
          )}

          {/* Available crew */}
          {filteredAvailable.length === 0 ? (
            <Typography variant="caption" color="text.disabled" sx={{ display: "block", mb: 1, textAlign: "center", py: 1 }}>
              {search ? "No matches" : "All crew assigned"}
            </Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.375, mb: 1 }}>
              {filteredAvailable.map((e) => (
                <CrewRow key={e.employee_id} emp={e} nameMap={nameMap} status="available" />
              ))}
            </Box>
          )}

          {/* Assigned crew */}
          {assigned.length > 0 && (
            <>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
                <Box sx={{ flex: 1, height: "1px", bgcolor: "divider" }} />
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Assigned
                </Typography>
                <Box sx={{ flex: 1, height: "1px", bgcolor: "divider" }} />
              </Box>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.375 }}>
                {assigned.map((e) => (
                  <CrewRow key={e.employee_id} emp={e} nameMap={nameMap} status="assigned" cells={cells} />
                ))}
              </Box>
            </>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
}

function CrewRow({
  emp,
  nameMap,
  status,
  cells,
}: {
  emp: Employee;
  nameMap: Map<string, string>;
  status: "available" | "assigned";
  cells?: AssignedCell[];
}) {
  const assignment = cells ? stationAssignment(emp, cells) : null;
  const isAssigned = status === "assigned";
  const color = avatarColor(emp.employee_name);

  return (
    <Box
      sx={(t) => {
        const isDark = t.palette.mode === "dark";
        return {
          display: "flex",
          alignItems: "center",
          gap: 0.75,
          p: "5px 8px",
          borderRadius: "10px",
          border: 1,
          borderColor: isAssigned
            ? (isDark ? "rgba(48,209,88,0.2)" : "rgba(52,199,89,0.25)")
            : "divider",
          bgcolor: isAssigned
            ? (isDark ? "rgba(48,209,88,0.04)" : "rgba(52,199,89,0.03)")
            : (isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.008)"),
          "&:hover": {
            borderColor: isAssigned ? "success.main" : "primary.main",
            bgcolor: isAssigned
              ? (isDark ? "rgba(48,209,88,0.08)" : "rgba(52,199,89,0.06)")
              : (isDark ? "rgba(62,145,255,0.06)" : "rgba(0,122,255,0.03)"),
          },
          transition: "all 0.15s",
          cursor: "default",
        };
      }}
    >
      {/* Avatar */}
      <Avatar
        sx={{
          width: 26,
          height: 26,
          fontSize: 9,
          fontWeight: 700,
          bgcolor: isAssigned ? "success.main" : color,
          flexShrink: 0,
        }}
      >
        {isAssigned ? <CheckCircleIcon sx={{ fontSize: 14 }} /> : initials(emp.employee_name)}
      </Avatar>

      {/* Name + meta */}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography
          sx={{
            fontSize: 11,
            fontWeight: 600,
            lineHeight: 1.2,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {emp.employee_name}
        </Typography>
        {isAssigned && assignment ? (
          <Typography variant="caption" color="success.main" sx={{ fontSize: 8.5, fontWeight: 500 }}>
            {nameMap.get(assignment.station) ?? assignment.station} · {assignment.shift}
          </Typography>
        ) : (
          <Box sx={{ display: "flex", gap: 0.25, mt: 0.125 }}>
            {emp.skills.slice(0, 3).map((sk) => (
              <Tooltip key={sk} title={nameMap.get(sk) ?? sk} arrow>
                <Box
                  sx={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    bgcolor: avatarColor(nameMap.get(sk) ?? sk),
                    opacity: 0.7,
                  }}
                />
              </Tooltip>
            ))}
            {emp.skills.length > 3 && (
              <Typography variant="caption" color="text.disabled" sx={{ fontSize: 8, lineHeight: 1, ml: 0.125 }}>
                +{emp.skills.length - 3}
              </Typography>
            )}
          </Box>
        )}
      </Box>

      {/* Shift availability badges */}
      <Box sx={{ display: "flex", gap: 0.25, flexShrink: 0 }}>
        {SHIFT_CONFIG.map((sh) => {
          const has = emp.available_shifts.includes(sh.key);
          return (
            <Tooltip key={sh.key} title={`${sh.label}${has ? "" : " (unavailable)"}`} arrow>
              <Box
                sx={{
                  width: 16,
                  height: 16,
                  borderRadius: "4px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 8,
                  fontWeight: 700,
                  color: has ? "#fff" : "text.disabled",
                  bgcolor: has ? sh.color : "transparent",
                  border: has ? "none" : "1px solid",
                  borderColor: "divider",
                  opacity: has ? 1 : 0.4,
                  transition: "all 0.15s",
                }}
              >
                {sh.abbr}
              </Box>
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
}
