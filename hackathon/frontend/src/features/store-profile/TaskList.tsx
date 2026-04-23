import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Switch from "@mui/material/Switch";
import Skeleton from "@mui/material/Skeleton";
import { useListTasksQuery } from "../../services/storeApi";

export default function TaskList() {
  const { data: tasks, isLoading } = useListTasksQuery();

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} variant="rounded" height={52} />
        ))}
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {tasks?.map((t) => (
        <Box
          key={t.task_id}
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
            sx={(t) => ({
              width: 34,
              height: 34,
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              bgcolor: t.palette.mode === "dark" ? "#081E14" : "#E8FAF2",
              flexShrink: 0,
            })}
          >
            {t.icon_emoji ?? "📋"}
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {t.task_name}
            </Typography>
            <Typography variant="caption" color="text.disabled">
              {t.category}
            </Typography>
          </Box>
          <Switch defaultChecked size="small" color="success" />
        </Box>
      ))}
    </Box>
  );
}
