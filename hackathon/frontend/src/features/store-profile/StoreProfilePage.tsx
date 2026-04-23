import { useEffect } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Skeleton from "@mui/material/Skeleton";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { selectStore } from "./storeProfileSlice";
import { useListStoresQuery } from "../../services/storeApi";
import StationList from "./StationList";
import TaskList from "./TaskList";

export default function StoreProfilePage() {
  const dispatch = useAppDispatch();
  const selectedStoreId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const { data: stores, isLoading } = useListStoresQuery();

  useEffect(() => {
    if (!selectedStoreId && stores?.length) {
      dispatch(selectStore(stores[0].store_id));
    }
  }, [stores, selectedStoreId, dispatch]);

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ textAlign: "left" }}>Store profile — stations & tasks</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Configure the operational stations and secondary tasks for your store. These become the rows in your deployment chart.
        </Typography>
      </Box>

      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <FormControl size="small" sx={{ minWidth: 280 }}>
            <InputLabel>Select store</InputLabel>
            <Select
              value={selectedStoreId ?? ""}
              label="Select store"
              onChange={(e) => dispatch(selectStore(e.target.value))}
              sx={{ borderRadius: "16px" }}
            >
              {isLoading && <MenuItem value="">Loading...</MenuItem>}
              {stores?.map((s) => (
                <MenuItem key={s.store_id} value={s.store_id}>
                  {s.store_name} — {s.city}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </CardContent>
      </Card>

      {isLoading ? (
        <Skeleton variant="rounded" height={300} sx={{ borderRadius: "28px" }} />
      ) : (
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Card sx={{ flex: "1 1 300px" }}>
            <CardContent>
              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                Stations
              </Typography>
              <StationList />
            </CardContent>
          </Card>
          <Card sx={{ flex: "1 1 260px" }}>
            <CardContent>
              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                Secondary tasks
              </Typography>
              <TaskList />
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
}
