import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Skeleton from "@mui/material/Skeleton";
import { useAppSelector, useAppDispatch } from "../../app/hooks";
import { setTargetDate, setContext } from "./suggestionSlice";
import { useLazyGetContextQuery } from "../../services/contextApi";
import FactorBadge from "./FactorBadge";

export default function DateContextBar() {
  const dispatch = useAppDispatch();
  const storeId = useAppSelector((s) => s.storeProfile.selectedStoreId);
  const targetDate = useAppSelector((s) => s.suggestion.targetDate);
  const context = useAppSelector((s) => s.suggestion.context);
  const [fetchContext, { isFetching }] = useLazyGetContextQuery();
  const dateRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (storeId && targetDate) {
      fetchContext({ storeId, date: targetDate })
        .unwrap()
        .then((data) => dispatch(setContext(data)))
        .catch(() => {});
    }
  }, [storeId, targetDate, fetchContext, dispatch]);

  return (
    <Card sx={{ mb: 2.5 }}>
      <CardContent>
        <Typography variant="subtitle2" sx={{ mb: 1.5 }}>Target date & context</Typography>
        <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", mb: 2 }}>
          <TextField
            type="date"
            size="small"
            label="Date"
            value={targetDate}
            onChange={(e) => dispatch(setTargetDate(e.target.value))}
            inputRef={dateRef}
            onClick={() => dateRef.current?.showPicker?.()}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ width: 180, cursor: "pointer", "& input": { cursor: "pointer" } }}
          />
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
          External factors
        </Typography>
        {isFetching ? (
          <Box sx={{ display: "flex", gap: 1.5 }}>
            {[1, 2, 3].map((i) => <Skeleton key={i} variant="rounded" width={220} height={140} sx={{ borderRadius: "20px" }} />)}
          </Box>
        ) : context ? (
          <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
            {context.factors.map((f, i) => (
              <FactorBadge key={i} factor={f} />
            ))}
          </Box>
        ) : (
          <Typography variant="caption" color="text.disabled">
            Select a date to fetch external factors
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
