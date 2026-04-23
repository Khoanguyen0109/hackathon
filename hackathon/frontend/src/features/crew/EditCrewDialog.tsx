import { useState, useEffect, useMemo } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { closeEditDialog } from "./crewSlice";
import { useUpdateCrewMemberMutation, useDeleteCrewMemberMutation } from "../../services/crewApi";
import SkillPicker from "./SkillPicker";
import type { Employee } from "../../services/types";

interface EditCrewDialogProps {
  crew: Employee[];
}

export default function EditCrewDialog({ crew }: EditCrewDialogProps) {
  const dispatch = useAppDispatch();
  const editingId = useAppSelector((s) => s.crew.editingEmployeeId);
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const emp = useMemo(() => crew.find((c) => c.employee_id === editingId), [crew, editingId]);
  const open = !!editingId;

  const [name, setName] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [updateMember, { isLoading: updating }] = useUpdateCrewMemberMutation();
  const [deleteMember, { isLoading: deleting }] = useDeleteCrewMemberMutation();

  useEffect(() => {
    if (emp) {
      setName(emp.employee_name);
      setSkills(emp.skills);
    }
  }, [emp]);

  const handleClose = () => dispatch(closeEditDialog());

  const handleSave = async () => {
    if (!editingId || !storeId) return;
    await updateMember({
      employeeId: editingId,
      storeId,
      body: { employee_name: name.trim(), skills },
    });
    handleClose();
  };

  const handleDelete = async () => {
    if (!editingId || !storeId) return;
    await deleteMember({ employeeId: editingId, storeId });
    handleClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ fontWeight: 700 }}>Edit crew member</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "8px !important" }}>
        <Typography variant="caption" color="text.secondary">
          Update skills, availability, or remove this member.
        </Typography>
        <TextField label="Full name" size="small" value={name} onChange={(e) => setName(e.target.value)} />
        {emp && (
          <Typography variant="caption" color="text.secondary">
            Role: {emp.role} · {emp.available_days.join(", ")} · {emp.available_shifts.join(", ")}
          </Typography>
        )}
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>Skills — certified stations</Typography>
          <SkillPicker selected={skills} onChange={setSkills} />
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, justifyContent: "space-between" }}>
        <Button color="error" onClick={handleDelete} disabled={deleting}>
          Remove
        </Button>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button onClick={handleClose}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={!name.trim() || updating}>
            Save
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
}
