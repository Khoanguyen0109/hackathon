import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { closeAddDialog } from "./crewSlice";
import { useAddCrewMemberMutation } from "../../services/crewApi";
import SkillPicker from "./SkillPicker";

const ROLES = ["Crew", "Shift Lead", "Manager", "Driver", "Cleaner"];
const DAY_OPTIONS = ["Mon–Sun", "Mon–Sat", "Mon–Fri", "Tue–Sun", "Wed–Sun"];
const SHIFT_OPTIONS = ["All shifts", "Morning+Afternoon", "Afternoon+Evening", "Morning only", "Evening only"];

function parseDays(label: string): string[] {
  const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const m = label.match(/^(\w+)–(\w+)$/);
  if (!m) return dayNames;
  const start = dayNames.indexOf(m[1]);
  const end = dayNames.indexOf(m[2]);
  if (start < 0 || end < 0) return dayNames;
  return start <= end ? dayNames.slice(start, end + 1) : [...dayNames.slice(start), ...dayNames.slice(0, end + 1)];
}

function parseShifts(label: string): ("Morning" | "Afternoon" | "Evening")[] {
  if (label === "All shifts") return ["Morning", "Afternoon", "Evening"];
  if (label === "Morning+Afternoon") return ["Morning", "Afternoon"];
  if (label === "Afternoon+Evening") return ["Afternoon", "Evening"];
  if (label === "Morning only") return ["Morning"];
  if (label === "Evening only") return ["Evening"];
  return ["Morning", "Afternoon", "Evening"];
}

export default function AddCrewDialog() {
  const dispatch = useAppDispatch();
  const open = useAppSelector((s) => s.crew.addDialogOpen);
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const [addMember, { isLoading }] = useAddCrewMemberMutation();

  const [name, setName] = useState("");
  const [role, setRole] = useState("Crew");
  const [dayLabel, setDayLabel] = useState("Mon–Sat");
  const [shiftLabel, setShiftLabel] = useState("All shifts");
  const [skills, setSkills] = useState<string[]>([]);

  const handleClose = () => {
    dispatch(closeAddDialog());
    setName("");
    setRole("Crew");
    setSkills([]);
  };

  const handleSubmit = async () => {
    if (!storeId || !name.trim()) return;
    await addMember({
      storeId,
      body: {
        employee_name: name.trim(),
        role,
        available_days: parseDays(dayLabel),
        available_shifts: parseShifts(shiftLabel),
        skills,
      },
    });
    handleClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ fontWeight: 700 }}>Add crew member</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "8px !important" }}>
        <Typography variant="caption" color="text.secondary">
          Add a new member to the crew roster and assign their station certifications.
        </Typography>
        <TextField label="Full name" size="small" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        <TextField label="Role" size="small" select value={role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
        </TextField>
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>Skills — certified stations</Typography>
          <SkillPicker selected={skills} onChange={setSkills} />
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField label="Days" size="small" select value={dayLabel} onChange={(e) => setDayLabel(e.target.value)} sx={{ flex: 1 }}>
            {DAY_OPTIONS.map((d) => <MenuItem key={d} value={d}>{d}</MenuItem>)}
          </TextField>
          <TextField label="Shifts" size="small" select value={shiftLabel} onChange={(e) => setShiftLabel(e.target.value)} sx={{ flex: 1 }}>
            {SHIFT_OPTIONS.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </TextField>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={!name.trim() || isLoading}>
          Add member
        </Button>
      </DialogActions>
    </Dialog>
  );
}
