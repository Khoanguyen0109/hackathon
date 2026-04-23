# AI-Driven Store Deployment Chart

**Initiative Name:** AI-Driven Store Deployment Chart

**Jira Link(s):** TBD

**Lead Contacts:** TBD

**Timeline (quarter):** Q2 2026 (Hackathon)

---

## 1 - Overview

### 1.1 - Background

Store managers in the Restaurant Manager App currently build deployment charts — the shift-by-shift assignment of crew members to stations and secondary tasks — based on intuition and personal experience. There is no data-driven tooling to help them decide how many people should be at the grill, drive-through, or front counter during a Saturday lunch rush versus a quiet Tuesday morning.

The Restaurant Profile already allows managers to configure stations (e.g., Grill, Fryer, Front Counter, Drive-Through) and secondary tasks (e.g., Cleaning, Restocking, Prep) for their store. However, the step from "what stations exist" to "who should be where, and when" is entirely manual.

This initiative introduces an AI-powered prediction layer that ingests external context — weather forecasts, local events, company promotions, and holidays — to suggest optimal staffing levels per station per shift. The manager then assigns specific crew members to fill those AI-recommended slots, combining data-driven guidance with human judgment.

### 1.2 - Business Need

From the store manager's perspective:

- **Time waste:** Building a deployment chart from scratch each week takes significant time, especially when the manager must mentally factor in upcoming weather, local events, and promotions.
- **Inconsistent quality:** Deployment decisions based on gut feeling vary widely between managers. A new manager may under-staff drive-through during a rainy day (when drive-through demand spikes), while an experienced manager would know to add staff.
- **Missed revenue & poor service:** Under-staffing high-demand stations leads to longer wait times and lost customers. Over-staffing wastes labor costs.
- **No scenario planning:** Managers cannot easily compare "what if it rains?" vs. "what if there's a local football game?" to prepare contingency plans.

### 1.3 - Scope, Goals, Objectives

**Scope:**

1. **Store Profile Setup** — Managers configure their store's stations, secondary tasks, and crew members (with skills and availability) within the Manager App.
2. **AI Prediction Engine** — A local LLM (via Ollama) acts as a reasoning engine, receiving store context and external factors to produce staffing-level recommendations per station per shift.
3. **Deployment Chart UI** — A shift-based interface where the AI's suggestions are displayed as staffing targets, and the manager drag-assigns individual crew members to stations and tasks.

**Goals:**

- Reduce deployment chart creation time by providing pre-filled AI suggestions.
- Improve staffing accuracy by incorporating weather, events, holidays, and company promotions.
- Give managers a clear, visual deployment chart with AI-recommended vs. manually-assigned states.

**Objectives:**

- Deliver a working end-to-end prototype: store setup → AI suggestion → deployment chart.
- Demonstrate measurable improvement in staffing allocation accuracy using simulated scenarios.

### 1.4 - Success Criteria

Upon completion, the end user (store manager) should be able to:

1. Configure their store's stations, secondary tasks, and crew members in the Manager App.
2. Select a date and have the system automatically fetch relevant external factors (weather, events, holidays).
3. Receive AI-generated staffing-level suggestions per station per shift (Morning, Afternoon, Evening).
4. **Read the AI's reasoning for every suggestion** — each station × shift cell must include a plain-language explanation of *why* the AI recommends that headcount (e.g., "Rain +5% delivery → need extra driver at Dispatch", "Saturday + World Cup → Dine-in peak, add 1 to Front Counter"). Reasoning must cite the specific external factors and prediction rules that influenced the number.
5. View the suggestions in a shift-based deployment chart grid.
6. Assign specific crew members to each station/task slot by dragging or selecting from the available pool.
7. Override or adjust AI suggestions before finalizing the chart.
8. **Refine AI suggestions through conversational chat** — a side-panel chat on the suggestion screen lets managers add context (e.g., crew absences), ask "why" for any cell, directly override values, and run "what-if" scenarios (e.g., "What if rain stops?"), with the grid updating in real time.
9. Save and review the finalized deployment chart.

### 1.5 - AI Reasoning Requirement (Key Requirement)

Every AI staffing suggestion **must** include a human-readable reasoning trace. This is a core product requirement, not optional.

**What the reasoning must contain:**

| Element | Description | Example |
|---------|-------------|---------|
| **Active factors** | Which external events are influencing this cell | "Rain, Saturday" |
| **Rule citation** | Which prediction rules fired and the resulting demand delta | "Rain → Delivery +5%, Saturday → Delivery +6% = +11% total" |
| **Channel mapping** | How the channel-level delta translates to this specific station | "Delivery +11% → Dispatch station needs +1 staff to handle volume" |
| **Crew constraint** | Whether available crew limits the recommendation | "Ideally 4, but only 3 drivers available → capped at 3" |
| **Confidence signal** | How much the AI is extrapolating vs. applying known rules | "High confidence (rule-based)" or "Medium (AI inference — no explicit rule for World Cup)" |

**Why this matters:**

- **Trust:** Managers will not follow AI suggestions they cannot understand. Transparent reasoning builds trust and adoption.
- **Override decisions:** When a manager disagrees with the AI, the reasoning helps them decide *which part* they disagree with (e.g., "I know this local match won't affect us because it's on the other side of town").
- **Learning loop:** Stored reasoning enables post-hoc analysis of where the AI was right vs. wrong, improving future predictions.
- **Auditability:** Operations leadership can review why staffing decisions were made on a specific day.

**UI treatment:**

- Each grid cell shows the headcount prominently with a short 1-line reason visible by default (e.g., "Rain + Sat peak").
- Hovering or clicking the cell expands the full reasoning trace with factor breakdown, rule citations, and confidence level.
- The AI summary banner below the grid provides an overall narrative (e.g., "Rainy Saturday drives Delivery +11% — prioritize Dispatch and Makeline. Dine-in near-neutral at +3%").

---

## 2 - Business Use Cases

### Use Case 1: Store Profile Configuration

#### 2.1 - Value

Managers can digitally define their store's operational structure (stations, tasks, crew) in one place, creating the foundation for AI-driven deployment planning. This replaces paper-based or spreadsheet-based tracking.

#### 2.2 - Actors

- **Store Manager**: Configures stations, secondary tasks, and crew members for their store. Has full read/write access to their store's profile.

#### 2.3 - Assumptions and Pre-conditions

- The store already exists in the system (`t_store`).
- Station and task master data is available from the existing schema (`t_station`, `t_station_area`).
- The manager is authenticated and authorized for their store.

#### 2.4 - Post-conditions & Security Considerations

- Store stations (`t_store_station`), tasks (`t_store_task`), and crew members are persisted.
- Changes to the store profile are audit-logged (`created_by`, `updated_by`, timestamps).
- A manager can only modify their own store's profile.
- Crew member personal data (name, contact) must be handled per data privacy standards.

---

### Use Case 2: AI-Driven Staffing Suggestion

#### 2.1 - Value

Managers receive data-informed staffing recommendations instead of relying on gut feeling. The AI considers factors the manager may overlook (e.g., a local event coinciding with bad weather), leading to better-prepared shifts.

#### 2.2 - Actors

- **Store Manager**: Selects a target date and triggers the AI suggestion.
- **AI Prediction Engine**: Processes store context + external factors and returns staffing recommendations.

#### 2.3 - Assumptions and Pre-conditions

- The store profile (stations, tasks, crew) is already configured.
- External data sources (weather, events, holidays) are available (simulated for hackathon).
- Ollama is running locally with a suitable LLM model loaded.

#### 2.4 - Post-conditions & Security Considerations

- AI suggestions are returned as structured data: for each shift × station, a recommended headcount and reasoning.
- Suggestions are non-binding — they are recommendations only.
- No customer or employee personal data is sent to the LLM. Only store operational context (station names, task names, crew count, skills) is included in prompts.
- AI responses are validated and sanitized before display.

---

### Use Case 3: Deployment Chart Creation & Assignment

#### 2.1 - Value

Managers get a visual, interactive deployment chart pre-populated with AI suggestions. They retain full control to assign specific people, adjust headcounts, and finalize the plan. This combines AI efficiency with human judgment.

#### 2.2 - Actors

- **Store Manager**: Reviews AI suggestions, assigns crew members to stations/tasks per shift, finalizes the deployment chart.

#### 2.3 - Assumptions and Pre-conditions

- AI suggestions have been generated for the selected date.
- Crew member availability for the target date is known.
- The store profile has at least one station and one crew member configured.

#### 2.4 - Post-conditions & Security Considerations

- The finalized deployment chart is saved and can be retrieved later.
- The chart records both the AI suggestion and the manager's final assignment for comparison/learning.
- Only authorized managers can create or modify deployment charts for their store.

---

## 3 - User Interface

### 3.1 - Mockups

**Screen 1: Store Profile — Stations & Tasks Setup**

- List view of configured stations (from `t_store_station`) with toggle for active/inactive.
- List view of secondary tasks (from `t_store_task`) with add/edit/delete.
- Each station shows: name, area, quantity (number of positions), active status.

**Screen 2: Store Profile — Crew Management**

- List/card view of crew members with name, role, skills (which stations they're certified for), and availability pattern.
- Add/edit/remove crew members.
- Skill tags linked to stations (e.g., "Grill Certified", "Drive-Through Trained").

**Screen 3: Deployment Chart — AI Suggestion View**

- Date picker at the top to select the target date.
- Grid layout: Rows = Stations + Secondary Tasks, Columns = Shifts (Morning, Afternoon, Evening).
- Each cell shows the AI-recommended headcount with a brief reasoning tooltip (e.g., "2 staff — rainy day increases drive-through demand").
- "Generate Suggestion" button that triggers the AI engine.
- Visual indicators for external factors: weather icon, event badge, holiday marker.

**Screen 4: Deployment Chart — Assignment View**

- Same grid as above, but each cell is expandable.
- Available crew member pool shown on the side, filterable by skills.
- Drag-and-drop or click-to-assign crew members into station/shift cells.
- Visual warning when a cell is under-staffed vs. AI recommendation.
- "Save Deployment" button to finalize.

*Detailed mockups to be created during implementation.*

### 3.2 - Normal Flow of Operation (and any Exceptions)

**Normal Flow:**

1. Manager opens the Store Profile and configures stations, tasks, and crew (one-time setup, editable anytime).
2. Manager navigates to the Deployment Chart screen.
3. Manager selects a target date using the date picker.
4. System fetches external factors (weather forecast, local events, holidays, company promotions) for that date and store location.
5. Manager clicks "Generate Suggestion."
6. System sends store context + external factors to the AI Prediction Engine.
7. AI returns staffing recommendations per station per shift.
8. System displays the recommendations in the grid with reasoning tooltips.
9. Manager reviews the suggestions and assigns specific crew members to each slot.
10. Manager adjusts headcounts if they disagree with the AI.
11. Manager saves the finalized deployment chart.

**Exceptions:**

- **AI service unavailable:** System displays a warning and allows the manager to manually fill the chart without AI suggestions.
- **Insufficient crew:** If total available crew is less than total AI-recommended headcount, the system highlights the gap and suggests prioritization.
- **No external data:** If weather/event APIs fail, the AI proceeds with available data and notes the missing context in its reasoning.

### 3.3 - Display Constraints

- **Responsive design:** Must work on desktop (primary) and tablet (secondary — managers may use tablets in-store).
- **Language:** English for hackathon. Architecture should support i18n for future localization.
- **Accessibility:** Follow WCAG 2.1 AA guidelines for color contrast, keyboard navigation, and screen reader support where feasible within hackathon timeline.

---

## 4 - External Interfaces

### 4.1 - Internal Interfaces

| Service | Purpose |
|---------|---------|
| **Python API (FastAPI)** | Unified backend — serves store/station/task/crew data via REST endpoints, handles AI prediction logic (prompt construction, Ollama calls, response parsing), and stores deployment charts. Consolidating the API and AI layers into a single Python service reduces complexity and eliminates inter-service communication overhead. |
| **SQLite Database** | Stores all application data (stores, stations, tasks, crew, deployment charts). Used for hackathon simplicity. Accessed via Python's built-in `sqlite3` or SQLAlchemy. |

### 4.2 - 3rd Party Interfaces

| Interface | Purpose | Hackathon Approach |
|-----------|---------|-------------------|
| **Ollama (Local LLM)** | AI reasoning engine for staffing predictions. | Runs locally. Model TBD (e.g., Llama 3, Mistral). |
| **Weather API** | Provides weather forecasts for the store's location and target date. | Simulated — pre-seeded from `simulated_event_data_and_rules.xlsx`. |
| **Events API** | Provides local event information (sports games). | Simulated — World Cup and SEA Games data pre-seeded. |
| **Holiday Calendar** | Provides national/regional holiday data. | Simulated — Vietnamese holidays pre-seeded (Tet, Hung Kings, 30/4, 1/5, 2/9, Christmas). |

### 4.3 - Simulated Data Specification

All external factor data is pre-seeded from `simulated_event_data_and_rules.xlsx` and loaded into the SQLite database at startup.

**Tab 1 — Event Table** (7,815 rows)

| Column | Type | Description |
|--------|------|-------------|
| `store_id` | string | Store identifier (S0001–S0015) |
| `date` | date | Event date (2026-01-01 to 2026-12-31) |
| `time` | time | Event time (06:00 for weather, 00:00 for day-level events) |
| `event` | string | Event value (see below) |
| `event_type` | string | Category: Weather, Weekends, Holidays, Events |

**Coverage:** 15 stores × 365 days. A single date may have multiple events (e.g., a rainy Saturday during the World Cup).

**Event values by type:**

| Event Type | Values | Volume |
|------------|--------|--------|
| **Weather** | `dry` (3,747), `rain` (1,728) | Daily per store |
| **Weekends** | `Saturday` (780), `Sunday` (780) | Weekly per store |
| **Events** | `World Cup` (465), `Seagame` (165) | Multi-day spans per store |
| **Holidays** | `Tet holiday` (75), `Hung Kings` (15), `30th April` (15), `1st May` (15), `2 Sep` (15), `Christmas` (15) | Specific dates, all stores |

**Tab 2 — Prediction Rules** (10 rules)

These rules define the expected demand delta per channel when an event is active. The AI uses these as ground-truth multipliers; compound events stack additively.

| Event Type | Event | Channel | Direction | Delta |
|------------|-------|---------|-----------|-------|
| Weather | rain | Delivery | Increase | +5% |
| Weather | rain | Dine-in | Decrease | −3% |
| Weather | dry | Delivery | No change | 0% |
| Weather | dry | Dine-in | No change | 0% |
| Holidays | Any | Delivery | Increase | +2% |
| Holidays | Any | Dine-in | Increase | +2% |
| Weekends | Saturday | Delivery | Increase | +6% |
| Weekends | Saturday | Dine-in | Increase | +6% |
| Weekends | Sunday | Delivery | Increase | +6% |
| Weekends | Sunday | Dine-in | Increase | +6% |

**Channel-to-Station Mapping:** The prediction rules operate at the channel level (Delivery vs. Dine-in). The AI engine must translate channel-level demand deltas into station-level staffing adjustments. For example, a +5% Delivery increase during rain maps to more staff at Makeline and Dispatch stations, while a −3% Dine-in decrease means fewer staff at Front Counter.

> **Note:** The `Events` type (World Cup, Seagame) does not have explicit rules in Tab 2. The AI should reason about their impact using general knowledge (major sporting events increase dine-in traffic, especially during match times).

---

## 5 - Non-Functional Requirements

### 5.1 - Data Retention

- **Deployment charts:** Retained indefinitely (or until manually deleted) for historical comparison and AI learning.
- **AI suggestions:** Stored alongside the deployment chart for audit trail (what the AI suggested vs. what the manager finalized).
- **External factor snapshots:** The weather/event/holiday data used for each suggestion is stored with the chart so suggestions can be explained retroactively.

### 5.2 - Logging & Reporting

| Trigger Event | What to Capture | Priority | Audience |
|---------------|----------------|----------|----------|
| AI suggestion generated | Store ID, date, external factors, model used, raw suggestion, latency | High | Developers, Data Science |
| Deployment chart saved | Store ID, date, AI suggestion vs. final assignment diff | Medium | Operations, Managers |
| AI service error | Error type, store context (no PII), stack trace | High | Developers |
| Store profile updated | Entity changed, old/new values, user ID | Low | Audit |

### 5.3 - Performance

- **AI suggestion latency:** Target < 30 seconds for a complete suggestion (acceptable for local Ollama inference).
- **UI responsiveness:** Page load < 2 seconds, drag-and-drop interactions < 100ms response.
- **Concurrent users:** Hackathon scope — single-user usage. Architecture should not preclude multi-user support.
- **Data volume:** Support stores with up to 20 stations, 50 crew members, and 3 shifts per day.

### 5.4 - Supportability

- All AI prompts and responses are logged for debugging.
- The FastAPI backend provides health-check endpoints (`/health`) covering API status, database connectivity, and Ollama availability.
- Error messages in the UI are user-friendly with actionable guidance (e.g., "AI service is starting up, please try again in 30 seconds").

---

## 6 - Constraints

### 6.1 - Known Dependencies

| Dependency | Impact |
|-----------|--------|
| **Ollama installation** | Must be installed and running locally with a compatible model. |
| **Python environment** | Python 3.12+ required for the unified backend (FastAPI + AI logic). |
| **Existing schema alignment** | New entities (crew members, deployment charts) must coexist with the existing schema (`t_store`, `t_store_station`, `t_store_task`). |

### 6.2 - Notable Milestones

| Milestone | Target |
|-----------|--------|
| Store Profile UI (stations, tasks, crew CRUD) | Day 1 |
| AI Prediction Engine (Ollama integration, prompt design) | Day 1-2 |
| Deployment Chart UI (grid, AI display, assignment) | Day 2 |
| End-to-end integration & demo prep | Day 2-3 |

### 6.3 - Operational Constraints

- **Ollama model size:** Larger models give better reasoning but require more RAM/GPU. Recommend at least 8GB RAM for a 7B parameter model.
- **Offline capability:** The system runs entirely locally (Ollama, SQLite) — no cloud dependency for the hackathon.
- **Simulated data:** External factors (weather, events, holidays) use pre-seeded mock data rather than live API calls.

---

## 7 - Epic Breakdown

### Epic 1: Project Bootstrap & Data Foundation

**Goal:** Set up the project skeleton, database, and seed data so all other epics have a working foundation.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 1.1 | Project scaffolding | Initialize Python project with FastAPI, SQLite, dependency management (`requirements.txt`), and folder structure (`/api`, `/ai`, `/db`, `/models`, `/seed`). | `pip install -r requirements.txt && python main.py` starts the server on port 8000. |
| 1.2 | Database schema creation | Create SQLite tables matching the existing ER diagram (`t_store`, `t_station`, `t_station_area`, `t_store_station`, `t_store_task`, `t_station_visibility`, `t_country`, `t_country_equipment`, `t_equipment`) plus new tables: `t_crew_member`, `t_crew_skill`, `t_deployment_chart`, `t_deployment_assignment`, `t_ai_suggestion`, `t_external_event`. | All tables created on startup via migration script. Foreign keys enforced. |
| 1.3 | Seed external event data | Parse `simulated_event_data_and_rules.xlsx` and load Tab 1 (7,815 event rows) and Tab 2 (10 prediction rules) into `t_external_event` and `t_prediction_rule` tables. | `GET /api/events?store_id=S0001&date=2026-01-03` returns `[{event: "rain", type: "Weather"}, {event: "Saturday", type: "Weekends"}]`. |
| 1.4 | Seed store & station data | Pre-populate 15 stores (S0001–S0015) with sample stations and tasks from the existing schema. | `GET /api/stores` returns 15 stores. Each store has at least 5 stations and 3 tasks. |
| 1.5 | Health check endpoint | `GET /health` returns status of API, database, and Ollama connectivity. | Returns `{"api": "ok", "db": "ok", "ollama": "ok|unavailable"}`. |

---

### Epic 2: Store Profile Management API

**Goal:** CRUD endpoints for managing a store's stations, tasks, and crew members.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 2.1 | Store stations CRUD | Endpoints to list, add, update, deactivate stations for a store (`t_store_station`). | `GET/POST/PUT/DELETE /api/stores/{id}/stations` work correctly. Quantity and active status editable. |
| 2.2 | Store tasks CRUD | Endpoints to list, add, update, deactivate secondary tasks for a store (`t_store_task`). | `GET/POST/PUT/DELETE /api/stores/{id}/tasks` work correctly. |
| 2.3 | Crew member CRUD | Endpoints to list, add, update, remove crew members. Each crew member has name, role, availability pattern, and active status. | `GET/POST/PUT/DELETE /api/stores/{id}/crew` work correctly. |
| 2.4 | Crew skills management | Assign/remove skill tags (station certifications) to crew members. A crew member can be certified for multiple stations. | `PUT /api/crew/{id}/skills` accepts a list of station IDs. `GET /api/stores/{id}/crew` returns crew with their skills. |

---

### Epic 3: External Events & Prediction Rules API

**Goal:** Endpoints to query simulated external factors for a given store and date, and retrieve the prediction rules.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 3.1 | Query events by store & date | Return all external events for a store on a given date (weather, weekends, holidays, events). | `GET /api/events?store_id=S0001&date=2026-03-14` returns all matching events. |
| 3.2 | Query events by date range | Return events for a store across a date range (for weekly deployment planning). | `GET /api/events?store_id=S0001&from=2026-03-09&to=2026-03-15` returns the week's events. |
| 3.3 | Prediction rules endpoint | Return the prediction rules table so the AI prompt and UI can reference them. | `GET /api/prediction-rules` returns all 10 rules with event type, channel, direction, and delta. |
| 3.4 | Event summary for a date | Aggregated view: for a store+date, return a structured summary of all active factors with their expected demand impact per channel. | `GET /api/events/summary?store_id=S0001&date=2026-02-14` returns `{factors: [...], delivery_delta: +0.11, dinein_delta: +0.03}` (rain + Saturday). |

---

### Epic 4: AI Prediction Engine

**Goal:** Build the LLM-powered staffing suggestion pipeline using Ollama.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 4.1 | Ollama client integration | Create a reusable Ollama client that sends prompts and receives structured JSON responses. Handle timeouts, retries, and model unavailability. | Client can send a prompt to Ollama and parse a JSON response. Graceful fallback on timeout. |
| 4.2 | Prompt template design | Design the prompt that includes: store profile (stations, tasks, crew count, skills), active events for the date, prediction rules, and the instruction to return staffing levels per station per shift. | Prompt template is parameterized. Output format is validated against a Pydantic schema. |
| 4.3 | Channel-to-station mapping | Translate channel-level deltas (Delivery +5%, Dine-in −3%) into station-level staffing adjustments. Provide this as context to the LLM. | Mapping is configurable per store. Default mapping provided (e.g., Delivery → Makeline + Dispatch, Dine-in → Front Counter + Dining). |
| 4.4 | Suggestion generation endpoint | `POST /api/suggestions/generate` accepts store_id and date, gathers all context, calls Ollama, and returns structured staffing suggestions. | Returns `{shifts: [{shift: "Morning", stations: [{station: "Grill", recommended: 2, reasoning: "..."}]}]}`. Latency < 30s. |
| 4.5 | Suggestion persistence | Store generated suggestions in `t_ai_suggestion` with the full context snapshot (events, rules, prompt, raw response, model used, latency). | Suggestions are retrievable via `GET /api/suggestions/{id}`. Context is preserved for audit. |
| 4.6 | Fallback: rule-based suggestions | If Ollama is unavailable, generate suggestions using only the prediction rules (deterministic calculation). | When Ollama is down, endpoint still returns suggestions with `source: "rule-based"` flag. |

---

### Epic 5: Deployment Chart API

**Goal:** Endpoints to create, read, update deployment charts with crew assignments.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 5.1 | Create deployment chart | Create a new chart for a store+date, optionally pre-populated with AI suggestion data. | `POST /api/stores/{id}/charts` creates a chart. If a suggestion exists, cells are pre-filled with recommended headcounts. |
| 5.2 | Assign crew to chart cells | Assign/unassign individual crew members to station+shift cells. Validate skill match and availability. | `PUT /api/charts/{id}/assignments` accepts `{shift, station_id, crew_member_id}`. Warns on skill mismatch. |
| 5.3 | Chart retrieval | Retrieve a deployment chart with all assignments, AI suggestions, and staffing gaps. | `GET /api/charts/{id}` returns the full chart with `ai_recommended` vs. `assigned` counts per cell. |
| 5.4 | Chart finalization | Mark a chart as finalized. Record the diff between AI suggestion and final assignment. | `POST /api/charts/{id}/finalize` locks the chart. Diff is computed and stored. |
| 5.5 | Chart history | List past deployment charts for a store, filterable by date range. | `GET /api/stores/{id}/charts?from=2026-01-01&to=2026-03-31` returns historical charts. |

---

### Epic 6: Frontend — Store Profile UI

**Goal:** React screens for managing store configuration.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 6.1 | Store selector | Dropdown/list to select from the 15 seeded stores. | Manager can select a store; selected store persists in session. |
| 6.2 | Stations & tasks setup | List view of stations with toggle active/inactive, edit quantity. List view of tasks with add/edit/delete. | Manager can configure stations and tasks. Changes persist via API. |
| 6.3 | Crew management | Card/list view of crew members. Add/edit/remove crew. Assign skill tags (station certifications). Filter/search crew. | Manager can manage crew roster. Skill tags display as badges. |
| 6.4 | Crew availability | Simple availability pattern per crew member (e.g., available Monday–Friday Morning+Afternoon). | Availability is editable and saved. Used later for assignment validation. |

---

### Epic 7: Frontend — Deployment Chart UI

**Goal:** The core interactive deployment chart with AI suggestions and crew assignment.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 7.1 | Date picker & event display | Date picker at top. On date selection, display active external factors (weather icon, event badge, holiday marker) with demand impact summary. | Selecting a date shows all events for that store+date with channel deltas. |
| 7.2 | AI suggestion grid | Grid layout: Rows = Stations + Tasks, Columns = Shifts (Morning, Afternoon, Evening). Each cell shows AI-recommended headcount. | Grid renders after clicking "Generate Suggestion". Reasoning tooltips on hover. |
| 7.3 | Generate suggestion flow | "Generate Suggestion" button triggers API call. Loading state during Ollama inference (up to 30s). Error handling if AI unavailable. | Button triggers generation, shows spinner, populates grid on success. Falls back to rule-based on failure. |
| 7.4 | Crew assignment panel | Side panel showing available crew, filterable by skills and availability. Click or drag to assign crew to station+shift cells. | Crew pool updates as members are assigned. Assigned crew appear in cells. |
| 7.5 | Staffing gap indicators | Visual warnings when a cell has fewer assigned crew than AI recommends (under-staffed) or more (over-staffed). | Red indicator for under-staffed, yellow for over-staffed, green for matched. |
| 7.6 | Save & finalize | "Save Draft" persists current state. "Finalize" locks the chart and records the AI-vs-actual diff. | Both actions persist via API. Finalized chart is read-only. |
| 7.7 | Chart history view | View past deployment charts for the store. Compare AI suggestion vs. actual assignment side-by-side. | Historical charts are browsable. Diff is visually highlighted. |

---

### Epic 8: Integration, Testing & Demo

**Goal:** End-to-end testing, polish, and demo preparation.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 8.1 | End-to-end smoke test | Verify the full flow: select store → pick date → generate suggestion → assign crew → finalize chart. | Full flow completes without errors for at least 3 different date/event scenarios. |
| 8.2 | Scenario demo scripts | Prepare 3 demo scenarios showcasing AI value: (1) Rainy Saturday — rain + weekend stacking, (2) Tet Holiday — holiday + possible rain, (3) World Cup evening — major event impact. | Each scenario has a script, expected AI output, and talking points. |
| 8.3 | Error handling polish | Ensure all error states (Ollama down, no crew, empty store) display user-friendly messages. | No unhandled errors in UI. All edge cases show actionable messages. |
| 8.4 | Performance validation | Verify AI suggestion latency < 30s, page loads < 2s, assignment interactions < 100ms. | Performance targets met on demo hardware. |

### Epic 9: AI Chat Refinement Panel

**Goal:** Enable managers to refine AI suggestions through a conversational side-panel, providing additional context, overriding cells, asking "why", and running what-if scenarios — with real-time grid updates.

| # | Story | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 9.1 | Chat panel UI (side panel) | Build a slide-in right-side panel (340px) on the AI Suggestion screen with header, scrollable message list, and input bar. | Panel opens/closes with smooth animation. Grid shrinks to accommodate. |
| 9.2 | Chat toggle & grid integration | Add "Chat with AI" button next to AI grid. Clicking a grid cell while chat is open auto-populates "Why [Station] [Shift]?" in the input. | Toggle works; cell-click auto-fill verified. |
| 9.3 | Quick-action chips | Provide contextual chips above the input bar: "Add context", "Ask why", "Override cell", "What if...". Clicking pre-fills the input. | All 4 chips render and populate input correctly. |
| 9.4 | Pattern A — Add context | Manager provides additional info (e.g., crew absences). AI adjusts affected cells, shows reasoning, grid reflects "refined" indicators. | Cells update with refined badge; chat shows structured diff. |
| 9.5 | Pattern B — Override cell | Manager directly overrides a cell value. AI acknowledges, marks cell as "manager override" (locked from future AI adjustments). | Override cell shows lock/override badge; value persists across regenerations. |
| 9.6 | Pattern C — Ask why | Manager asks "Why X at Y station?". AI returns structured reasoning (factors, rules, channel mapping, crew constraint, confidence). | Reasoning response renders with structured layout; covers all 5 reasoning elements. |
| 9.7 | Pattern D — What-if scenario | Manager asks "What if [condition]?". AI shows proposed changes as diff; manager can "Apply" or "Dismiss". | Scenario diff renders; Apply updates grid; Dismiss reverts to original. |
| 9.8 | Chat context persistence | Full chat history is sent with each AI prompt so the AI remembers all prior context. Chat persists if manager navigates away and returns. | Chat history survives tab switches; AI responses account for prior context. |
| 9.9 | Grid update indicators | Cells modified via chat show visual indicators: orange "refined" label for AI adjustments, lock icon for manager overrides, side-by-side diff for what-if scenarios. | All 3 indicator types render correctly and are visually distinct. |

---

## 8 - References

| Reference | Link |
|-----------|------|
| Database Schema (ER Diagram) | `docs/schema-er-diagram.png` |
| Simulated Event Data & Rules | `simulated_event_data_and_rules.xlsx` |
| Ollama Documentation | https://ollama.ai |
| PRD Template | https://pizzahut.atlassian.net/wiki/spaces/PC2/pages/6042419220/Example+PRD |
