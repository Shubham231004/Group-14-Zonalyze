import { useMemo, useState } from "react";
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
  if (score >= 70) return "text-emerald-300";
  if (score >= 45) return "text-amber-300";
  return "text-rose-300";
}

function riskClass(risk: string): string {
  const value = risk.toLowerCase();
  if (value === "low") return "bg-emerald-500/15 text-emerald-200 border-emerald-400/40";
  if (value === "medium") return "bg-amber-500/15 text-amber-200 border-amber-400/40";
  return "bg-rose-500/15 text-rose-200 border-rose-400/40";
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
    <section className="rounded-2xl border border-slate-700/80 bg-slate-950/70 p-5 shadow-xl shadow-slate-950/20">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-300/80">
            Scenario Comparison Explorer
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-50">
            Compare nearby municipalities and radius options
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Rank alternative locations using the same prediction, demand, competition, rent, and risk evidence pipeline that powers the dashboard.
          </p>
        </div>
        <button
          type="button"
          onClick={runComparison}
          disabled={loading || !businessSubcategory}
          className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Comparing..." : "Compare locations"}
        </button>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_260px]">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Candidate municipalities
          </span>
          <input
            value={candidateText}
            onChange={(event) => setCandidateText(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
            placeholder="Kitchener, Waterloo, Cambridge, Guelph"
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Radius options km
          </span>
          <input
            value={radiusText}
            onChange={(event) => setRadiusText(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
            placeholder="3, 5, 10"
          />
        </label>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      {comparison && comparison.results.length > 0 && comparison.results.every((r) => r.decision_score < 0) && (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Every compared option currently scores below viability for this business type — the
          ranking shows the least risky option, not a recommended one. Consider a different
          business type, city, or radius.
        </div>
      )}

      {best && (
        <div className="mt-5 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200/90">Best current option</p>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-50">
                {best.municipality_name} · {Number(best.radius_km).toFixed(0)} km
              </h3>
              <p className="text-sm text-slate-300">
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
                className="rounded-xl border border-emerald-300/40 bg-emerald-300/10 px-4 py-2 text-sm font-semibold text-emerald-100 hover:bg-emerald-300/20"
              >
                Apply to dashboard
              </button>
            )}
          </div>
        </div>
      )}

      {comparison && comparison.results.length > 0 && (
        <div className="mt-5 overflow-hidden rounded-2xl border border-slate-800">
          <div className="grid grid-cols-12 bg-slate-900/90 px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
            <div className="col-span-1">Rank</div>
            <div className="col-span-3">Location</div>
            <div className="col-span-2">Score</div>
            <div className="col-span-2">Revenue</div>
            <div className="col-span-2">Feasibility</div>
            <div className="col-span-2">Risk</div>
          </div>
          {comparison.results.map((item: LocationComparisonItem) => (
            <div key={`${item.rank}-${item.municipality_name}-${item.radius_km}`} className="grid grid-cols-12 gap-2 border-t border-slate-800 px-4 py-3 text-sm text-slate-200">
              <div className="col-span-1 font-semibold text-slate-400">#{item.rank}</div>
              <div className="col-span-3">
                <p className="font-semibold text-slate-100">{item.municipality_name}</p>
                <p className="text-xs text-slate-500">
                  {Number(item.radius_km).toLocaleString(undefined, { maximumFractionDigits: 1 })} km radius
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
                  <div className="rounded-xl bg-emerald-500/5 p-3 text-xs text-emerald-100/90">
                    <span className="font-semibold text-emerald-200">Strengths: </span>
                    {item.strengths.join(" ") || "No major strength detected."}
                  </div>
                  <div className="rounded-xl bg-rose-500/5 p-3 text-xs text-rose-100/90">
                    <span className="font-semibold text-rose-200">Concerns: </span>
                    {item.concerns.join(" ") || "No major concern detected."}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {comparison && (
        <p className="mt-4 text-xs text-slate-500">{comparison.user_facing_note}</p>
      )}
    </section>
  );
}
