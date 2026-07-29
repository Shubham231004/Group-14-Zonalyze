const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export type LocationComparisonRequest = {
  business_subcategory: string;
  base_municipality_name?: string | null;
  candidate_municipalities?: string[];
  radius_options_km?: number[];
  max_results?: number;
};

export type LocationComparisonItem = {
  rank: number;
  municipality_name: string;
  radius_km: number;
  business_subcategory: string;
  predicted_monthly_net_revenue: number;
  predicted_feasibility_score: number;
  predicted_risk_class: string;
  recommendation: string;
  high_risk_probability: number;
  competition_pressure_index: number;
  demand_pressure_index: number;
  rent_pressure_index: number;
  reachable_population_estimate: number;
  estimated_monthly_lease_cost: number;
  estimated_monthly_operating_cost: number;
  decision_score: number;
  strengths: string[];
  concerns: string[];
  data_notes: string[];
};

export type LocationComparisonResponse = {
  status: string;
  business_subcategory: string;
  compared_scenario_count: number;
  returned_result_count: number;
  ranking_method: string;
  best_option?: LocationComparisonItem | null;
  results: LocationComparisonItem[];
  skipped_scenarios: string[];
  user_facing_note: string;
};

export async function compareScenarioLocations(
  payload: LocationComparisonRequest,
): Promise<LocationComparisonResponse> {
  const response = await fetch(`${API_BASE_URL}/scenario/location-comparison`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Location comparison failed with status ${response.status}`);
  }

  return response.json();
}
