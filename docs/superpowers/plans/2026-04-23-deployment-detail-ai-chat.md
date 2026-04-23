# Deployment Detail + AI Chat Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only deployment detail page accessible from history, and enhance the AI chat panel with Skip buttons, swap handling, toast feedback, and always-open default.

**Architecture:** Single new page component (`DeploymentDetailPage`) reusing the existing `DeploymentGrid` with a `readOnly` prop. Chat enhancements are localized to `ChatBubble` (Skip button, swap logic) and `DeploymentPage` (default open). All data comes from existing RTK Query hooks — zero backend changes.

**Tech Stack:** React 19, TypeScript, MUI 9, Redux Toolkit + RTK Query, react-router-dom 7, Vite 8

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `hackathon/frontend/src/features/history/DeploymentDetailPage.tsx` | Create | Read-only detail page: fetches deployment + summary, renders stats + grid |
| `hackathon/frontend/src/features/deployment/DeploymentGrid.tsx` | Modify | Add `readOnly?: boolean` prop to hide assign/delete UI |
| `hackathon/frontend/src/features/chat/ChatBubble.tsx` | Modify | Add Skip button, swap action handling, toast on Apply |
| `hackathon/frontend/src/features/deployment/DeploymentPage.tsx` | Modify | Flip `chatOpen` default to `true` |
| `hackathon/frontend/src/features/history/HistoryPage.tsx` | Modify | Add `onClick` to navigate to `/history/:id` |
| `hackathon/frontend/src/App.tsx` | Modify | Add `/history/:id` route |

---

### Task 1: Add `readOnly` prop to DeploymentGrid

**Files:**
- Modify: `hackathon/frontend/src/features/deployment/DeploymentGrid.tsx:30-34` (interface), `:36` (component signature), `:204-220` (assign button), `:192-203` (chip delete)

- [ ] **Step 1: Add `readOnly` to the props interface and destructure it**

In `hackathon/frontend/src/features/deployment/DeploymentGrid.tsx`, change the interface and component signature:

```tsx
interface DeploymentGridProps {
  cells: AssignedCell[];
  staffingCells: StaffingCell[];
  crew: Employee[];
  readOnly?: boolean;
}

export default function DeploymentGrid({ cells, staffingCells, crew, readOnly }: DeploymentGridProps) {
```

- [ ] **Step 2: Conditionally hide the assign button**

In the same file, find the `{available.length > 0 && (` block (around line 204). Wrap it to also check `!readOnly`:

```tsx
{!readOnly && available.length > 0 && (
  <Button
    size="small"
    variant="outlined"
    sx={{
      minWidth: 0,
      px: 1,
      py: 0.25,
      fontSize: 10,
      borderStyle: "dashed",
      borderRadius: "10px",
    }}
    onClick={() => {
      const next = available[0];
      if (next) dispatch(assignEmployee({ stationId: sid, shift: sh, employeeId: next.employee_id }));
    }}
  >
    + assign
  </Button>
)}
```

- [ ] **Step 3: Conditionally remove the delete handler on crew chips**

In the same file, find the `{cell.assigned_employee_ids.map((eid) => {` block (around line 192). Change the `Chip` to conditionally include `onDelete`:

```tsx
{cell.assigned_employee_ids.map((eid) => {
  const emp = empMap.get(eid);
  return (
    <Chip
      key={eid}
      label={emp ? emp.employee_name.split(" ").map((w: string) => w[0]).join("") : eid.slice(0, 4)}
      size="small"
      {...(!readOnly && {
        onDelete: () => dispatch(unassignEmployee({ stationId: sid, shift: sh, employeeId: eid })),
      })}
      sx={{ fontSize: 10, fontWeight: 600, height: 24 }}
    />
  );
})}
```

- [ ] **Step 4: Verify the grid renders correctly in both modes**

Run the dev server and check:
```bash
cd hackathon/frontend && npm run dev
```
- Navigate to `/deploy` (after generating a suggestion) — grid should work as before (assign buttons visible, chips deletable)
- The `readOnly` prop is not passed yet, so this is a regression check

- [ ] **Step 5: Commit**

```bash
git add hackathon/frontend/src/features/deployment/DeploymentGrid.tsx
git commit -m "feat: add readOnly prop to DeploymentGrid to hide assign/delete UI"
```

---

### Task 2: Create DeploymentDetailPage

**Files:**
- Create: `hackathon/frontend/src/features/history/DeploymentDetailPage.tsx`

- [ ] **Step 1: Create the DeploymentDetailPage component**

Create `hackathon/frontend/src/features/history/DeploymentDetailPage.tsx`:

```tsx
import { useParams, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import IconButton from "@mui/material/IconButton";
import Skeleton from "@mui/material/Skeleton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useGetDeploymentQuery, useGetDeploymentSummaryQuery } from "../../services/deploymentApi";
import { useListCrewQuery } from "../../services/crewApi";
import DeploymentGrid from "../deployment/DeploymentGrid";

export default function DeploymentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: deployment, isLoading, isError } = useGetDeploymentQuery(id ?? "", { skip: !id });
  const { data: summary } = useGetDeploymentSummaryQuery(id ?? "", { skip: !id });
  const { data: crew } = useListCrewQuery(deployment?.store_id ?? "", { skip: !deployment?.store_id });

  if (isLoading) {
    return (
      <Box>
        <Skeleton variant="rounded" height={40} sx={{ mb: 2, borderRadius: "16px" }} />
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2, mb: 2.5 }}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} variant="rounded" height={90} sx={{ borderRadius: "16px" }} />
          ))}
        </Box>
        <Skeleton variant="rounded" height={300} sx={{ borderRadius: "16px" }} />
      </Box>
    );
  }

  if (isError || !deployment) {
    return (
      <Box sx={{ py: 8, textAlign: "center" }}>
        <Typography color="text.secondary">Deployment not found.</Typography>
      </Box>
    );
  }

  const cells = deployment.cells;
  const totalRec = cells.reduce((s, c) => s + c.ai_recommended, 0);
  const totalAssigned = cells.reduce((s, c) => s + c.assigned_employee_ids.length, 0);
  const gaps = totalRec - totalAssigned;
  const uniqueCrew = new Set(cells.flatMap((c) => c.assigned_employee_ids)).size;
  const coveragePct = totalRec > 0 ? Math.round((totalAssigned / totalRec) * 100) : 0;

  const staffingCells = cells.map((c) => ({
    station_id: c.station_id,
    station_name: c.station_id,
    shift: c.shift,
    ai_recommended: c.ai_recommended,
    reason_short: "",
    confidence: "medium" as const,
    factors: [],
    rules_applied: [],
    channel_note: "",
    crew_note: "",
    reason_rows: [],
  }));

  return (
    <Box>
      <Box sx={{ mb: 3, display: "flex", alignItems: "center", gap: 1.5 }}>
        <IconButton onClick={() => navigate("/history")} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h6" sx={{ textAlign: "left" }}>
            Deployment chart — {deployment.date}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Saved {new Date(deployment.created_at).toLocaleString()}
          </Typography>
        </Box>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2, mb: 2.5 }}>
        <StatCard value={summary?.total_assigned ?? totalAssigned} label="Slots assigned" color="success.main" />
        <StatCard value={summary?.gap ?? gaps} label="Gaps vs AI rec" color="warning.main" />
        <StatCard value={uniqueCrew} label="Crew deployed" color="text.primary" />
        <StatCard value={`${summary?.coverage_pct ?? coveragePct}%`} label="AI rec coverage" color="primary.main" />
      </Box>

      <DeploymentGrid cells={cells} staffingCells={staffingCells} crew={crew ?? []} readOnly />
    </Box>
  );
}

function StatCard({ value, label, color }: { value: number | string; label: string; color: string }) {
  return (
    <Card>
      <CardContent>
        <Typography sx={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, fontWeight: 500, display: "block" }}>
          {label}
        </Typography>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Verify the file has no TypeScript errors**

```bash
cd hackathon/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: No errors related to `DeploymentDetailPage.tsx` (there may be pre-existing warnings).

- [ ] **Step 3: Commit**

```bash
git add hackathon/frontend/src/features/history/DeploymentDetailPage.tsx
git commit -m "feat: add DeploymentDetailPage with read-only grid and summary stats"
```

---

### Task 3: Wire History page click-through and route

**Files:**
- Modify: `hackathon/frontend/src/features/history/HistoryPage.tsx:52-76` (row onClick)
- Modify: `hackathon/frontend/src/App.tsx:13,26` (import + route)

- [ ] **Step 1: Add onClick to history deployment rows**

In `hackathon/frontend/src/features/history/HistoryPage.tsx`, find the `<Box key={d.deployment_id}` element (around line 52). Add an `onClick` handler:

```tsx
<Box
  key={d.deployment_id}
  onClick={() => navigate(`/history/${d.deployment_id}`)}
  sx={(t) => {
```

No other changes to this block — the `cursor: "pointer"` style already exists.

- [ ] **Step 2: Add the route and import in App.tsx**

In `hackathon/frontend/src/App.tsx`, add the import after the existing `HistoryPage` import (line 13):

```tsx
import HistoryPage from "./features/history/HistoryPage";
import DeploymentDetailPage from "./features/history/DeploymentDetailPage";
```

Then add the route inside the `<Route element={<AppLayout />}>` block, after the `/history` route (around line 27):

```tsx
<Route path="/history" element={<HistoryPage />} />
<Route path="/history/:id" element={<DeploymentDetailPage />} />
```

- [ ] **Step 3: Verify navigation works**

```bash
cd hackathon/frontend && npm run dev
```

1. Navigate to `/history`
2. If there are saved deployments, click one — should navigate to `/history/{id}` and show the detail page with stats + read-only grid
3. Click the back arrow — should return to `/history`
4. If no saved deployments, go through the flow: generate suggestion → deploy → save → go to history → click the row

- [ ] **Step 4: Commit**

```bash
git add hackathon/frontend/src/features/history/HistoryPage.tsx hackathon/frontend/src/App.tsx
git commit -m "feat: wire history row click-through to deployment detail page"
```

---

### Task 4: Enhance ChatBubble with Skip button and swap handling

**Files:**
- Modify: `hackathon/frontend/src/features/chat/ChatBubble.tsx:14-91` (ActionCard component)

- [ ] **Step 1: Add `skipped` state, Skip button, and toast to ActionCard**

In `hackathon/frontend/src/features/chat/ChatBubble.tsx`, replace the entire `ActionCard` function (lines 14–91) with:

```tsx
function ActionCard({
  action,
  messageId,
  actionIndex,
}: {
  action: ChatAction & { applied?: boolean };
  messageId: string;
  actionIndex: number;
}) {
  const dispatch = useAppDispatch();
  const [status, setStatus] = useState<"pending" | "applied" | "skipped">(
    action.applied ? "applied" : "pending"
  );
  const [toast, setToast] = useState(false);

  const employeeLabel = action.employee_name || action.employee_id;
  const stationLabel = action.station_name || action.station_id;

  const handleApply = () => {
    if (action.type === "assign") {
      dispatch(
        assignEmployee({
          stationId: action.station_id,
          shift: action.shift,
          employeeId: action.employee_id,
        })
      );
    } else if (action.type === "unassign") {
      dispatch(
        unassignEmployee({
          stationId: action.station_id,
          shift: action.shift,
          employeeId: action.employee_id,
        })
      );
    } else if (action.type === "swap") {
      dispatch(
        assignEmployee({
          stationId: action.station_id,
          shift: action.shift,
          employeeId: action.employee_id,
        })
      );
    }
    dispatch(markActionApplied({ messageId, actionIndex }));
    setStatus("applied");
    setToast(true);
  };

  const handleSkip = () => {
    setStatus("skipped");
  };

  const icon =
    action.type === "unassign" ? (
      <PersonRemoveIcon sx={{ fontSize: 14 }} />
    ) : action.type === "swap" ? (
      <SwapHorizIcon sx={{ fontSize: 14 }} />
    ) : (
      <PersonAddIcon sx={{ fontSize: 14 }} />
    );

  const typeLabel = action.type === "swap" ? "swap" : action.type;
  const typeColor = action.type === "unassign" ? "warning" : action.type === "swap" ? "info" : "primary";

  const toastMessage =
    action.type === "unassign"
      ? `Unassigned ${employeeLabel} from ${stationLabel}`
      : action.type === "swap"
        ? `Swapped ${employeeLabel} into ${stationLabel}`
        : `Assigned ${employeeLabel} to ${stationLabel}`;

  if (status === "skipped") {
    return (
      <Box
        sx={(t) => ({
          mt: 0.75,
          p: 1.25,
          borderRadius: "14px",
          bgcolor: t.palette.mode === "dark" ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)",
          border: 1,
          borderColor: "divider",
          opacity: 0.5,
        })}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
          <Typography sx={{ fontSize: 11, color: "text.secondary", fontStyle: "italic" }}>
            Skipped: {employeeLabel} → {stationLabel}
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <>
      <Box
        sx={(t) => ({
          mt: 0.75,
          p: 1.25,
          borderRadius: "14px",
          bgcolor:
            status === "applied"
              ? t.palette.mode === "dark"
                ? "rgba(48,209,88,0.08)"
                : "success.light"
              : t.palette.mode === "dark"
                ? "rgba(255,255,255,0.04)"
                : "background.paper",
          border: 1,
          borderColor: status === "applied" ? "success.main" : "divider",
          transition: "all 0.2s",
        })}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
          <Chip
            label={typeLabel}
            size="small"
            color={typeColor}
            sx={{ fontSize: 9, height: 20, borderRadius: "10px" }}
          />
          <Typography sx={{ fontSize: 11, fontWeight: 600, flex: 1 }}>
            {employeeLabel} → {stationLabel} ({action.shift})
          </Typography>
        </Box>
        <Typography sx={{ fontSize: 10, color: "text.secondary", mb: 0.75 }}>
          {action.reason}
        </Typography>
        <Box sx={{ display: "flex", gap: 0.75 }}>
          <Button
            size="small"
            variant={status === "applied" ? "outlined" : "contained"}
            color={status === "applied" ? "success" : "primary"}
            disabled={status === "applied"}
            onClick={handleApply}
            startIcon={status === "applied" ? <CheckIcon sx={{ fontSize: 12 }} /> : icon}
            sx={{ fontSize: 10, py: 0.25, px: 1.5, minHeight: 24 }}
          >
            {status === "applied" ? "Applied" : "Apply"}
          </Button>
          {status === "pending" && (
            <Button
              size="small"
              variant="outlined"
              color="inherit"
              onClick={handleSkip}
              sx={{ fontSize: 10, py: 0.25, px: 1.5, minHeight: 24, color: "text.secondary" }}
            >
              Skip
            </Button>
          )}
        </Box>
      </Box>
      <Snackbar open={toast} autoHideDuration={2500} onClose={() => setToast(false)}>
        <Alert severity="success" variant="filled" sx={{ borderRadius: "20px", fontSize: 12 }}>
          {toastMessage}
        </Alert>
      </Snackbar>
    </>
  );
}
```

- [ ] **Step 2: Add the new imports**

At the top of `hackathon/frontend/src/features/chat/ChatBubble.tsx`, add the missing imports alongside existing ones:

```tsx
import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import CheckIcon from "@mui/icons-material/Check";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import PersonRemoveIcon from "@mui/icons-material/PersonRemove";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import type { ChatMessage, ChatAction } from "../../services/types";
import { useAppDispatch } from "../../app/hooks";
import { assignEmployee, unassignEmployee } from "../deployment/deploymentSlice";
import { markActionApplied } from "./chatSlice";
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd hackathon/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: No errors related to `ChatBubble.tsx`.

- [ ] **Step 4: Commit**

```bash
git add hackathon/frontend/src/features/chat/ChatBubble.tsx
git commit -m "feat: add Skip button, swap handling, and skipped state to chat action cards"
```

---

### Task 5: Set chat panel open by default on DeploymentPage

**Files:**
- Modify: `hackathon/frontend/src/features/deployment/DeploymentPage.tsx:30`

- [ ] **Step 1: Change `chatOpen` default to `true`**

In `hackathon/frontend/src/features/deployment/DeploymentPage.tsx`, find line 30:

```tsx
const [chatOpen, setChatOpen] = useState(false);
```

Change to:

```tsx
const [chatOpen, setChatOpen] = useState(true);
```

- [ ] **Step 2: Verify the deploy page loads with chat open**

```bash
cd hackathon/frontend && npm run dev
```

Navigate to `/deploy` (after generating a suggestion). The AI chat panel should be visible immediately without clicking the toggle button. Clicking "AI Assistant" button should collapse it.

- [ ] **Step 3: Commit**

```bash
git add hackathon/frontend/src/features/deployment/DeploymentPage.tsx
git commit -m "feat: open AI chat panel by default on deployment page"
```

---

### Task 6: Final integration verification

- [ ] **Step 1: Run TypeScript check on the entire frontend**

```bash
cd hackathon/frontend && npx tsc --noEmit
```

Expected: No new errors introduced.

- [ ] **Step 2: Run lint check**

```bash
cd hackathon/frontend && npx eslint src/ --max-warnings=0 2>&1 | tail -20
```

Fix any new lint errors.

- [ ] **Step 3: End-to-end walkthrough**

Start the dev server:
```bash
cd hackathon/frontend && npm run dev
```

Full flow verification:

1. **Home (/)** — Generate AI suggestion (click "Generate staffing")
2. **Deploy (/deploy)** — Chat panel should be open by default. Grid should show AI recommendations with assign buttons. Toggle chat closed and open again.
3. **Deploy** — Click "+ assign" to add crew. Use chat to ask "Who should I assign?" — AI response should include action cards with Apply and Skip buttons. Click Apply on one → grid updates, button shows "✓ Applied". Click Skip on another → card fades to "Skipped" state.
4. **Deploy** — Click "Save deployment chart" → navigates to summary.
5. **History (/history)** — Saved chart appears in the list. Click the row → navigates to `/history/{id}`.
6. **Detail (/history/:id)** — Shows header with date + back arrow, 4 stat cards, read-only grid (no assign buttons, no delete on chips). Click back arrow → returns to `/history`.

- [ ] **Step 4: Final commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix: address integration issues from final verification"
```
