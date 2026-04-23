import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Skeleton from "@mui/material/Skeleton";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { openAddDialog, openEditDialog } from "./crewSlice";
import { useListCrewQuery } from "../../services/crewApi";
import CrewCard from "./CrewCard";
import AddCrewDialog from "./AddCrewDialog";
import EditCrewDialog from "./EditCrewDialog";
import EmptyState from "../../components/EmptyState";

export default function CrewPage() {
  const dispatch = useAppDispatch();
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const { data: crew, isLoading } = useListCrewQuery(storeId ?? "", { skip: !storeId });

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ textAlign: "left" }}>Store profile — crew members</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Add crew members, their certified stations (skills), and their typical availability. This pool appears in the deployment chart for assignment.
        </Typography>
      </Box>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 2 }}>
            Crew roster — {crew?.length ?? 0} members
          </Typography>

          {isLoading ? (
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 1.25 }}>
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} variant="rounded" height={120} />
              ))}
            </Box>
          ) : !crew?.length ? (
            <EmptyState icon="👤" message="No crew members yet. Add your first crew member to get started." />
          ) : (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                gap: 1.25,
              }}
            >
              {crew.map((emp) => (
                <CrewCard
                  key={emp.employee_id}
                  employee={emp}
                  onClick={() => dispatch(openEditDialog(emp.employee_id))}
                />
              ))}
              <Box
                onClick={() => dispatch(openAddDialog())}
                sx={{
                  border: "1px dashed",
                  borderColor: "divider",
                  borderRadius: "20px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  minHeight: 100,
                  cursor: "pointer",
                  color: "text.secondary",
                  "&:hover": { borderColor: "primary.main", color: "primary.main" },
                  transition: "all 0.15s",
                }}
              >
                <Typography sx={{ fontSize: 20, mb: 0.5, color: "inherit" }}>+</Typography>
                <Typography variant="caption" color="inherit">Add crew member</Typography>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      <AddCrewDialog />
      <EditCrewDialog crew={crew ?? []} />

    </Box>
  );
}
