# AI Crew Auto-Assignment — Design Spec

## Summary

When the manager presses "Next: Assign crew" on the Suggestion page, the system calls Ollama to intelligently assign specific employees to station/shift slots based on the AI-recommended headcounts. The Deployment grid arrives pre-filled. The manager can then tweak assignments before saving.

## Decisions

| Question | Answer |
|----------|--------|
| Review flow | AI fills grid instantly, manager tweaks before saving |
| Assignment engine | Ollama/LLM with reasoning per cell |
| Trigger point | "Next: Assign crew" button on `/suggestion` page |
| Gap handling | Assign what's available, no special edge-case handling |
| Architecture | New dedicated endpoint (`POST /api/v1/forecast/crew-assignment`) |

---

## Backend

### New Pydantic schemas (`schemas.py`)

```python
class CrewAssignmentRequest(BaseModel):
    store_id: str
    date: Date
    staffing_cells: list[StaffingCell]

class CrewAssignmentCell(BaseModel):
    station_id: str
    shift: Shift
    ai_recommended: int
    assigned_employee_ids: list[str] = Field(default_factory=list)
    reasoning: str = ""

class CrewAssignmentResponse(BaseModel):
    cells: list[CrewAssignmentCell]
    model_used: str
    generation_ms: int
    summary: str = ""
```

### New service: `crew_assignment_service.py`

Sibling to `chat_service.py`, located at `src/ai_forecaster/api/crew_assignment_service.py`.

**Responsibilities:**

1. **Collect inputs**: Receives staffing grid (`StaffingCell[]` with `ai_recommended` per station/shift) and loads employees from `DataBundle`.

2. **Pre-filter employees**: Reuses the `_available_crew` pattern from `reasoning.py` — filters by `store_id`, `available_days` (target day-of-week), `available_shifts`, `skills` (certified station IDs), and PTO overrides.

3. **Build Ollama prompt**: Structured system prompt containing:
   - Station grid: which stations need how many people per shift
   - Employee roster: ID, name, skills, available shifts, hourly rate
   - Context factors summary (weather, events, promos)
   - Instruction: assign employees to cells, each employee max one shift, prefer skill match, distribute fairly

4. **Call Ollama**: Same `call_ollama` pattern as `chat_service.py` (POST to `/api/chat`, non-streaming).

5. **Parse response**: Extract ```json block (same `_JSON_BLOCK_RE` regex as `chat_service.py`), parse into `CrewAssignmentCell[]`.

6. **Validate**: Ensure no employee appears in more than one shift. If duplicates found, keep the first occurrence, drop later ones.

7. **Fallback**: If Ollama is unreachable or returns unparseable output, fall back to a greedy rules-based assignment:
   - For each cell (ordered by shift: Morning → Afternoon → Evening):
     - Get available + skilled employees not yet assigned to any cell
     - Sort by hourly rate ascending (cheapest first)
     - Assign up to `ai_recommended` count
   - Set `model_used` to `"rules-fallback"` and `reasoning` to `"Fallback: assigned by skill match + lowest hourly rate"`

### New router: `crew_assignment.py`

Located at `src/ai_forecaster/api/routers/crew_assignment.py`.

```
POST /api/v1/forecast/crew-assignment
  Body: CrewAssignmentRequest
  Response: CrewAssignmentResponse
```

Retrieves `AppState` from `request.app.state`, calls the service, returns the response.

### Registration

Add `from .routers import crew_assignment` and `app.include_router(crew_assignment.router)` in `app.py`.

---

## Ollama Prompt

### System prompt template

```
You are an AI crew assignment optimizer for a pizza restaurant.

STATIONS NEEDING CREW:
{grid_table}

AVAILABLE EMPLOYEES:
{employees_table}

CONTEXT:
{context_summary}

RULES:
- Each employee can be assigned to AT MOST ONE shift (Morning, Afternoon, or Evening)
- Only assign employees to stations they are certified for (skills list contains the station_id)
- Only assign employees to shifts they are available for (available_shifts)
- Prefer lower hourly_rate employees when multiple candidates have equal qualifications
- Try to fill each cell up to its ai_recommended count
- If not enough qualified employees exist for a cell, assign what you can

Return a JSON array inside ```json fences with this structure:
[
  {
    "station_id": "ST_XXX",
    "shift": "Morning",
    "assigned_employee_ids": ["EMP_01", "EMP_03"],
    "reasoning": "Why these employees were chosen"
  }
]

Include ALL station/shift cells from the grid, even if no employees can be assigned (use empty array).
After the JSON block, write a brief overall summary of the assignment.
```

### User message

```
Please assign crew for {day_of_week} {date} at store {store_id}. Fill all station/shift slots optimally.
```

---

## Frontend

### New types (`types.ts`)

```typescript
export interface CrewAssignmentRequest {
  store_id: string;
  date: string;
  staffing_cells: StaffingCell[];
}

export interface CrewAssignmentCell {
  station_id: string;
  shift: Shift;
  ai_recommended: number;
  assigned_employee_ids: string[];
  reasoning: string;
}

export interface CrewAssignmentResponse {
  cells: CrewAssignmentCell[];
  model_used: string;
  generation_ms: number;
  summary: string;
}
```

### New RTK Query endpoint (`forecastApi.ts`)

```typescript
assignCrew: build.mutation<CrewAssignmentResponse, CrewAssignmentRequest>({
  query: (body) => ({
    url: "/api/v1/forecast/crew-assignment",
    method: "POST",
    body,
  }),
}),
```

### SuggestionPage flow change

Currently the "Next: Assign crew" button navigates directly to `/deploy`. New behavior:

1. `SuggestionPage` uses `useFlowNavOverride` to intercept the button press (already in place for disabling the button).

2. `onNext` handler:
   - Calls `assignCrew` mutation with `{ store_id, date, staffing_cells: staffing.cells }`
   - Sets button to loading state ("Assigning crew..." with spinner, disabled)
   - On success: dispatches `initCells` with the AI's `CrewAssignmentCell[]` (which have `assigned_employee_ids` filled), then navigates to `/deploy`
   - On error: shows an alert, navigates to `/deploy` anyway with empty assignments (existing behavior)

3. The `useFlowNavOverride` is updated to set `nextLabel` to `"Assigning crew..."` and `nextDisabled: true` during the API call.

### DeploymentPage — no changes

`DeploymentPage` already reads `cells` from Redux via `useAppSelector(s => s.deployment.cells)`. If those cells arrive with `assigned_employee_ids` pre-filled, `DeploymentGrid` renders them as chips. All existing `+ assign` / unassign functionality continues to work for manual tweaks.

### deploymentSlice — no changes

`initCells` already accepts `AssignedCell[]` with `assigned_employee_ids`. No slice modifications needed.

---

## Data Flow

```
[Suggestion Page]
  Manager presses "Next: Assign crew"
    ↓
[Frontend] POST /api/v1/forecast/crew-assignment
  { store_id, date, staffing_cells }
    ↓
[Backend] crew_assignment_service.py
  1. Load employees from DataBundle
  2. Pre-filter by day/shift/skills/overrides
  3. Build Ollama prompt with grid + employees + context
  4. Call Ollama → parse JSON response
  5. Validate (no duplicate assignments across shifts)
  6. (Fallback to greedy rules if Ollama fails)
    ↓
[Backend] Returns CrewAssignmentResponse
  { cells: [{station_id, shift, ai_recommended, assigned_employee_ids, reasoning}], model_used, generation_ms, summary }
    ↓
[Frontend] Dispatches initCells(response.cells) to Redux
  Navigates to /deploy
    ↓
[Deployment Page]
  Grid renders with pre-filled crew chips
  Manager can tweak, then save
```

---

## Files to create/modify

| File | Action |
|------|--------|
| `src/ai_forecaster/api/schemas.py` | Add `CrewAssignmentRequest`, `CrewAssignmentCell`, `CrewAssignmentResponse` |
| `src/ai_forecaster/api/crew_assignment_service.py` | **New** — Ollama prompt builder, caller, parser, fallback |
| `src/ai_forecaster/api/routers/crew_assignment.py` | **New** — POST endpoint |
| `src/ai_forecaster/api/app.py` | Register new router |
| `frontend/src/services/types.ts` | Add TS types |
| `frontend/src/services/forecastApi.ts` | Add `assignCrew` mutation |
| `frontend/src/features/suggestion/SuggestionPage.tsx` | Intercept "Next: Assign crew" → call API → init cells → navigate |

---

## Out of scope

- Per-cell reasoning display in the DeploymentGrid UI (could be a follow-up)
- Re-assign button on the Deployment page (could be a follow-up)
- Drag-and-drop crew assignment
- SQLite persistence
- Cost optimization weighting configuration
