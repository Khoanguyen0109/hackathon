import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";

interface FlowNavProps {
  step: number;
  totalSteps: number;
  backPath?: string;
  backLabel?: string;
  nextPath?: string;
  nextLabel?: string;
  nextVariant?: "primary" | "success";
  nextDisabled?: boolean;
  onNext?: () => void;
}

export default function FlowNav({
  step,
  totalSteps,
  backPath,
  backLabel = "← Back",
  nextPath,
  nextLabel = "Next →",
  nextVariant = "primary",
  nextDisabled = false,
  onNext,
}: FlowNavProps) {
  const navigate = useNavigate();

  const handleNext = () => {
    if (onNext) {
      onNext();
      return;
    }
    if (nextPath) navigate(nextPath);
  };

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        mt: 3,
        pt: 2,
        borderTop: 1,
        borderColor: "divider",
      }}
    >
      <Typography variant="caption" color="text.secondary">
        Step {step} of {totalSteps}
      </Typography>
      <Box sx={{ display: "flex", gap: 1 }}>
        {backPath && (
          <Button variant="outlined" onClick={() => navigate(backPath)}>
            {backLabel}
          </Button>
        )}
        {nextPath && (
          <Button
            variant="contained"
            color={nextVariant === "success" ? "success" : "primary"}
            disabled={nextDisabled}
            onClick={handleNext}
          >
            {nextLabel}
          </Button>
        )}
      </Box>
    </Box>
  );
}
