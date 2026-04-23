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
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import { useAppDispatch } from "../../app/hooks";
import { assignEmployee, unassignEmployee } from "./deploymentSlice";
import type { AssignedCell, StaffingCell, Employee, Shift } from "../../services/types";

const SHIFTS: Shift[] = ["Morning", "Afternoon", "Evening"];
const SHIFT_LABELS: Record<Shift, string> = {
  Morning: "Morning (6\u201312)",
  Afternoon: "Afternoon (12\u201318)",
  Evening: "Evening (18\u201323)",
};

function rushForShift(staffingCells: StaffingCell[], shift: Shift) {
  const sample = staffingCells.find((c) => c.shift === shift && c.rush_hour?.is_rush);
  return sample?.rush_hour;
}

interface DeploymentGridProps {
  cells: AssignedCell[];
  staffingCells: StaffingCell[];
  crew: Employee[];
}

export default function DeploymentGrid({ cells, staffingCells, crew }: DeploymentGridProps) {
  const dispatch = useAppDispatch();
  const empMap = new Map(crew.map((e) => [e.employee_id, e]));
  const stationIds = [...new Set(cells.map((c) => c.station_id))];
  const cellMap = new Map(cells.map((c) => [`${c.station_id}-${c.shift}`, c]));
  const staffMap = new Map(staffingCells.map((c) => [`${c.station_id}-${c.shift}`, c]));

  const getAvailable = (_stationId: string, shift: Shift): Employee[] => {
    const assigned = new Set(cells.flatMap((c) => c.shift === shift ? c.assigned_employee_ids : []));
    return crew.filter(
      (e) => !assigned.has(e.employee_id) && e.available_shifts.includes(shift)
    );
  };

  return (
    <Card>
      <CardContent>
        <TableContainer sx={{ borderRadius: "16px", overflow: "hidden" }}>
          <Table size="small" sx={{ minWidth: 500 }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600, fontSize: 11, color: "text.secondary", minWidth: 120 }}>Station</TableCell>
                {SHIFTS.map((sh) => {
                  const rush = rushForShift(staffingCells, sh);
                  return (
                    <TableCell
                      key={sh}
                      sx={(t) => ({
                        fontWeight: 600,
                        fontSize: 11,
                        color: "text.secondary",
                        ...(rush && {
                          background: t.palette.mode === "dark"
                            ? "rgba(255,149,0,0.06)"
                            : "linear-gradient(180deg, #FFF7ED 0%, transparent 100%)",
                          borderTop: `2px solid ${t.palette.mode === "dark" ? "#FFB340" : "#FB923C"}`,
                        }),
                      })}
                    >
                      <Box sx={{ display: "flex", alignItems: "center" }}>
                        {SHIFT_LABELS[sh]}
                        {rush && (
                          <Tooltip title={`${rush.label} (${rush.window})`} arrow>
                            <Chip
                              label={`🔥 ${rush.label}`}
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
                        )}
                      </Box>
                    </TableCell>
                  );
                })}
              </TableRow>
            </TableHead>
            <TableBody>
              {stationIds.map((sid) => {
                const stName = staffingCells.find((c) => c.station_id === sid)?.station_name ?? sid;
                return (
                  <TableRow key={sid} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{stName}</Typography>
                    </TableCell>
                    {SHIFTS.map((sh) => {
                      const cell = cellMap.get(`${sid}-${sh}`);
                      if (!cell) return <TableCell key={sh} />;
                      const diff = cell.assigned_employee_ids.length - cell.ai_recommended;
                      const available = getAvailable(sid, sh);
                      const scell = staffMap.get(`${sid}-${sh}`);
                      const isRush = scell?.rush_hour?.is_rush ?? false;

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
                                minWidth: 14,
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
                              AI rec
                            </Typography>
                            {isRush && scell?.rush_hour && (
                              <Chip
                                label={`+${scell.rush_hour.staff_uplift} rush`}
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
                          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.75 }}>
                            {cell.assigned_employee_ids.map((eid) => {
                              const emp = empMap.get(eid);
                              return (
                                <Chip
                                  key={eid}
                                  label={emp ? emp.employee_name.split(" ").map((w: string) => w[0]).join("") : eid.slice(0, 4)}
                                  size="small"
                                  onDelete={() => dispatch(unassignEmployee({ stationId: sid, shift: sh, employeeId: eid }))}
                                  sx={{ fontSize: 10, fontWeight: 600, height: 24 }}
                                />
                              );
                            })}
                            {available.length > 0 && (
                              <Button
                                size="small"
                                variant="outlined"
                                sx={{
                                  minWidth: 0,
                                  px: 1,
                                  py: 0.25,
                                  fontSize: 10,
                                  borderStyle: "dashed",
                                  borderRadius: "10px",
                                }}
                                onClick={() => {
                                  const next = available[0];
                                  if (next) dispatch(assignEmployee({ stationId: sid, shift: sh, employeeId: next.employee_id }));
                                }}
                              >
                                + assign
                              </Button>
                            )}
                          </Box>
                          {diff < 0 && (
                            <Chip
                              label={`⚠ ${Math.abs(diff)} short`}
                              size="small"
                              color="warning"
                              variant="outlined"
                              sx={{ mt: 0.5, fontSize: 10, height: 22 }}
                            />
                          )}
                          {diff === 0 && cell.assigned_employee_ids.length > 0 && (
                            <Chip
                              label={"✓ met"}
                              size="small"
                              color="success"
                              variant="outlined"
                              sx={{ mt: 0.5, fontSize: 10, height: 22 }}
                            />
                          )}
                          {diff > 0 && (
                            <Chip
                              label={`+${diff} over`}
                              size="small"
                              color="warning"
                              variant="outlined"
                              sx={{ mt: 0.5, fontSize: 10, height: 22 }}
                            />
                          )}
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
