import { useMemo, useState } from "react";
import { LoaderCircle } from "lucide-react";
import {
  compareScenarioLocations,
  type LocationComparisonItem,
  type LocationComparisonResponse,
} from "@/services/locationComparisonApi";

type Props = {
  municipalityName: string;
  businessSubcategory: string;
  radiusKm: number;
  onApplyScenario?: (scenario: {
    municipality_name: string;
    business_subcategory: string;
    radius_km: number;
  }) => void;
};

function money(value: number): string {
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function scoreClass(score: number): string {
  if (score >= 70) return "text-emerald-700";
  if (score >= 45) return "text-amber-700";
  return "text-rose-700";
}

function riskClass(risk: string): string {
  const value = risk.toLowerCase();
  if (value === "low") return "bg-emerald-500/15 text-emerald-700 border-emerald-400/40";
  if (value === "medium") return "bg-amber-500/15 text-amber-700 border-amber-400/40";
  return "bg-rose-500/15 text-rose-700 border-rose-400/40";
}

export default function LocationComparisonPanel({
  municipalityName,
  businessSubcategory,
  radiusKm,
  onApplyScenario,
}: Props) {
  const [candidateText, setCandidateText] = useState(
    [municipalityName, "Waterloo", "Cambridge", "Guelph", "London", "Kingston"]
      .filter(Boolean)
      .join(", "),
  );
  const [radiusText, setRadiusText] = useState(`${radiusKm}, 3, 10`);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<LocationComparisonResponse | null>(null);

  const parsedCandidates = useMemo(
    () =>
      candidateText
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    [candidateText],
  );

  const parsedRadii = useMemo(
    () =>
      radiusText
        .split(",")
        .map((item) => Number(item.trim()))
        .filter((item) => Number.isFinite(item) && item >= 1 && item <= 25),
    [radiusText],
  );

  async function runComparison() {
    setLoading(true);
    setError(null);
    try {
      const result = await compareScenarioLocations({
        business_subcategory: businessSubcategory,
        base_municipality_name: municipalityName,
        candidate_municipalities: parsedCandidates,
        radius_options_km: parsedRadii.length ? parsedRadii : [radiusKm],
        max_results: 10,
      });
      setComparison(result);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Location comparison failed.");
    } finally {
      setLoading(false);
    }
  }

  const best = comparison?.best_option ?? null;

  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-xl shadow-slate-950/20">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-primary">
            Scenario Comparison Explorer
          </p>
          <h2 className="mt-1 text-xl font-semibold text-foreground">
            Compare nearby municipalities and radius options
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Compare alternative locations using the same score, demand, competition, rent, and risk measures as your current spot.
          </p>
        </div>
        <button
          type="button"
          onClick={runComparison}
          disabled={loading || !businessSubcategory}
          aria-busy={loading}
          className={`inline-flex min-w-44 items-center justify-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20 ${
            loading
              ? "border-primary bg-primary text-primary-foreground shadow-md ring-4 ring-primary/15 disabled:cursor-wait disabled:opacity-100"
              : "border-primary/40 bg-primary/10 text-primary hover:bg-primary/15 disabled:cursor-not-allowed disabled:opacity-50"
          }`}
        >
          {loading ? (
            <span className="inline-flex items-center gap-2" role="status" aria-live="polite">
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              Comparing locations
            </span>
          ) : (
            "Compare locations"
          )}
        </button>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_260px]">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Candidate municipalities
          </span>
          <input
            value={candidateText}
            onChange={(event) => setCandidateText(event.target.value)}
            className="mt-2 w-full rounded-xl border border-border bg-card px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary"
            placeholder="Kitchener, Waterloo, Cambridge, Guelph"
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Radius options km
          </span>
          <input
            value={radiusText}
            onChange={(event) => setRadiusText(event.target.value)}
            className="mt-2 w-full rounded-xl border border-border bg-card px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary"
            placeholder="3, 5, 10"
          />
        </label>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {comparison && comparison.results.length > 0 && comparison.results.every((r) => r.decision_score < 0) && (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-700">
          Every compared option currently scores below viability for this business type — the
          ranking shows the least risky option, not a recommended one. Consider a different
          business type, city, or radius.
        </div>
      )}

      {best && (
        <div className="mt-5 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700/90">Best current option</p>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                {best.municipality_name} · {Number(best.radius_km).toFixed(0)} km
              </h3>
              <p className="text-sm text-muted-foreground">
                Decision score <span className={`font-semibold ${scoreClass(best.decision_score)}`}>{best.decision_score.toFixed(1)}/100</span> · Revenue {money(best.predicted_monthly_net_revenue)} · Feasibility {best.predicted_feasibility_score.toFixed(1)}/100
              </p>
            </div>
            {onApplyScenario && (
              <button
                type="button"
                onClick={() =>
                  onApplyScenario({
                    municipality_name: best.municipality_name,
                    business_subcategory: best.business_subcategory,
                    radius_km: best.radius_km,
                  })
                }
                className="rounded-xl border border-emerald-300/40 bg-emerald-300/10 px-4 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-300/20"
              >
                Apply to dashboard
              </button>
            )}
          </div>
        </div>
      )}

      {comparison && comparison.results.length > 0 && (
        <div className="mt-5 overflow-hidden rounded-2xl border border-border">
          <div className="grid grid-cols-12 bg-card px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            <div className="col-span-1">Rank</div>
            <div className="col-span-3">Location</div>
            <div className="col-span-2">Decision score</div>
            <div className="col-span-2">Revenue</div>
            <div className="col-span-2">Feasibility</div>
            <div className="col-span-2">Risk</div>
          </div>
          {comparison.results.map((item: LocationComparisonItem) => (
            <div key={`${item.rank}-${item.municipality_name}-${item.radius_km}`} className="grid grid-cols-12 gap-2 border-t border-border px-4 py-3 text-sm text-foreground">
              <div className="col-span-1 font-semibold text-muted-foreground">#{item.rank}</div>
              <div className="col-span-3">
                <p className="font-semibold text-foreground">{item.municipality_name}</p>
                <p className="text-xs text-muted-foreground">
                  {Number(item.radius_km).toLocaleString(undefined, { maximumFractionDigits: 1 })} km radius
                  {typeof item.observed_competitor_count === "number"
                    ? ` · ${item.observed_competitor_count} mapped competitor${item.observed_competitor_count === 1 ? "" : "s"}`
                    : ""}
                </p>
              </div>
              <div className={`col-span-2 font-semibold ${scoreClass(item.decision_score)}`}>{item.decision_score.toFixed(1)}/100</div>
              <div className="col-span-2">{money(item.predicted_monthly_net_revenue)}</div>
              <div className="col-span-2">{item.predicted_feasibility_score.toFixed(1)}/100</div>
              <div className="col-span-2">
                <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${riskClass(item.predicted_risk_class)}`}>
                  {item.predicted_risk_class}
                </span>
              </div>
              {(item.strengths.length > 0 || item.concerns.length > 0) && (
                <div className="col-span-12 mt-2 grid gap-2 lg:grid-cols-2">
                  <div className="rounded-xl bg-emerald-500/5 p-3 text-xs text-emerald-700/90">
                    <span className="font-semibold text-emerald-700">Strengths: </span>
                    {item.strengths.join(" ") || "No major strength detected."}
                  </div>
                  <div className="rounded-xl bg-rose-500/5 p-3 text-xs text-rose-700/90">
                    <span className="font-semibold text-rose-700">Concerns: </span>
                    {item.concerns.join(" ") || "No major concern detected."}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {comparison && (
        <p className="mt-4 text-xs text-muted-foreground">{comparison.user_facing_note}</p>
      )}
    </section>
  );
}
