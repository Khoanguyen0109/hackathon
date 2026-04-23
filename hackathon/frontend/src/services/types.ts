export type Shift = "Morning" | "Afternoon" | "Evening";
export type Confidence = "high" | "medium" | "low";
export type Outcome = "short" | "met" | "over";

// Screen 0 — Store profile

export interface Station {
  station_id: string;
  station_name: string;
  area: string;
  positions: number;
  base_staff_morning: number;
  base_staff_afternoon: number;
  base_staff_evening: number;
  primary_channel: string;
  channel_weight: number;
  icon_emoji?: string;
  colour_hex?: string;
}

export interface Task {
  task_id: string;
  task_name: string;
  category: string;
  area: string;
  duration_min: number;
  frequency_per_shift: number;
  icon_emoji?: string;
}

export interface Store {
  store_id: string;
  store_name: string;
  city: string;
  open_hour: number;
  close_hour: number;
  shifts_per_day: number;
  base_staff_per_shift: number;
  min_staff_per_shift: number;
  max_staff_per_shift: number;
  base_daily_orders?: number;
}

// Screen 1 — Crew

export interface Employee {
  employee_id: string;
  employee_name: string;
  store_id: string;
  role: string;
  contract_hours_per_week: number;
  min_hours_per_week: number;
  hourly_rate: number;
  available_days: string[];
  available_shifts: Shift[];
  skills: string[];
}

export interface EmployeeCreate {
  employee_name: string;
  role: string;
  contract_hours_per_week?: number;
  min_hours_per_week?: number;
  hourly_rate?: number;
  available_days?: string[];
  available_shifts?: Shift[];
  skills?: string[];
}

export interface EmployeePatch {
  employee_name?: string;
  role?: string;
  contract_hours_per_week?: number;
  min_hours_per_week?: number;
  hourly_rate?: number;
  available_days?: string[];
  available_shifts?: Shift[];
  skills?: string[];
}

// Screen 2 — AI context + suggestion

export interface ContextFactor {
  kind: "weather" | "event" | "promo" | "holiday" | "day_of_week";
  label: string;
  icon: string;
  probability?: number;
  impact_delivery: number;
  impact_dinein: number;
  impact_drivethrough: number;
  source: string;
  note: string;
  time_window?: string;
}

export interface ContextResponse {
  store_id: string;
  date: string;
  day_of_week: string;
  factors: ContextFactor[];
  channel_multipliers: Record<string, number>;
}

export interface ReasonRow {
  icon: string;
  label: string;
  value: string;
}

export interface RushHourInfo {
  is_rush: boolean;
  label?: string;
  window?: string;
  overlap_pct: number;
  staff_uplift: number;
  solutions: string[];
}

export interface StaffingCell {
  station_id: string;
  station_name: string;
  shift: Shift;
  ai_recommended: number;
  reason_short: string;
  confidence: Confidence;
  factors: string[];
  rules_applied: string[];
  channel_note: string;
  crew_note: string;
  reason_rows: ReasonRow[];
  rush_hour?: RushHourInfo;
}

export interface StaffingRequest {
  store_id: string;
  date: string;
  demo_mode?: boolean;
}

export interface StaffingResponse {
  store_id: string;
  date: string;
  day_of_week: string;
  generated_at: string;
  model_used: string;
  generation_ms: number;
  context: ContextResponse;
  cells: StaffingCell[];
}

// Screen 3-5 — Deployments

export interface AssignedCell {
  station_id: string;
  shift: Shift;
  ai_recommended: number;
  assigned_employee_ids: string[];
  manager_note?: string;
}

export interface DeploymentCreate {
  store_id: string;
  date: string;
  cells: AssignedCell[];
  source_staffing_model?: string;
}

export interface Deployment {
  deployment_id: string;
  store_id: string;
  date: string;
  created_at: string;
  updated_at: string;
  cells: AssignedCell[];
  source_staffing_model?: string;
}

export interface DeploymentSummary {
  deployment_id: string;
  store_id: string;
  date: string;
  total_ai_recommended: number;
  total_assigned: number;
  gap: number;
  coverage_pct: number;
  shortages: AssignedCell[];
  overages: AssignedCell[];
  est_wage_cost: number;
  confidence_mix: Record<Confidence, number>;
}

export interface ComparisonRow {
  station_id: string;
  shift: Shift;
  ai_recommended: number;
  manager_assigned: number;
  actual_staffed?: number;
  gap: number;
  outcome: Outcome;
}

export interface DeploymentComparison {
  deployment_id: string;
  rows: ComparisonRow[];
}

// Chat

export interface ChatMessage {
  id: string;
  role: "user" | "ai" | "system";
  content: string;
  timestamp: string;
  actions?: ChatAction[];
}

export interface ChatAction {
  type: "assign" | "unassign" | "swap";
  employee_id: string;
  employee_name?: string;
  station_id: string;
  station_name?: string;
  shift: Shift;
  reason: string;
}

export interface ChatMessageIn {
  role: "user" | "ai" | "system";
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessageIn[];
  store_id: string;
  date: string;
  current_cells: AssignedCell[];
}

export interface ChatResponse {
  message: string;
  actions: ChatAction[];
}
