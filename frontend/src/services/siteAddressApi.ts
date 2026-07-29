const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export type SiteAddressAnalysisRequest = {
  address_line: string;
  municipality_name: string;
  radius_km: number;
  business_subcategory?: string | null;
  business_query?: string | null;
};

export type SiteGeocodeCandidate = {
  display_name: string;
  latitude: number;
  longitude: number;
  resolved_municipality?: string | null;
  municipality_match: boolean;
  confidence: string;
  importance?: number | null;
  source: string;
};

export type SiteEvidenceItem = {
  name: string;
  category: string;
  distance_km: number;
  latitude: number;
  longitude: number;
  address?: string | null;
  source: string;
};

export type SiteEvidenceSummary = {
  count: number;
  nearest?: SiteEvidenceItem | null;
  items: SiteEvidenceItem[];
  status?: string;
  note?: string | null;
};

export type SiteAddressAnalysisResponse = {
  status: string;
  input_address: string;
  resolved_address?: string | null;
  resolved_municipality?: string | null;
  municipality_name: string;
  municipality_match?: boolean;
  radius_km: number;
  coordinate?: { latitude: number; longitude: number } | null;
  geocode_source: string;
  geocode_confidence: string;
  geocode_candidates?: SiteGeocodeCandidate[];
  competitor_evidence: SiteEvidenceSummary;
  transit_evidence: SiteEvidenceSummary;
  commercial_activity_evidence: SiteEvidenceSummary;
  source_method: string;
  user_facing_note: string;
  warnings: string[];
  next_steps: string[];
};

export async function analyzeSiteAddress(
  payload: SiteAddressAnalysisRequest,
): Promise<SiteAddressAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/geo/site-address-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Site address analysis failed with status ${response.status}`);
  }

  return response.json();
}
