// frontend/src/services/api.ts

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface MetricItem {
  key: string;
  label: string;
  value: number;
  unit: string;
}

export interface SensorPacket {
  timestamp: string;
  device_name: string;
  sensor_type: string;
  selected_zone: string;
  selected_business_type: string;
  radius_km: number;
  indicator: string;
  summary_text: string;
  metrics: MetricItem[];
  meta: Record<string, string>;
}

export interface MonitorStatus {
  name: string;
  value: string;
  indicator: string;
}

export interface MLPredictionResponse {
  predicted_risk_class: string;
  risk_probabilities: Record<string, number>;
  predicted_monthly_net_revenue: number;
  predicted_feasibility_score: number;
  recommendation: string;
}

export interface ModuleAnalysisResponse {
  score: number;
  level: string;
  summary: string;
  signals: string[];
  metrics: Record<string, number>;
}

export interface AnalysisBreakdownResponse {
  demand_analysis: ModuleAnalysisResponse;
  competition_analysis: ModuleAnalysisResponse;
  lease_cost_analysis: ModuleAnalysisResponse;
}

export interface PredictionExplanationResponse {
  competition_score: number;
  demand_score: number;
  demographic_fit_score: number;
  estimated_competitor_count: number;
  reachable_population_estimate: number;
  monthly_lease_cost_estimate: number;
  monthly_operating_cost_estimate: number;
  revenue_explanation: string;
  risk_explanation: string;
  feasibility_explanation: string;
  top_positive_factors: string[];
  top_negative_factors: string[];
}

export interface OutputEvidenceItem {
  field_name: string;
  label: string;
  method: string;
  credibility: string;
  source: string;
  user_note: string;
}

export interface PredictionCredibilityResponse {
  overall_confidence_score: number;
  confidence_level: string;
  data_quality_score: number;
  model_signal_score: number;
  proxy_dependency_score: number;
  observed_inputs: OutputEvidenceItem[];
  model_predicted_outputs: OutputEvidenceItem[];
  proxy_estimated_inputs: OutputEvidenceItem[];
  derived_metrics: OutputEvidenceItem[];
  user_facing_disclaimer: string;
  next_data_needed: string[];
}


export interface CompetitionObservationEvidence {
  municipality_name: string;
  business_subcategory: string;
  source_name: string;
  source_method: string;
  source_date: string;
  method: string;
  credibility: string;
  observed_competitor_count: number;
  competitor_density_per_10k: number;
  nearest_competitor_distance_km: number | null;
  avg_competitor_rating: number | null;
  chain_share_pct: number | null;
  competition_pressure_index: number;
  data_quality_note: string;
}

export interface CompetitionObservationCatalogResponse {
  count: number;
  observations: CompetitionObservationEvidence[];
}


export interface DemandEvidence {
  municipality_name: string;
  business_subcategory: string;
  source_name: string;
  source_method: string;
  source_date: string;
  method: string;
  credibility: string;
  reachable_population_estimate: number;
  target_customer_pool_estimate: number;
  daytime_activity_index: number;
  foot_traffic_proxy_index: number;
  transit_access_proxy_index: number;
  demographic_fit_score: number;
  demand_pressure_index: number;
  demand_level: string;
  data_quality_note: string;
}

export interface DemandEvidenceCatalogResponse {
  count: number;
  observations: DemandEvidence[];
}

export interface LeaseCostEvidence {
  municipality_name: string;
  business_subcategory: string;
  source_name: string;
  source_method: string;
  source_date: string;
  method: string;
  credibility: string;
  estimated_space_sqft: number;
  low_monthly_lease_cost: number;
  median_monthly_lease_cost: number;
  high_monthly_lease_cost: number;
  lease_cost_per_sqft_year: number;
  rent_pressure_index: number;
  commercial_cost_pressure_level: string;
  data_quality_note: string;
}

export interface LeaseCostCatalogResponse {
  count: number;
  observations: LeaseCostEvidence[];
}


export interface RecommendationEvidenceSignal {
  name: string;
  value: string;
  direction: string;
  impact: string;
  source_type: string;
}

export interface RecommendationDecisionResponse {
  final_recommendation: string;
  recommendation_label: string;
  decision_confidence_score: number;
  confidence_level: string;
  decision_summary: string;
  decision_rationale: string;
  action_guidance: string;
  major_strengths: string[];
  major_concerns: string[];
  evidence_signals: RecommendationEvidenceSignal[];
  caution_note: string;
}

export interface OperatingProfileRange {
  low?: number | null;
  median?: number | null;
  high?: number | null;
  unit: string;
  display_value: string;
}

export interface OperatingProfileSection {
  key: string;
  title: string;
  status: string;
  estimate_type: string;
  confidence: string;
  range?: OperatingProfileRange | null;
  summary: string;
  reasoning: string[];
  evidence_used: string[];
  limitations: string[];
}

export interface OperatingProfileResponse {
  status: string;
  municipality_name: string;
  business_query?: string | null;
  business_subcategory?: string | null;
  normalized_business_name?: string | null;
  radius_km: number;
  source_method: string;
  cache_status: string;
  model?: string | null;
  overall_confidence: string;
  user_facing_note: string;
  sections: OperatingProfileSection[];
  warnings: string[];
  next_data_needed: string[];
  raw_ai_available: boolean;
  raw_ai_error?: string | null;
}



export interface GeoCoordinate {
  latitude: number;
  longitude: number;
}

export interface MapMarker {
  marker_id: string;
  marker_type: string;
  label: string;
  latitude: number;
  longitude: number;
  x_offset_pct: number;
  y_offset_pct: number;
  intensity: number;
  source_method: string;
  credibility: string;
  osm_id?: string | null;
  osm_type?: string | null;
  category?: string | null;
  address?: string | null;
  tags: Record<string, string>;
}

export interface HeatmapCell {
  cell_id: string;
  latitude: number;
  longitude: number;
  demand_intensity: number;
  risk_intensity: number;
  label: string;
  source_method: string;
}

export interface GeospatialMarketContext {
  municipality_name: string;
  business_subcategory: string;
  radius_km: number;
  center: GeoCoordinate;
  // Where the radius/evidence is anchored: "address" (a specific site geocoded) or
  // "city_center". resolved_address names the exact geocoded site when available.
  anchor_type?: string;
  resolved_address?: string | null;
  geocode_confidence?: string | null;
  municipality_match?: boolean | null;
  anchor_note?: string;
  // How the feasibility score was derived for the requested business input.
  score_basis?: "exact_catalog" | "nearest_catalog" | "unavailable" | string;
  score_basis_subcategory?: string | null;
  score_basis_note?: string;
  map_method: string;
  map_credibility: string;
  coverage_note: string;
  evidence_note: string;
  radius_label: string;
  competition_pressure_index: number;
  demand_pressure_index: number;
  rent_pressure_index: number;
  marker_count: number;
  real_competitor_count: number;
  competition_evidence?: CompetitionObservationEvidence | null;
  competition_evidence_source?: string;
  transit_marker_count: number;
  lease_marker_count: number;
  markers: MapMarker[];
  heatmap_cells: HeatmapCell[];
  osm_query_status: string;
  osm_query_note: string;
  next_data_needed: string[];
}

export interface DashboardSummaryResponse {
  application_name: string;
  project_phase: string;
  municipality_name: string;
  business_subcategory: string;
  radius_km: number;
  people_location_packet: SensorPacket;
  competition_monitor: MonitorStatus;
  revenue_monitor: MonitorStatus;
  risk_monitor: MonitorStatus;
  ml_prediction: MLPredictionResponse | null;
  prediction_explanation: PredictionExplanationResponse | null;
  analysis_breakdown: AnalysisBreakdownResponse | null;
  prediction_credibility: PredictionCredibilityResponse | null;
  competition_evidence: CompetitionObservationEvidence | null;
  lease_cost_evidence: LeaseCostEvidence | null;
  demand_evidence: DemandEvidence | null;
  recommendation_decision: RecommendationDecisionResponse | null;
  operating_profile?: OperatingProfileResponse | null;
}

export interface AnalyzeScenarioRequest {
  municipality_name: string;
  business_subcategory: string;
  radius_km: number;
}

export interface GeospatialMarketMapRequest {
  municipality_name: string;
  radius_km: number;
  site_address?: string;
  business_subcategory?: string;
  business_query?: string;
}

export interface ScenarioSupportRequest {
  municipality_name: string;
  business_subcategory: string;
  radius_km: number;
  business_input_mode: "catalog" | "custom";
  custom_business_query?: string | null;
  use_custom_business_for_map: boolean;
  business_resolution_status?: string | null;
  resolved_osm_tag_count: number;
  business_resolution_confidence?: string | null;
}

export interface ScenarioSupportSection {
  status: string;
  label: string;
  summary: string;
  reasons: string[];
  required_next_steps: string[];
}

export interface ScenarioSupportResponse {
  overall_status: string;
  overall_label: string;
  summary: string;
  prediction_support: ScenarioSupportSection;
  map_evidence_support: ScenarioSupportSection;
  data_trust_notes: string[];
  warnings: string[];
  allowed_next_actions: string[];
}

export interface FeasibilityReportResponse {
  filename: string;
  content_type: string;
  report_text: string;
}

export interface ScenarioHistoryItem {
  scenario_id: string;
  saved_at: string;
  municipality_name: string;
  business_subcategory: string;
  radius_km: number;
  predicted_monthly_net_revenue: number | null;
  predicted_risk_class: string | null;
  predicted_feasibility_score: number | null;
  recommendation_label: string | null;
  decision_confidence_score: number | null;
  prediction_confidence_score: number | null;
  demand_pressure_index: number | null;
  competition_pressure_index: number | null;
  median_monthly_lease_cost: number | null;
  data_reliability_note: string;
}

export interface ScenarioHistoryResponse {
  count: number;
  scenarios: ScenarioHistoryItem[];
}

export interface ScenarioComparisonItem {
  scenario_id: string;
  label: string;
  overall_score: number;
  revenue_position: number;
  risk_position: number;
  feasibility_position: number;
  confidence_position: number;
  key_tradeoff: string;
}

export interface ScenarioComparisonResponse {
  generated_at: string;
  compared_count: number;
  best_overall_scenario_id: string | null;
  comparison_summary: string;
  rankings: ScenarioComparisonItem[];
}


export interface ModelFileStatusResponse {
  risk_classifier: boolean;
  revenue_regressor: boolean;
  feasibility_regressor: boolean;
  metadata: boolean;
}

export interface ModelStatusResponse {
  status: string;
  trained_at: string | null;
  dataset_path: string | null;
  row_count: number;
  feature_count: number;
  categorical_feature_count: number;
  numeric_feature_count: number;
  targets: Record<string, string>;
  risk_accuracy: number | null;
  revenue_mae: number | null;
  revenue_rmse: number | null;
  revenue_r2: number | null;
  feasibility_mae: number | null;
  feasibility_rmse: number | null;
  feasibility_r2: number | null;
  model_files: ModelFileStatusResponse;
  important_note: string;
}

export interface ValidationCheckResponse {
  name: string;
  status: string;
  message: string;
}

export interface SystemValidationResponse {
  overall_status: string;
  passed_checks: number;
  total_checks: number;
  checks: ValidationCheckResponse[];
}

export interface MunicipalityOption {
  municipality_name: string;
  municipality_type: string;
  label: string;
}

export interface MunicipalitiesResponse {
  municipalities: MunicipalityOption[];
}

export interface BusinessSubcategoryOption {
  business_category: string;
  business_subcategory: string;
  label: string;
}

export interface BusinessSubcategoriesResponse {
  business_subcategories: BusinessSubcategoryOption[];
}

export type BusinessInputMode = "catalog" | "custom";

export interface BusinessResolverOSMTag {
  key: string;
  value: string;
  confidence: number;
  tag_role: string;
  reason?: string | null;
}

export interface BusinessResolverRejectedTag {
  raw: unknown;
  reason: string;
}

export interface BusinessResolveRequest {
  business_query: string;
  municipality_name?: string | null;
  model?: string | null;
}

export interface BusinessResolutionResponse {
  status: string;
  input_text: string;
  normalized_business_name: string;
  primary_category: string;
  secondary_categories: string[];
  brand_terms: string[];
  specialty_terms: string[];
  osm_tags: BusinessResolverOSMTag[];
  rejected_osm_tags: BusinessResolverRejectedTag[];
  resolution_confidence: string;
  confidence_score: number;
  source_method: string;
  raw_ai_available: boolean;
  warnings: string[];
  next_steps: string[];
  raw_ai_error?: string | null;
}

export interface RegisteredSensorsResponse {
  sensors: Record<string, string>;
}

export interface PacketHistoryResponse {
  sensor_type: string;
  count: number;
  packets: SensorPacket[];
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface DbCheckResponse {
  database_connected: boolean;
  message: string;
}

const DEFAULT_TIMEOUT_MS = 60000;

async function requestJson<T>(
  url: string,
  init?: RequestInit,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s: ${url}. Is the backend running?`,
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let details = "";
    try {
      details = await res.text();
    } catch {
      details = "";
    }
    throw new Error(
      `${res.status} ${res.statusText}${details ? ` — ${details}` : ""}`,
    );
  }

  return res.json() as Promise<T>;
}

export function fetchDashboardSummary(): Promise<DashboardSummaryResponse> {
  return requestJson<DashboardSummaryResponse>(`${API_BASE}/dashboard-summary`);
}

export function analyzeScenario(
  request: AnalyzeScenarioRequest,
): Promise<DashboardSummaryResponse> {
  return requestJson<DashboardSummaryResponse>(`${API_BASE}/analyze-scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function generateFeasibilityReport(
  request: AnalyzeScenarioRequest,
): Promise<FeasibilityReportResponse> {
  return requestJson<FeasibilityReportResponse>(
    `${API_BASE}/reports/feasibility`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}


export function fetchGeospatialMarketMap(
  request: GeospatialMarketMapRequest,
): Promise<GeospatialMarketContext> {
  return requestJson<GeospatialMarketContext>(`${API_BASE}/geo/market-map`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function fetchOsmPois(request: AnalyzeScenarioRequest): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(`${API_BASE}/geo/osm-pois`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function saveScenarioToHistory(
  request: AnalyzeScenarioRequest,
): Promise<ScenarioHistoryItem> {
  return requestJson<ScenarioHistoryItem>(`${API_BASE}/scenario-history/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function fetchScenarioHistory(): Promise<ScenarioHistoryResponse> {
  return requestJson<ScenarioHistoryResponse>(`${API_BASE}/scenario-history`);
}

export function clearScenarioHistory(): Promise<ScenarioHistoryResponse> {
  return requestJson<ScenarioHistoryResponse>(`${API_BASE}/scenario-history`, {
    method: "DELETE",
  });
}

export function compareScenarioHistory(): Promise<ScenarioComparisonResponse> {
  return requestJson<ScenarioComparisonResponse>(
    `${API_BASE}/scenario-history/compare`,
    { method: "POST" },
  );
}



export function fetchCompetitionObservations(): Promise<CompetitionObservationCatalogResponse> {
  return requestJson<CompetitionObservationCatalogResponse>(
    `${API_BASE}/market/competition-observations`,
  );
}

export function fetchCompetitionEvidence(
  request: AnalyzeScenarioRequest,
): Promise<CompetitionObservationEvidence | null> {
  return requestJson<CompetitionObservationEvidence | null>(
    `${API_BASE}/market/competition-evidence`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}


export function fetchLeaseCostObservations(): Promise<LeaseCostCatalogResponse> {
  return requestJson<LeaseCostCatalogResponse>(
    `${API_BASE}/market/lease-cost-observations`,
  );
}

export function fetchLeaseCostEvidence(
  request: AnalyzeScenarioRequest,
): Promise<LeaseCostEvidence> {
  return requestJson<LeaseCostEvidence>(
    `${API_BASE}/market/lease-cost-evidence`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}


export function fetchDemandObservations(): Promise<DemandEvidenceCatalogResponse> {
  return requestJson<DemandEvidenceCatalogResponse>(
    `${API_BASE}/market/demand-observations`,
  );
}

export function fetchDemandEvidence(
  request: AnalyzeScenarioRequest,
): Promise<DemandEvidence> {
  return requestJson<DemandEvidence>(
    `${API_BASE}/market/demand-evidence`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}


export function fetchRecommendationDecision(
  request: AnalyzeScenarioRequest,
): Promise<RecommendationDecisionResponse> {
  return requestJson<RecommendationDecisionResponse>(
    `${API_BASE}/recommendation/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export function fetchPredictionCredibility(
  request: AnalyzeScenarioRequest,
): Promise<PredictionCredibilityResponse> {
  return requestJson<PredictionCredibilityResponse>(
    `${API_BASE}/ml/prediction-credibility`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}


export function checkScenarioSupportCoverage(
  request: ScenarioSupportRequest,
): Promise<ScenarioSupportResponse> {
  return requestJson<ScenarioSupportResponse>(`${API_BASE}/scenario/support-coverage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function fetchModelStatus(): Promise<ModelStatusResponse> {
  return requestJson<ModelStatusResponse>(`${API_BASE}/ml/model-status`);
}

export function runSystemValidation(): Promise<SystemValidationResponse> {
  return requestJson<SystemValidationResponse>(`${API_BASE}/validation/system`);
}

export function fetchMunicipalities(): Promise<MunicipalitiesResponse> {
  return requestJson<MunicipalitiesResponse>(`${API_BASE}/municipalities`);
}

export function fetchBusinessSubcategories(): Promise<BusinessSubcategoriesResponse> {
  return requestJson<BusinessSubcategoriesResponse>(
    `${API_BASE}/business-subcategories`,
  );
}

export function resolveBusiness(
  request: BusinessResolveRequest,
): Promise<BusinessResolutionResponse> {
  return requestJson<BusinessResolutionResponse>(`${API_BASE}/business/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function fetchRegisteredSensors(): Promise<RegisteredSensorsResponse> {
  return requestJson<RegisteredSensorsResponse>(
    `${API_BASE}/bus/registered-sensors`,
  );
}

export async function fetchLatestPacket(
  sensorType: string,
): Promise<SensorPacket | null> {
  const res = await fetch(`${API_BASE}/bus/latest/${sensorType}`);
  if (!res.ok) throw new Error(`Failed to fetch latest packet: ${res.status}`);
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export function fetchPacketHistory(
  sensorType: string,
): Promise<PacketHistoryResponse> {
  return requestJson<PacketHistoryResponse>(
    `${API_BASE}/bus/history/${sensorType}`,
  );
}

export function checkHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>(`${API_BASE}/health`);
}

export function checkDatabase(): Promise<DbCheckResponse> {
  return requestJson<DbCheckResponse>(`${API_BASE}/db-check`);
}

export function getIndicatorColor(indicator: string): string {
  switch (indicator) {
    case "green":
      return "text-emerald-400";
    case "yellow":
      return "text-accent";
    case "red":
      return "text-destructive";
    default:
      return "text-muted-foreground";
  }
}

export function getIndicatorBg(indicator: string): string {
  switch (indicator) {
    case "green":
      return "bg-emerald-400/10 border-emerald-400/30";
    case "yellow":
      return "bg-accent/10 border-accent/30";
    case "red":
      return "bg-destructive/10 border-destructive/30";
    default:
      return "bg-white/5 border-white/10";
  }
}
