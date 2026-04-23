import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

interface EmptyStateProps {
  icon: string;
  message: string;
}

export default function EmptyState({ icon, message }: EmptyStateProps) {
  return (
    <Box sx={{ textAlign: "center", py: 5, color: "text.secondary" }}>
      <Typography sx={{ fontSize: 32, opacity: 0.5, mb: 1 }}>{icon}</Typography>
      <Typography variant="body2">{message}</Typography>
    </Box>
  );
}
