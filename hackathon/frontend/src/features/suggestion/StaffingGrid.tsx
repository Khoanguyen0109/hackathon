import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Collapse from "@mui/material/Collapse";
import type { StaffingCell, Shift } from "../../services/types";
import ReasoningPanel from "./ReasoningPanel";

const SHIFTS: Shift[] = ["Morning", "Afternoon", "Evening"];
const SHIFT_LABELS: Record<Shift, string> = {
  Morning: "Morning (6\u201312)",
  Afternoon: "Afternoon (12\u201318)",
  Evening: "Evening (18\u201323)",
};

const CONFIDENCE_COLOR: Record<string, { light: string; dark: string }> = {
  high: { light: "#34C759", dark: "#30D158" },
  medium: { light: "#FF9500", dark: "#FFD60A" },
  low: { light: "#FF3B30", dark: "#FF453A" },
};

function hasShiftRush(cells: StaffingCell[], shift: Shift): boolean {
  return cells.some((c) => c.shift === shift && c.rush_hour?.is_rush);
}

function RushHeaderBadge({ cells, shift }: { cells: StaffingCell[]; shift: Shift }) {
  const sample = cells.find((c) => c.shift === shift && c.rush_hour?.is_rush);
  if (!sample?.rush_hour?.is_rush) return null;
  return (
    <Tooltip title={`${sample.rush_hour.label} (${sample.rush_hour.window}) — ${Math.round((sample.rush_hour.overlap_pct ?? 0) * 100)}% of shift`} arrow>
      <Chip
        label={`🔥 ${sample.rush_hour.label}`}
        size="small"
        sx={(t) => ({
          ml: 0.75,
          height: 20,
          fontSize: 9,
          fontWeight: 700,
          color: t.palette.mode === "dark" ? "#FFB340" : "#C2410C",
          bgcolor: t.palette.mode === "dark" ? "rgba(255,149,0,0.1)" : "#FFF7ED",
          border: `1px solid ${t.palette.mode === "dark" ? "rgba(255,149,0,0.2)" : "#FDBA74"}`,
          borderRadius: "10px",
        })}
      />
    </Tooltip>
  );
}

function RushSolutionTips({ cell }: { cell: StaffingCell }) {
  const [open, setOpen] = useState(false);
  const rush = cell.rush_hour;
  if (!rush?.is_rush || !rush.solutions?.length) return null;

  return (
    <Box sx={{ mt: 0.5 }}>
      <Typography
        variant="caption"
        onClick={(e) => { e.stopPropagation(); setOpen((p) => !p); }}
        sx={(t) => ({
          cursor: "pointer",
          color: t.palette.mode === "dark" ? "#FFB340" : "#C2410C",
          fontWeight: 600,
          fontSize: 9,
          display: "flex",
          alignItems: "center",
          gap: 0.25,
          "&:hover": { textDecoration: "underline" },
        })}
      >
        💡 {open ? "Hide" : "View"} rush-hour solutions
      </Typography>
      <Collapse in={open}>
        <Box
          sx={(t) => ({
            mt: 0.5,
            p: 1.25,
            borderRadius: "12px",
            bgcolor: t.palette.mode === "dark" ? "rgba(255,149,0,0.06)" : "#FFFBEB",
            border: `1px solid ${t.palette.mode === "dark" ? "rgba(255,214,10,0.15)" : "#FDE68A"}`,
            fontSize: 10,
            lineHeight: 1.5,
          })}
        >
          {rush.solutions.map((tip, i) => (
            <Box key={i} sx={{ display: "flex", gap: 0.5, mb: i < rush.solutions.length - 1 ? 0.5 : 0 }}>
              <Box component="span" sx={{ color: "warning.main", fontWeight: 700, flexShrink: 0 }}>{i + 1}.</Box>
              <Typography variant="caption" sx={{ fontSize: 10 }}>{tip}</Typography>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}

interface StaffingGridProps {
  cells: StaffingCell[];
}

export default function StaffingGrid({ cells }: StaffingGridProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const stationIds = [...new Set(cells.map((c) => c.station_id))];
  const lookup = new Map(cells.map((c) => [`${c.station_id}-${c.shift}`, c]));

  const toggle = (key: string) => setExpandedKey((prev) => (prev === key ? null : key));

  return (
    <Card>
      <CardContent>
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="subtitle2">AI recommendation</Typography>
        </Box>
        <TableContainer sx={{ borderRadius: "16px", overflow: "hidden" }}>
          <Table size="small" sx={{ minWidth: 560 }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600, fontSize: 11, color: "text.secondary", minWidth: 130 }}>
                  Station
                </TableCell>
                {SHIFTS.map((sh) => (
                  <TableCell
                    key={sh}
                    sx={(t) => ({
                      fontWeight: 600,
                      fontSize: 11,
                      color: "text.secondary",
                      ...(hasShiftRush(cells, sh) && {
                        background: t.palette.mode === "dark"
                          ? "rgba(255,149,0,0.06)"
                          : "linear-gradient(180deg, #FFF7ED 0%, transparent 100%)",
                        borderTop: `2px solid ${t.palette.mode === "dark" ? "#FFB340" : "#FB923C"}`,
                      }),
                    })}
                  >
                    <Box sx={{ display: "flex", alignItems: "center" }}>
                      {SHIFT_LABELS[sh]}
                      <RushHeaderBadge cells={cells} shift={sh} />
                    </Box>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {stationIds.map((sid) => {
                const first = cells.find((c) => c.station_id === sid);
                return (
                  <TableRow key={sid} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {first?.station_name}
                      </Typography>
                    </TableCell>
                    {SHIFTS.map((sh) => {
                      const cell = lookup.get(`${sid}-${sh}`);
                      const key = `${sid}-${sh}`;
                      if (!cell) return <TableCell key={sh} />;
                      const isRush = cell.rush_hour?.is_rush ?? false;
                      return (
                        <TableCell
                          key={sh}
                          sx={(t) => ({
                            verticalAlign: "top",
                            ...(isRush && {
                              background: t.palette.mode === "dark"
                                ? "rgba(255,149,0,0.04)"
                                : "linear-gradient(135deg, #FFF7ED 0%, #FFFBEB 100%)",
                              borderLeft: `3px solid ${t.palette.mode === "dark" ? "#FFB340" : "#FB923C"}`,
                            }),
                          })}
                        >
                          <Box
                            onClick={() => toggle(key)}
                            sx={{
                              cursor: "pointer",
                              borderRadius: "12px",
                              p: 0.75,
                              position: "relative",
                              "&:hover": {
                                bgcolor: isRush ? "rgba(251,146,60,0.06)" : "primary.light",
                              },
                              transition: "background 0.15s",
                            }}
                          >
                            <Box
                              sx={(t) => {
                                const isDark = t.palette.mode === "dark";
                                return {
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 0.75,
                                  p: "6px 10px",
                                  borderRadius: "10px",
                                  bgcolor: isRush
                                    ? (isDark ? "rgba(255,149,0,0.1)" : "#FFF7ED")
                                    : (isDark ? "rgba(62,145,255,0.1)" : "#EDF4FF"),
                                  border: `1px solid ${
                                    isRush
                                      ? (isDark ? "rgba(255,149,0,0.2)" : "#FDBA74")
                                      : (isDark ? "rgba(62,145,255,0.2)" : "#B8D4F8")
                                  }`,
                                  mb: 0.5,
                                };
                              }}
                            >
                              <Typography
                                variant="body2"
                                sx={(t) => ({
                                  fontWeight: 700,
                                  color: isRush
                                    ? (t.palette.mode === "dark" ? "#FFB340" : "#C2410C")
                                    : "primary.main",
                                })}
                              >
                                {cell.ai_recommended}
                              </Typography>
                              <Typography
                                variant="caption"
                                sx={(t) => ({
                                  color: isRush
                                    ? (t.palette.mode === "dark" ? "#E89440" : "#EA580C")
                                    : "primary.main",
                                  fontWeight: 500,
                                })}
                              >
                                staff
                              </Typography>
                              {isRush && cell.rush_hour && (
                                <Chip
                                  label={`+${cell.rush_hour.staff_uplift} rush`}
                                  size="small"
                                  sx={(t) => ({
                                    height: 18,
                                    fontSize: 9,
                                    fontWeight: 700,
                                    color: t.palette.mode === "dark" ? "#FFB340" : "#C2410C",
                                    bgcolor: t.palette.mode === "dark" ? "rgba(255,149,0,0.12)" : "#FFEDD5",
                                    border: `1px solid ${t.palette.mode === "dark" ? "rgba(255,149,0,0.2)" : "#FDBA74"}`,
                                    ml: "auto",
                                    borderRadius: "8px",
                                  })}
                                />
                              )}
                            </Box>
                            <Typography variant="caption" color="text.disabled" sx={{ fontStyle: "italic", lineHeight: 1.4 }}>
                              {cell.reason_short}
                            </Typography>
                            <Chip
                              label={cell.confidence}
                              size="small"
                              sx={(t) => {
                                const cc = CONFIDENCE_COLOR[cell.confidence] ?? CONFIDENCE_COLOR.medium;
                                const c = t.palette.mode === "dark" ? cc.dark : cc.light;
                                return {
                                  ml: 0.5,
                                  height: 18,
                                  fontSize: 9,
                                  fontWeight: 700,
                                  color: c,
                                  bgcolor: "transparent",
                                  borderRadius: "8px",
                                };
                              }}
                              icon={
                                <Box
                                  component="span"
                                  sx={(t) => {
                                    const cc = CONFIDENCE_COLOR[cell.confidence] ?? CONFIDENCE_COLOR.medium;
                                    return { fontSize: 8, color: t.palette.mode === "dark" ? cc.dark : cc.light };
                                  }}
                                >
                                  ●
                                </Box>
                              }
                            />
                            <RushSolutionTips cell={cell} />
                            <ReasoningPanel open={expandedKey === key} rows={cell.reason_rows} />
                          </Box>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
}
