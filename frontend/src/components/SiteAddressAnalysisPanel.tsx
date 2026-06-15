import { useState } from "react";
import {
  analyzeSiteAddress,
  type SiteAddressAnalysisResponse,
} from "@/services/siteAddressApi";

type SiteAddressAnalysisPanelProps = {
  municipalityName: string;
  businessSubcategory: string;
  businessQuery?: string | null;
  radiusKm: number;
};

const formatKm = (value: number | string | null | undefined) =>
  Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

function EvidenceMiniList({
  title,
  summary,
}: {
  title: string;
  summary: SiteAddressAnalysisResponse["competitor_evidence"];
}) {
  const status = summary.status || "unknown";
  const statusLabel =
    status === "available"
      ? `${summary.count}`
      : status === "query_failed"
        ? "Unavailable"
        : status === "no_results"
          ? "0 found"
          : status === "skipped"
            ? "Skipped"
            : `${summary.count}`;

  return (
    <div className="rounded-xl border border-slate-200 bg-white/80 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-800">{title}</p>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
            status === "query_failed"
              ? "bg-amber-100 text-amber-700"
              : status === "available"
                ? "bg-emerald-100 text-emerald-700"
                : "bg-slate-100 text-slate-600"
          }`}
        >
          {statusLabel}
        </span>
      </div>

      {status === "query_failed" ? (
        <p className="mt-2 text-xs text-amber-700">
          Evidence query failed or timed out. This should not be interpreted as zero nearby evidence points.
        </p>
      ) : summary.nearest ? (
        <div className="mt-2 space-y-1">
          <p className="text-xs font-medium text-slate-700">Nearest: {summary.nearest.name}</p>
          <p className="text-xs text-slate-500">
            {formatKm(summary.nearest.distance_km)} km away · {summary.nearest.category}
          </p>
          {summary.nearest.address ? (
            <p className="text-xs text-slate-500">{summary.nearest.address}</p>
          ) : null}
        </div>
      ) : (
        <p className="mt-2 text-xs text-slate-500">
          {status === "skipped"
            ? summary.note || "This evidence check was skipped."
            : "The public OSM query completed, but no matching evidence points were found in this radius."}
        </p>
      )}
    </div>
  );
}

export default function SiteAddressAnalysisPanel({
  municipalityName,
  businessSubcategory,
  businessQuery,
  radiusKm,
}: SiteAddressAnalysisPanelProps) {
  const [addressLine, setAddressLine] = useState("");
  const [siteRadius, setSiteRadius] = useState(Math.min(Math.max(radiusKm || 1.5, 0.5), 5));
  const [result, setResult] = useState<SiteAddressAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    const cleanAddress = addressLine.trim();
    if (!cleanAddress) {
      setError("Enter a street address or site location first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await analyzeSiteAddress({
        address_line: cleanAddress,
        municipality_name: municipalityName,
        radius_km: siteRadius,
        business_subcategory: businessSubcategory || null,
        business_query: businessQuery || null,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Site analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const needsReview = result?.status === "needs_review" || result?.geocode_confidence === "limited" || result?.municipality_match === false;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Site-level screening</p>
        <h3 className="text-base font-semibold text-slate-900">Address Evidence Check</h3>
        <p className="text-xs text-slate-500">
          Screen a specific storefront/address using public geocoding, nearby OSM competitors, transit access,
          and commercial activity evidence.
        </p>
      </div>

      <div className="mt-4 space-y-3">
        <label className="block text-xs font-semibold text-slate-600">
          Address or site location
          <input
            value={addressLine}
            onChange={(event) => setAddressLine(event.target.value)}
            placeholder={`Example: 100 King St W, ${municipalityName}`}
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
          />
        </label>

        <label className="block text-xs font-semibold text-slate-600">
          Site evidence radius: {formatKm(siteRadius)} km
          <input
            type="range"
            min={0.5}
            max={5}
            step={0.5}
            value={siteRadius}
            onChange={(event) => setSiteRadius(Number(event.target.value))}
            className="mt-2 w-full"
          />
        </label>

        <button
          type="button"
          onClick={handleAnalyze}
          disabled={loading}
          className="w-full rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Checking site evidence..." : "Analyze this address"}
        </button>

        {error ? <p className="rounded-xl bg-red-50 p-3 text-xs text-red-700">{error}</p> : null}
      </div>

      {result ? (
        <div className="mt-4 space-y-3">
          <div className={`rounded-xl p-3 ${needsReview ? "bg-amber-50" : "bg-slate-50"}`}>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-800">
                {needsReview ? "Confirm address match" : "Site evidence available"}
              </p>
              <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-600">
                {result.geocode_confidence} geocode
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-600">{result.resolved_address || result.input_address}</p>
            {result.resolved_municipality ? (
              <p className="mt-1 text-xs text-slate-500">
                Resolved municipality: {result.resolved_municipality}
                {result.municipality_match === false ? ` · requested ${result.municipality_name}` : ""}
              </p>
            ) : null}
            {result.coordinate ? (
              <p className="mt-1 text-xs text-slate-500">
                {result.coordinate.latitude.toFixed(5)}, {result.coordinate.longitude.toFixed(5)}
              </p>
            ) : null}
          </div>

          {needsReview ? (
            <p className="rounded-xl bg-amber-50 p-3 text-xs text-amber-800">
              Address match is uncertain. Confirm the resolved address and municipality before using this site analysis.
            </p>
          ) : null}

          <div className="grid gap-2">
            <EvidenceMiniList title="Nearby competitors" summary={result.competitor_evidence} />
            <EvidenceMiniList title="Transit access" summary={result.transit_evidence} />
            <EvidenceMiniList title="Commercial activity" summary={result.commercial_activity_evidence} />
          </div>

          {result.geocode_candidates && result.geocode_candidates.length > 1 ? (
            <div className="rounded-xl border border-slate-200 bg-white/80 p-3">
              <p className="text-xs font-semibold text-slate-700">Other geocode candidates</p>
              <ul className="mt-2 space-y-1 text-xs text-slate-500">
                {result.geocode_candidates.slice(0, 3).map((candidate) => (
                  <li key={`${candidate.latitude}-${candidate.longitude}-${candidate.display_name}`}>
                    • {candidate.display_name}
                    {candidate.municipality_match ? " · municipality match" : ""}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">{result.user_facing_note}</p>

          {result.warnings.length ? (
            <ul className="space-y-1 text-xs text-slate-500">
              {result.warnings.slice(0, 5).map((warning) => (
                <li key={warning}>• {warning}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
