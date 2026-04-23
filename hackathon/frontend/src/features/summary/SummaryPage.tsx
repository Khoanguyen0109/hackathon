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
import { useAppSelector } from "../../app/hooks";

export default function SummaryPage() {
  const staffing = useAppSelector((s) => s.suggestion.staffing);
  const cells = useAppSelector((s) => s.deployment.cells);

  if (!staffing) {
    return (
      <Box sx={{ py: 8, textAlign: "center" }}>
        <Typography color="text.secondary">No deployment saved yet.</Typography>
      </Box>
    );
  }

  const totalRec = cells.reduce((s, c) => s + c.ai_recommended, 0);
  const totalAssigned = cells.reduce((s, c) => s + c.assigned_employee_ids.length, 0);
  const gaps = totalRec - totalAssigned;
  const uniqueCrew = new Set(cells.flatMap((c) => c.assigned_employee_ids)).size;
  const coveragePct = totalRec > 0 ? Math.round((totalAssigned / totalRec) * 100) : 0;

  const shortCells = cells.filter((c) => c.assigned_employee_ids.length < c.ai_recommended);
  const stNameMap = new Map(staffing.cells.map((c) => [c.station_id, c.station_name]));

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ textAlign: "left" }}>Deployment chart saved</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Chart for {staffing.day_of_week} {staffing.date} has been saved. Below is the coverage summary and AI vs. manager comparison.
        </Typography>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2, mb: 2.5 }}>
        <StatCard value={totalAssigned} label="Slots assigned" color="success.main" />
        <StatCard value={gaps} label="Gaps vs AI rec" color="warning.main" />
        <StatCard value={uniqueCrew} label="Crew deployed" color="text.primary" />
        <StatCard value={`${coveragePct}%`} label="AI rec coverage" color="primary.main" />
      </Box>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>AI suggestion vs. manager final — diff log</Typography>
          <TableContainer sx={{ borderRadius: "16px" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, fontSize: 11 }}>Station</TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: 11 }}>Shift</TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: 11 }}>AI rec</TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: 11 }}>Assigned</TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: 11 }}>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {shortCells.map((c) => {
                  const diff = c.assigned_employee_ids.length - c.ai_recommended;
                  return (
                    <TableRow key={`${c.station_id}-${c.shift}`}>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{stNameMap.get(c.station_id) ?? c.station_id}</Typography>
                      </TableCell>
                      <TableCell><Typography variant="body2">{c.shift}</Typography></TableCell>
                      <TableCell><Typography variant="body2" color="primary.main">{c.ai_recommended}</Typography></TableCell>
                      <TableCell><Typography variant="body2">{c.assigned_employee_ids.length}</Typography></TableCell>
                      <TableCell>
                        <Chip label={`⚠ ${diff}`} size="small" color="warning" variant="outlined" sx={{ fontSize: 10, height: 22 }} />
                      </TableCell>
                    </TableRow>
                  );
                })}
                {shortCells.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} sx={{ textAlign: "center" }}>
                      <Chip label="✓ All slots met" size="small" color="success" variant="outlined" />
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: "block" }}>
            Diff stored for AI learning and historical audit. View historical charts in the Saved Charts section.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}

function StatCard({ value, label, color }: { value: number | string; label: string; color: string }) {
  return (
    <Card>
      <CardContent>
        <Typography sx={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, fontWeight: 500, display: "block" }}>{label}</Typography>
      </CardContent>
    </Card>
  );
}
