import { useParams, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import IconButton from "@mui/material/IconButton";
import Skeleton from "@mui/material/Skeleton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useGetDeploymentQuery, useGetDeploymentSummaryQuery } from "../../services/deploymentApi";
import { useListCrewQuery } from "../../services/crewApi";
import DeploymentGrid from "../deployment/DeploymentGrid";

export default function DeploymentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: deployment, isLoading, isError } = useGetDeploymentQuery(id ?? "", { skip: !id });
  const { data: summary } = useGetDeploymentSummaryQuery(id ?? "", { skip: !id });
  const { data: crew } = useListCrewQuery(deployment?.store_id ?? "", { skip: !deployment?.store_id });

  if (isLoading) {
    return (
      <Box>
        <Skeleton variant="rounded" height={40} sx={{ mb: 2, borderRadius: "16px" }} />
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2, mb: 2.5 }}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} variant="rounded" height={90} sx={{ borderRadius: "16px" }} />
          ))}
        </Box>
        <Skeleton variant="rounded" height={300} sx={{ borderRadius: "16px" }} />
      </Box>
    );
  }

  if (isError || !deployment) {
    return (
      <Box sx={{ py: 8, textAlign: "center" }}>
        <Typography color="text.secondary">Deployment not found.</Typography>
      </Box>
    );
  }

  const cells = deployment.cells;
  const totalRec = cells.reduce((s, c) => s + c.ai_recommended, 0);
  const totalAssigned = cells.reduce((s, c) => s + c.assigned_employee_ids.length, 0);
  const gaps = totalRec - totalAssigned;
  const uniqueCrew = new Set(cells.flatMap((c) => c.assigned_employee_ids)).size;
  const coveragePct = totalRec > 0 ? Math.round((totalAssigned / totalRec) * 100) : 0;

  const staffingCells = cells.map((c) => ({
    station_id: c.station_id,
    station_name: c.station_id,
    shift: c.shift,
    ai_recommended: c.ai_recommended,
    reason_short: "",
    confidence: "medium" as const,
    factors: [],
    rules_applied: [],
    channel_note: "",
    crew_note: "",
    reason_rows: [],
  }));

  return (
    <Box>
      <Box sx={{ mb: 3, display: "flex", alignItems: "center", gap: 1.5 }}>
        <IconButton onClick={() => navigate("/history")} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h6" sx={{ textAlign: "left" }}>
            Deployment chart — {deployment.date}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Saved {new Date(deployment.created_at).toLocaleString()}
          </Typography>
        </Box>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2, mb: 2.5 }}>
        <StatCard value={summary?.total_assigned ?? totalAssigned} label="Slots assigned" color="success.main" />
        <StatCard value={summary?.gap ?? gaps} label="Gaps vs AI rec" color="warning.main" />
        <StatCard value={uniqueCrew} label="Crew deployed" color="text.primary" />
        <StatCard value={`${summary?.coverage_pct ?? coveragePct}%`} label="AI rec coverage" color="primary.main" />
      </Box>

      <DeploymentGrid cells={cells} staffingCells={staffingCells} crew={crew ?? []} readOnly />
    </Box>
  );
}

function StatCard({ value, label, color }: { value: number | string; label: string; color: string }) {
  return (
    <Card>
      <CardContent>
        <Typography sx={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, fontWeight: 500, display: "block" }}>
          {label}
        </Typography>
      </CardContent>
    </Card>
  );
}
