import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import { useListStationsQuery } from "../../services/storeApi";

interface SkillPickerProps {
  selected: string[];
  onChange: (skills: string[]) => void;
}

export default function SkillPicker({ selected, onChange }: SkillPickerProps) {
  const { data: stations } = useListStationsQuery();

  const toggle = (id: string) => {
    onChange(
      selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]
    );
  };

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
      {stations?.map((st) => {
        const active = selected.includes(st.station_id);
        return (
          <Chip
            key={st.station_id}
            label={st.station_name}
            clickable
            onClick={() => toggle(st.station_id)}
            variant={active ? "filled" : "outlined"}
            color={active ? "primary" : "default"}
            sx={{
              fontWeight: 500,
              fontSize: 12,
              ...(active && { bgcolor: "primary.light", color: "primary.dark", borderColor: "primary.main" }),
            }}
          />
        );
      })}
    </Box>
  );
}
