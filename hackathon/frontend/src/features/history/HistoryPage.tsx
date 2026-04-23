import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import { useNavigate } from "react-router-dom";
import { useAppSelector } from "../../app/hooks";
import { useListDeploymentsQuery } from "../../services/deploymentApi";
import EmptyState from "../../components/EmptyState";

export default function HistoryPage() {
  const navigate = useNavigate();
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const { data: deployments, isLoading } = useListDeploymentsQuery(
    { storeId: storeId ?? "" },
    { skip: !storeId }
  );

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ textAlign: "left" }}>Saved deployment charts</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          View, edit, or compare past deployment charts. Click any row to re-open.
        </Typography>
      </Box>

      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
        <Button variant="contained" size="small" onClick={() => navigate("/")}>
          + New chart
        </Button>
      </Box>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 2 }}>Recent charts</Typography>
          {isLoading ? (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {[1, 2, 3].map((i) => <Skeleton key={i} variant="rounded" height={60} sx={{ borderRadius: "16px" }} />)}
            </Box>
          ) : !deployments?.length ? (
            <EmptyState icon="📋" message="No saved charts yet. Create a deployment to see it here." />
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {deployments.map((d) => {
                const totalRec = d.cells.reduce((s, c) => s + c.ai_recommended, 0);
                const totalAssigned = d.cells.reduce((s, c) => s + c.assigned_employee_ids.length, 0);
                const uniqueCrew = new Set(d.cells.flatMap((c) => c.assigned_employee_ids)).size;
                return (
                  <Box
                    key={d.deployment_id}
                    sx={(t) => {
                      const isDark = t.palette.mode === "dark";
                      return {
                        display: "flex",
                        alignItems: "center",
                        gap: 1.75,
                        p: "14px 18px",
                        borderRadius: "16px",
                        border: 1,
                        borderColor: "divider",
                        cursor: "pointer",
                        bgcolor: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.01)",
                        "&:hover": {
                          borderColor: "primary.main",
                          boxShadow: isDark
                            ? "0 4px 16px rgba(0,0,0,0.3)"
                            : "0 4px 16px rgba(0,0,0,0.06)",
                          transform: "translateY(-1px)",
                          bgcolor: isDark ? "rgba(62,145,255,0.04)" : "rgba(0,122,255,0.02)",
                        },
                        transition: "all 0.2s ease",
                      };
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600, minWidth: 120 }}>
                      📅 {d.date}
                    </Typography>
                    <Box sx={{ flex: 1 }} />
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                      👥 {uniqueCrew} crew
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                      {totalAssigned}/{totalRec} slots
                    </Typography>
                    <Chip
                      label="Saved"
                      size="small"
                      color="success"
                      variant="outlined"
                      sx={{ fontSize: 11 }}
                    />
                  </Box>
                );
              })}
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
