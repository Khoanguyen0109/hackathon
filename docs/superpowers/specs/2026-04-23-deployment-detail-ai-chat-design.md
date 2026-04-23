# Deployment Chart Detail + AI Chat Actions — Design Spec

## Overview

Two features for the ByteCoach Manager AI Deployment Chart application:

1. **Deployment Chart Detail Page** — a read-only detail view for saved deployment charts, accessible from the History page.
2. **Enhanced AI Chat with Actionable Suggestions** — the existing chat panel on the Deployment page becomes always-open by default and renders per-action Apply/Skip buttons when the AI suggests crew assignments.

## Goals

- Let managers review past deployment charts with full grid + summary stats
- Give managers fine-grained control over AI-suggested crew assignments via inline Apply/Skip buttons
- Zero backend changes — all required API endpoints already exist

## Non-Goals

- Editing past deployments from the detail page (read-only only)
- Persisting chat action states (applied/skipped) across sessions
- Adding new AI models or changing the Ollama-based chat backend

---

## Feature 1: Deployment Chart Detail Page

### Route

`/history/:id` — new route nested under the existing `AppLayout`.

### Entry Point

From `HistoryPage` (`/history`): clicking any saved deployment row navigates to `/history/{deployment_id}`.

### Data Fetching

Uses existing RTK Query hooks:

| Hook | Endpoint | Purpose |
|------|----------|---------|
| `useGetDeploymentQuery(id)` | `GET /api/v1/deployments/{id}` | Deployment with cells |
| `useGetDeploymentSummaryQuery(id)` | `GET /api/v1/deployments/{id}/summary` | Aggregate stats |
| `useListCrewQuery(storeId)` | `GET /api/v1/stores/{store_id}/crew` | Resolve employee IDs → names |

### Layout (top to bottom)

1. **Header bar**
   - Title: "Deployment chart — {date}"
   - Back button (IconButton with ArrowBack) → navigates to `/history`
   - Date + day-of-week subtitle

2. **Summary stats row** — 4 `StatCard` components (reuse pattern from `SummaryPage`):
   - Slots assigned (total assigned employee IDs across all cells)
   - Gaps vs AI rec (total AI recommended − total assigned)
   - Crew deployed (unique employee IDs)
   - AI rec coverage % (assigned / recommended × 100)

3. **Read-only deployment grid**
   - Reuses `DeploymentGrid` component with a new `readOnly` prop
   - When `readOnly=true`:
     - Hides all "+ assign" buttons
     - Hides delete (×) icons on crew chips (renders plain chips instead)
     - No dispatch calls for assign/unassign
   - Shows: AI rec badges, rush hour indicators, met/short/over status chips
   - Crew names resolved from the crew query

4. **Loading / error states**
   - Skeleton placeholders while fetching
   - Error message if deployment not found (404)

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `features/history/DeploymentDetailPage.tsx` | Create | New page component |
| `features/deployment/DeploymentGrid.tsx` | Modify | Add optional `readOnly?: boolean` prop |
| `features/history/HistoryPage.tsx` | Modify | Add `onClick` handler to navigate to detail |
| `App.tsx` | Modify | Add `/history/:id` route + import |

---

## Feature 2: Enhanced AI Chat with Action Buttons

### 2a. Chat Panel Always Open by Default

On `DeploymentPage`, change the `chatOpen` state initial value from `false` to `true`. The existing toggle button continues to work for collapsing/expanding.

### 2b. Actionable Chat Bubbles

When an AI chat message includes `actions: ChatAction[]`, the `ChatBubble` component renders action cards below the message text.

#### Action Card Layout

Each `ChatAction` renders as a small card within the bubble:

- **Icon** based on action type: assign (➕), unassign (➖), swap (🔄)
- **Primary text**: "{action type} {employee_name} → {station_name}"
- **Secondary text**: "{shift} shift"
- **Reason text**: the `reason` field from `ChatAction`
- **Two buttons**: "Apply" (contained, primary) and "Skip" (outlined)

#### Action Button Behavior

Each action card tracks its own state via `useState` in `ChatBubble`:

| State | Apply Button | Skip Button |
|-------|-------------|-------------|
| `pending` | Enabled, "Apply" | Enabled, "Skip" |
| `applied` | Disabled, "✓ Applied" (success color) | Hidden |
| `skipped` | Hidden | Disabled, "Skipped" (muted) |

**On Apply click:**
- **assign** action → dispatch `assignEmployee({ stationId, shift, employeeId })`
- **unassign** action → dispatch `unassignEmployee({ stationId, shift, employeeId })`
- **swap** action → the backend currently sends `swap` with a single `employee_id`. Implementation: treat swap as "assign this employee into the slot." If the slot is at capacity (assigned >= ai_recommended), unassign the first existing employee, then assign the new one. This avoids needing a schema change.
- Show toast: "Assigned {name} to {station}" (or "Unassigned" / "Swapped")
- Set action state to `applied`

**On Skip click:**
- Set action state to `skipped`
- No Redux dispatch, no grid change

#### State Persistence

Action states (pending/applied/skipped) are ephemeral — stored in component-level `useState`, not Redux. Navigating away and back resets them to `pending`. This is acceptable because:
- The grid state (Redux) is the source of truth
- Re-applying an already-assigned employee is a no-op (the reducer checks for duplicates)

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `features/chat/ChatBubble.tsx` | Modify | Add action card rendering with Apply/Skip buttons and local state |
| `features/deployment/DeploymentPage.tsx` | Modify | Change `chatOpen` default to `true` |

---

## Complete File Change Summary

| File | Action |
|------|--------|
| `features/history/DeploymentDetailPage.tsx` | **Create** |
| `features/deployment/DeploymentGrid.tsx` | Modify |
| `features/chat/ChatBubble.tsx` | Modify |
| `features/deployment/DeploymentPage.tsx` | Modify |
| `features/history/HistoryPage.tsx` | Modify |
| `App.tsx` | Modify |

**Total: 1 new file, 5 modified files. Zero backend changes.**

---

## Existing API Endpoints Used (no changes needed)

| Method | Path | Used By |
|--------|------|---------|
| `GET` | `/api/v1/deployments` | HistoryPage (existing) |
| `GET` | `/api/v1/deployments/{id}` | DeploymentDetailPage (new usage) |
| `GET` | `/api/v1/deployments/{id}/summary` | DeploymentDetailPage (new usage) |
| `GET` | `/api/v1/stores/{store_id}/crew` | DeploymentDetailPage (new usage) |
| `POST` | `/api/v1/chat` | ChatPanel (existing, returns actions) |

## Tech Stack (unchanged)

- React 19, TypeScript, Vite 8
- MUI 9 (Material UI)
- Redux Toolkit + RTK Query
- react-router-dom 7
