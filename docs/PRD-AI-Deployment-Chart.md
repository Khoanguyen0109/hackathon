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
4. View the suggestions in a shift-based deployment chart grid.
5. Assign specific crew members to each station/task slot by dragging or selecting from the available pool.
6. Override or adjust AI suggestions before finalizing the chart.
7. Save and review the finalized deployment chart.

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
| **Weather API** | Provides weather forecasts for the store's location and target date. | Simulated with mock data. |
| **Events API** | Provides local event information (sports, concerts, community events). | Simulated with mock data. |
| **Holiday Calendar** | Provides national/regional holiday data. | Simulated with mock data. |
| **Company Promotions** | Internal promotions or campaigns that drive demand. | Simulated with mock data. |

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

## 7 - References

| Reference | Link |
|-----------|------|
| Database Schema | `schema.md` (project root) |
| Ollama Documentation | https://ollama.ai |
| PRD Template | https://pizzahut.atlassian.net/wiki/spaces/PC2/pages/6042419220/Example+PRD |
