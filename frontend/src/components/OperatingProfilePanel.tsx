import { useEffect, useMemo, useRef, useState } from "react";
import { LoaderCircle } from "lucide-react";
import {
  generateOperatingProfile,
  type OperatingProfileResponse,
} from "@/services/operatingProfileApi";

type OperatingProfilePanelProps = {
  municipalityName: string;
  radiusKm: number;
  businessSubcategory?: string | null;
  businessQuery?: string | null;
  businessResolution?: Record<string, unknown> | null;
  customBusinessMapActive?: boolean;
  initialProfile?: OperatingProfileResponse | null;
};

function formatRange(section: OperatingProfileResponse["sections"][number]) {
  const range = section.range;
  if (!range) return "No range returned";
  if (range.display_value) return range.display_value;
  const values = [range.low, range.median, range.high].filter(
    (value) => typeof value === "number",
  );
  if (!values.length) return "No range returned";
  const [low, median, high] = [range.low, range.median, range.high];
  if (typeof low === "number" && typeof high === "number") {
    return `${low.toLocaleString()} – ${high.toLocaleString()} ${range.unit}`;
  }
  if (typeof median === "number") {
    return `${median.toLocaleString()} ${range.unit}`;
  }
  return `${values[0]?.toLocaleString()} ${range.unit}`;
}

function confidenceClass(confidence: string) {
  const normalized = confidence.toLowerCase();
  if (normalized.includes("high")) return "border-emerald-400/50 bg-emerald-500/10 text-emerald-700";
  if (normalized.includes("moderate")) return "border-amber-400/50 bg-amber-500/10 text-amber-700";
  if (normalized.includes("limited")) return "border-sky-500 bg-sky-100 text-sky-900";
  return "border-slate-500 bg-slate-100 text-slate-800";
}

const confidenceLabels: Record<string, string> = {
  high: "High",
  moderate: "Moderate",
  limited: "Limited",
  low: "Low",
  unavailable: "Unavailable",
};

const sourceMethodLabels: Record<string, string> = {
  local_ai_benchmark_operating_profile_with_available_context: "AI estimate",
  local_ai_unavailable_no_static_formula_fallback: "Unavailable",
};

function confidenceLabel(value: string) {
  return confidenceLabels[value.trim().toLowerCase()] ?? "Estimated";
}

function sourceMethodLabel(value: string) {
  return sourceMethodLabels[value.trim().toLowerCase()] ?? "Estimate";
}

export default function OperatingProfilePanel({
  municipalityName,
  radiusKm,
  businessSubcategory,
  businessQuery,
  businessResolution,
  customBusinessMapActive = false,
  initialProfile = null,
}: OperatingProfilePanelProps) {
  const [profile, setProfile] = useState<OperatingProfileResponse | null>(initialProfile);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProfile(initialProfile);
    setError(null);
  }, [initialProfile]);

  const activeBusinessLabel = useMemo(() => {
    if (customBusinessMapActive && businessQuery?.trim()) return businessQuery.trim();
    return businessSubcategory || businessQuery || "Selected business";
  }, [businessQuery, businessSubcategory, customBusinessMapActive]);

  const canGenerate = Boolean(municipalityName && radiusKm && (businessQuery || businessSubcategory));

  async function handleGenerate() {
    if (!canGenerate) return;
    setLoading(true);
    setError(null);
    try {
      const result = await generateOperatingProfile({
        municipality_name: municipalityName,
        radius_km: radiusKm,
        business_query: businessQuery || null,
        business_subcategory: businessSubcategory || null,
        business_resolution: businessResolution || null,
      });
      setProfile(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operating profile failed.");
    } finally {
      setLoading(false);
    }
  }

  // Auto-fetch the operating profile when the scenario changes, on its own
  // (non-blocking) schedule so it never delays the main dashboard. Debounced,
  // and guarded so the same scenario is not re-fetched (the backend also caches).
  const scenarioKey = useMemo(
    () =>
      JSON.stringify({
        municipalityName,
        radiusKm,
        businessSubcategory: businessSubcategory ?? null,
        businessQuery: businessQuery ?? null,
        customBusinessMapActive,
      }),
    [municipalityName, radiusKm, businessSubcategory, businessQuery, customBusinessMapActive],
  );
  const lastFetchedKeyRef = useRef<string | null>(null);
  const handleGenerateRef = useRef(handleGenerate);
  handleGenerateRef.current = handleGenerate;

  useEffect(() => {
    if (!canGenerate) return;
    if (lastFetchedKeyRef.current === scenarioKey) return;
    const timer = window.setTimeout(() => {
      lastFetchedKeyRef.current = scenarioKey;
      void handleGenerateRef.current();
    }, 800);
    return () => window.clearTimeout(timer);
  }, [scenarioKey, canGenerate]);

  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-xl">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
            Operating cost guide
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">
            Estimated operating assumptions for {activeBusinessLabel}
          </h3>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Planning ranges for lease, space, staffing, customer economics, utilities, and marketing — grounded in the active business and location. Treat them as a starting point, then confirm with local quotes.
          </p>
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={!canGenerate || loading}
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
              {profile ? "Refreshing profile" : "Generating profile"}
            </span>
          ) : profile ? (
            "Refresh profile"
          ) : (
            "Generate profile"
          )}
        </button>
      </div>

      {!canGenerate && (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 p-3 text-sm text-amber-700">
          Select a municipality and business input before generating the operating profile.
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-xl border border-rose-400/30 bg-rose-500/10 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {profile && (
        <div className="mt-5 space-y-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${confidenceClass(profile.overall_confidence)}`}>
                {confidenceLabel(profile.overall_confidence)}
              </span>
              <span className="rounded-full border border-slate-600 bg-muted px-3 py-1 text-xs text-foreground">
                {sourceMethodLabel(profile.source_method)}
              </span>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">{profile.user_facing_note}</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {profile.sections.map((section) => (
              <article key={section.key} className="rounded-xl border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-base font-semibold text-foreground">{section.title}</h4>
                    <p className="mt-1 text-sm text-primary">{formatRange(section)}</p>
                  </div>
                  <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${confidenceClass(section.confidence)}`}>
                    {confidenceLabel(section.confidence)}
                  </span>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{section.summary}</p>

                {section.reasoning.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Reasoning</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                      {section.reasoning.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {section.evidence_used.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence used</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                      {section.evidence_used.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {section.limitations.length > 0 && (
                  <div className="mt-3 rounded-lg border border-border bg-card p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Limitations</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                      {section.limitations.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </article>
            ))}
          </div>

          {(profile.warnings.length > 0 || profile.next_data_needed.length > 0) && (
            <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 p-4">
              <p className="text-sm font-semibold text-amber-700">Operating profile notes</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-800/90">
                {[...profile.warnings, ...profile.next_data_needed].map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
