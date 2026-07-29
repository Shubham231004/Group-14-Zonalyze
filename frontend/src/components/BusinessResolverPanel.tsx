import { useMemo, useState } from "react";

import {
  resolveBusiness,
  type BusinessResolutionResponse,
} from "@/services/api";

export type BusinessInputMode = "catalog" | "custom";

type BusinessResolverPanelProps = {
  municipalityName: string;
  radiusKm: number;
  currentCatalogBusinessSubcategory: string;
  businessInputMode: BusinessInputMode;
  onBusinessInputModeChange: (mode: BusinessInputMode) => void;
  customBusinessQuery: string;
  onCustomBusinessQueryChange: (value: string) => void;
  useCustomBusinessForMap: boolean;
  onUseCustomBusinessForMapChange: (value: boolean) => void;
  onBusinessResolutionChange?: (resolution: BusinessResolutionResponse | null) => void;
  className?: string;
};

function confidenceBadgeClass(confidence?: string): string {
  const normalized = (confidence || "").toLowerCase();

  if (normalized === "high") {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-700";
  }

  if (normalized === "medium") {
    return "border-amber-500/40 bg-amber-500/10 text-amber-700";
  }

  if (normalized === "low" || normalized === "unresolved") {
    return "border-red-500/40 bg-red-500/10 text-red-200";
  }

  return "border-slate-600 bg-card text-muted-foreground";
}

function statusBadgeClass(status?: string): string {
  if (status === "resolved") {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-700";
  }

  if (status === "needs_review") {
    return "border-amber-500/40 bg-amber-500/10 text-amber-700";
  }

  return "border-slate-600 bg-card text-muted-foreground";
}

function formatScore(score?: number): string {
  if (score === undefined || score === null || Number.isNaN(score)) return "N/A";
  return `${Math.round(score * 100)}%`;
}

export default function BusinessResolverPanel({
  municipalityName,
  radiusKm,
  currentCatalogBusinessSubcategory,
  businessInputMode,
  onBusinessInputModeChange,
  customBusinessQuery,
  onCustomBusinessQueryChange,
  useCustomBusinessForMap,
  onUseCustomBusinessForMapChange,
  onBusinessResolutionChange,
  className = "",
}: BusinessResolverPanelProps) {
  const [resolution, setResolution] = useState<BusinessResolutionResponse | null>(null);
  const [isResolving, setIsResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedQuery = customBusinessQuery.trim();
  const canResolve = trimmedQuery.length >= 3 && !isResolving;
  const canUseForMap =
    resolution?.status === "resolved" &&
    Array.isArray(resolution.osm_tags) &&
    resolution.osm_tags.length > 0;

  const resolvedSummary = useMemo(() => {
    if (!resolution) return null;

    const parts = [
      resolution.normalized_business_name,
      resolution.primary_category,
      ...(resolution.secondary_categories || []),
    ].filter(Boolean);

    return parts.length ? parts.join(" · ") : "Business interpretation needs review";
  }, [resolution]);

  async function resolveBusinessIdea() {
    if (!canResolve) return;

    setIsResolving(true);
    setError(null);

    try {
      const payload = await resolveBusiness({
        business_query: trimmedQuery,
      });
      setResolution(payload);
      onBusinessResolutionChange?.(payload);

      if (payload.status === "resolved" && payload.osm_tags && payload.osm_tags.length > 0) {
        onUseCustomBusinessForMapChange(true);
      } else {
        onUseCustomBusinessForMapChange(false);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Business resolver failed.";
      setError(message);
      setResolution(null);
      onBusinessResolutionChange?.(null);
      onUseCustomBusinessForMapChange(false);
    } finally {
      setIsResolving(false);
    }
  }

  function switchMode(mode: BusinessInputMode) {
    onBusinessInputModeChange(mode);

    if (mode === "catalog") {
      onUseCustomBusinessForMapChange(false);
    }
  }

  return (
    <section className={`rounded-2xl border border-border bg-card p-5 shadow-xl ${className}`}>
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-primary">
            Business interpretation
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">
            How BestSpot reads your idea
          </h3>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Choose a standard business type for the fullest result, or describe a niche idea so BestSpot can find the right competitors on the map.
          </p>
        </div>

        <div className="rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
          {municipalityName} · {radiusKm} km
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <button
          type="button"
          onClick={() => switchMode("catalog")}
          className={`rounded-xl border p-4 text-left transition ${
            businessInputMode === "catalog"
              ? "border-primary/40 bg-primary/10"
              : "border-border bg-card hover:border-slate-500"
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-semibold text-foreground">Standard business type</span>
            <span className="text-xs text-muted-foreground">Full score available</span>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{currentCatalogBusinessSubcategory}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            Uses the complete scoring and comparison data available for this business type.
          </p>
        </button>

        <button
          type="button"
          onClick={() => switchMode("custom")}
          className={`rounded-xl border p-4 text-left transition ${
            businessInputMode === "custom"
              ? "border-primary/40 bg-primary/10"
              : "border-border bg-card hover:border-slate-500"
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-semibold text-foreground">Custom business idea</span>
            <span className="text-xs text-muted-foreground">Custom map search</span>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Describe a specific or niche idea and BestSpot will interpret what to look for nearby.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            You will see the interpretation before it changes the competitor map.
          </p>
        </button>
      </div>

      {businessInputMode === "custom" ? (
        <div className="mt-5 space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground" htmlFor="custom-business-query">
              Describe the business idea
            </label>
            <div className="mt-2 flex flex-col gap-3 md:flex-row">
              <input
                id="custom-business-query"
                type="text"
                value={customBusinessQuery}
                onChange={(event) => {
                  onCustomBusinessQueryChange(event.target.value);
                  setResolution(null);
                  setError(null);
                  onBusinessResolutionChange?.(null);
                  onUseCustomBusinessForMapChange(false);
                }}
                placeholder="Example: Esso gas station with Circle K convenience store"
                className="min-h-11 flex-1 rounded-xl border border-border bg-card px-4 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-primary"
              />
              <button
                type="button"
                onClick={resolveBusinessIdea}
                disabled={!canResolve}
                className="rounded-xl border border-primary/40 bg-primary/10 px-5 py-2 text-sm font-semibold text-primary transition hover:bg-primary/10 disabled:cursor-not-allowed disabled:border-border disabled:bg-card disabled:text-muted-foreground"
              >
                {isResolving ? "Resolving..." : "Resolve business"}
              </button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              BestSpot uses the nearest standard business type for financial scoring while your custom idea drives the competitor search.
            </p>
          </div>

          {error ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}

          {resolution ? (
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    BestSpot interpretation
                  </p>
                  <h4 className="mt-1 text-base font-semibold text-foreground">{resolvedSummary}</h4>
                </div>

                <div className="flex flex-wrap gap-2">
                  <span className={`rounded-full border px-3 py-1 text-xs ${statusBadgeClass(resolution.status)}`}>
                    {resolution.status}
                  </span>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs ${confidenceBadgeClass(
                      resolution.resolution_confidence,
                    )}`}
                  >
                    {resolution.resolution_confidence || "unknown"} · {formatScore(resolution.confidence_score)}
                  </span>
                  <span className="rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
                    {resolution.raw_ai_available ? "Interpretation ready" : "Needs review"}
                  </span>
                </div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-xs text-muted-foreground">Brand terms</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {(resolution.brand_terms || []).length ? resolution.brand_terms?.join(", ") : "None detected"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Specialty terms</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {(resolution.specialty_terms || []).length
                      ? resolution.specialty_terms?.join(", ")
                      : "None detected"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Source method</p>
                  <p className="mt-1 text-sm text-muted-foreground">{resolution.source_method || "unknown"}</p>
                </div>
              </div>

              <div className="mt-4">
                <p className="text-xs text-muted-foreground">Map categories</p>
                {(resolution.osm_tags || []).length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {resolution.osm_tags?.map((tag, index) => (
                      <span
                        key={`${tag.key}-${tag.value}-${index}`}
                        className="rounded-lg border border-primary/40 bg-primary/10 px-3 py-1 text-xs text-primary"
                        title={tag.reason || undefined}
                      >
                        {tag.key}={tag.value} · {Math.round(tag.confidence * 100)}% · {tag.tag_role}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="mt-1 text-sm text-amber-700">
                    BestSpot could not confirm map categories for this idea yet. Review the description before using it.
                  </p>
                )}
              </div>

              {(resolution.warnings || []).length ? (
                <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">
                    Warnings
                  </p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-700">
                    {resolution.warnings?.map((warning, index) => (
                      <li key={`${warning}-${index}`}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <label className="mt-4 flex items-start gap-3 rounded-xl border border-border bg-card p-3 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={useCustomBusinessForMap && canUseForMap}
                  disabled={!canUseForMap}
                  onChange={(event) => onUseCustomBusinessForMapChange(event.target.checked)}
                  className="mt-1"
                />
                <span>
                  <span className="font-semibold text-foreground">Use this interpretation for map evidence</span>
                  <br />
                  The competitor map will use this interpretation. The feasibility score will continue to use the nearest standard business type and will label that choice.
                </span>
              </label>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
