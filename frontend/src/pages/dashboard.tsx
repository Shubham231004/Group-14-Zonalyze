// frontend/src/pages/dashboard.tsx

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart4,
  BrainCircuit,
  Cpu,
  Database,
  Gauge,
  DollarSign,
  Download,
  GitCompare,
  History,
  Save,
  MapPin,
  Navigation, 
  Settings,
  Signal,
  ShieldCheck,
  Info,
  Store,
  Target,
  TrendingUp,
  Users,
  MessageSquare,
  X,
  ChevronRight,
  HelpCircle,
} from "lucide-react";
import { Link } from "wouter";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { motion, AnimatePresence } from "framer-motion";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { useToast } from "@/hooks/use-toast";

import MarketMap from "@/components/MarketMap";
import ScenarioAIChat from "@/components/ScenarioAIChat";
import ScenarioSupportPanel from "@/components/ScenarioSupportPanel";
import AccountButton from "@/components/AccountButton";
import BusinessResolverPanel, {
  type BusinessInputMode,
} from "@/components/BusinessResolverPanel";

import OperatingProfilePanel from "@/components/OperatingProfilePanel";
import LocationComparisonPanel from "@/components/LocationComparisonPanel";

import {
  analyzeScenario,
  clearScenarioHistory,
  compareScenarioHistory,
  fetchBusinessSubcategories,
  fetchDashboardSummary,
  fetchMunicipalities,
  fetchModelStatus,
  fetchGeospatialMarketMap,
  fetchScenarioHistory,
  generateFeasibilityReport,
  resolveBusiness,
  runSystemValidation,
  saveScenarioToHistory,
  type BusinessResolutionResponse,
  type BusinessSubcategoryOption,
  type DashboardSummaryResponse,
  type GeospatialMarketContext,
  type GeospatialMarketMapRequest,
  type MunicipalityOption,
  type ModelStatusResponse,
  type ScenarioComparisonResponse,
  type ScenarioHistoryItem,
  type SystemValidationResponse,
} from "@/services/api";

const DEFAULT_MUNICIPALITY = "Kitchener";
const DEFAULT_BUSINESS = "Indian Grocery Store";
const DEFAULT_RADIUS = 5;

function indicatorLabelForCompetition(indicator: string) {
  if (indicator === "green") return "LOW";
  if (indicator === "yellow") return "MODERATE";
  if (indicator === "red") return "HIGH";
  return "UNKNOWN";
}

function indicatorLabelForRevenue(indicator: string) {
  if (indicator === "green") return "POSITIVE";
  if (indicator === "yellow") return "WATCH";
  if (indicator === "red") return "NEGATIVE";
  return "UNKNOWN";
}

function indicatorLabelForRisk(indicator: string) {
  if (indicator === "green") return "LOW";
  if (indicator === "yellow") return "MEDIUM";
  if (indicator === "red") return "HIGH";
  return "UNKNOWN";
}

function indicatorTextClass(indicator: string) {
  if (indicator === "green") return "text-emerald-600";
  if (indicator === "yellow") return "text-accent";
  if (indicator === "red") return "text-destructive";
  return "text-foreground";
}

function indicatorBadgeClass(indicator: string) {
  if (indicator === "green") return "text-emerald-600 border-emerald-400/30 bg-emerald-500/5";
  if (indicator === "yellow") return "text-accent border-accent/30 bg-accent/5";
  if (indicator === "red") return "text-destructive border-destructive/30 bg-destructive/5";
  return "text-foreground border-border";
}

function recommendationBadgeClass(recommendation?: string) {
  if (recommendation === "recommended")
    return "text-emerald-600 border-emerald-400/30 bg-emerald-500/5";
  if (recommendation === "borderline") return "text-accent border-accent/30 bg-accent/5";
  if (recommendation === "not_recommended")
    return "text-destructive border-destructive/30 bg-destructive/5";
  return "text-foreground border-border";
}

function getMetric(data: DashboardSummaryResponse | null, key: string) {
  return (
    data?.people_location_packet.metrics.find((m) => m.key === key)?.value ?? 0
  );
}

// Generates synthetic population data for charts
function buildDemographicChartData(data: DashboardSummaryResponse | null) {
  return [
    { group: "Youth", value: getMetric(data, "students_pct") },
    { group: "Families", value: getMetric(data, "families_pct") },
    { group: "Seniors", value: getMetric(data, "retirees_pct") },
    { group: "Diversity", value: getMetric(data, "diversity_index_0_100") },
  ].filter((item) => Number.isFinite(item.value));
}

function buildPopulationTrend(population: number) {
  const safePopulation = Math.max(population, 1);

  return Array.from({ length: 12 }).map((_, i) => {
    const variance = (i % 2 === 0 ? 1 : -1) * safePopulation * 0.015;
    return {
      time: `${i * 2}h`,
      value: Math.round(safePopulation + variance),
    };
  });
}

function buildRiskProbabilityData(data: DashboardSummaryResponse | null) {
  const probs = data?.ml_prediction?.risk_probabilities ?? {};

  return Object.entries(probs).map(([riskClass, probability]) => ({
    riskClass: riskClass.toUpperCase(),
    probability: Math.round(probability * 100),
  }));
}

function formatCurrency(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";

  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-CA", { maximumFractionDigits: 0 }).format(
    value,
  );
}

function formatPercent(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  return `${(value * 100).toFixed(1)}%`;
}

function credibilityClass(level?: string) {
  if (level === "strong") return "text-emerald-600 border-emerald-400/30 bg-emerald-500/5";
  if (level === "moderate") return "text-primary border-primary/30 bg-primary/5";
  if (level === "limited") return "text-accent border-accent/30 bg-accent/5";
  return "text-destructive border-destructive/30 bg-destructive/5";
}

function readableRecommendation(value?: string) {
  if (!value) return "No recommendation";
  return value.replace(/_/g, " ").toUpperCase();
}

function MarketMapPanel({
  geoContext,
  isLoading,
  error,
  onRetry,
}: {
  geoContext: GeospatialMarketContext | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (!geoContext) {
    return (
      <Card className="scada-panel border-border">
        <CardContent className="p-8 flex flex-col items-center justify-center min-h-[400px]">
          {error && !isLoading ? (
            <>
              <Signal className="w-8 h-8 text-destructive mb-3" />
              <p className="text-xs font-mono lcd-text text-muted-foreground text-center max-w-sm mb-4">
                The market map could not be loaded. This does not affect your
                scenario analysis.
              </p>
              <Button variant="outline" size="sm" onClick={onRetry}>
                Retry map
              </Button>
            </>
          ) : (
            <>
              <Signal className="w-8 h-8 text-primary animate-pulse mb-3" />
              <p className="text-xs font-mono lcd-text text-muted-foreground">
                Geospatial market context is loading...
              </p>
            </>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <MarketMap
      geoContext={geoContext}
      className="scada-panel border-border shadow-2xl rounded-2xl overflow-hidden min-h-[500px]"
    />
  );
}

export default function Dashboard() {
  const { toast } = useToast();

  const [radius, setRadius] = useState<number[]>([DEFAULT_RADIUS]);
  const [municipalityName, setMunicipalityName] =
    useState(DEFAULT_MUNICIPALITY);
  // Optional specific street address. When set, the whole analysis (radius, map,
  // competitors, transit) anchors on this exact point instead of the city centre.
  const [siteAddress, setSiteAddress] = useState("");
  const [businessSubcategory, setBusinessSubcategory] =
    useState(DEFAULT_BUSINESS);
  const [businessInputMode, setBusinessInputMode] =
    useState<BusinessInputMode>("catalog");
  const [customBusinessQuery, setCustomBusinessQuery] = useState("");
  const [businessResolution, setBusinessResolution] =
    useState<BusinessResolutionResponse | null>(null);
  const [useCustomBusinessForMap, setUseCustomBusinessForMap] =
    useState(false);

  const [municipalityOptions, setMunicipalityOptions] = useState<
    MunicipalityOption[]
  >([]);
  const [businessOptions, setBusinessOptions] = useState<
    BusinessSubcategoryOption[]
  >([]);
  const [dashboardData, setDashboardData] =
    useState<DashboardSummaryResponse | null>(null);

  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isUpdating, setIsUpdating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [systemValidation, setSystemValidation] =
    useState<SystemValidationResponse | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [scenarioHistory, setScenarioHistory] = useState<ScenarioHistoryItem[]>([]);
  const [geoContext, setGeoContext] = useState<GeospatialMarketContext | null>(null);
  // The market map loads independently of the scenario analysis so a slow or
  // failed Overpass call never blocks the UI or fails the scenario report.
  const [isGeoLoading, setIsGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [scenarioComparison, setScenarioComparison] =
    useState<ScenarioComparisonResponse | null>(null);
  const [isSavingScenario, setIsSavingScenario] = useState(false);
  const [isComparingScenarios, setIsComparingScenarios] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);

  // Redesign & loader state managers
  const [isScenarioSelected, setIsScenarioSelected] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "map" | "evidence" | "benchmarks" | "history">("map");
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Simulated Loader Progress States
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingStep, setLoadingStep] = useState("");

  const debounceRef = useRef<number | null>(null);
  const initialLoadDoneRef = useRef(false);
  // Monotonic id so only the most recent market-map request updates the map.
  // Without this, slow out-of-order responses overwrite each other and the map
  // flickers between locations (e.g. Kitchener → Cambridge).
  const geoRequestSeq = useRef(0);

  const ml = dashboardData?.ml_prediction ?? null;
  const explanation = dashboardData?.prediction_explanation ?? null;
  const breakdown = dashboardData?.analysis_breakdown ?? null;
  const credibility = dashboardData?.prediction_credibility ?? null;
  // Prefer real, live OpenStreetMap competition evidence (from the market map)
  // over the catalog seed / formula proxy from the dashboard response.
  const osmCompetitionEvidence =
    (geoContext as any)?.competition_evidence_source === "openstreetmap_live"
      ? (geoContext as any)?.competition_evidence ?? null
      : null;
  const competitionEvidence =
    osmCompetitionEvidence ?? dashboardData?.competition_evidence ?? null;
  const competitionIsLiveOsm = Boolean(osmCompetitionEvidence);
  const leaseCostEvidence = dashboardData?.lease_cost_evidence ?? null;
  const demandEvidence = dashboardData?.demand_evidence ?? null;
  const recommendationDecision = dashboardData?.recommendation_decision ?? null;
  const operatingProfile = (dashboardData as any)?.operating_profile ?? null;
  const populationValue = getMetric(dashboardData, "population_total");
  const studentPct = getMetric(dashboardData, "students_pct");
  const familiesPct = getMetric(dashboardData, "families_pct");
  const retireesPct = getMetric(dashboardData, "retirees_pct");
  const density = getMetric(dashboardData, "population_density_per_km2");
  const medianIncome = getMetric(
    dashboardData,
    "household_median_total_income_2020",
  );

  const demographicChartData = useMemo(
    () => buildDemographicChartData(dashboardData),
    [dashboardData],
  );
  const populationTrend = useMemo(
    () => buildPopulationTrend(populationValue),
    [populationValue],
  );
  const riskProbabilityData = useMemo(
    () => buildRiskProbabilityData(dashboardData),
    [dashboardData],
  );

  const shouldUseCustomBusinessMap =
    businessInputMode === "custom" &&
    useCustomBusinessForMap &&
    customBusinessQuery.trim().length > 0 &&
    businessResolution?.status === "resolved";

  const activeGeoPayload = useMemo(() => {
    const site_address = siteAddress.trim() || undefined;
    if (shouldUseCustomBusinessMap) {
      return {
        municipality_name: municipalityName,
        site_address,
        business_query: customBusinessQuery.trim(),
        radius_km: radius[0],
      };
    }

    return {
      municipality_name: municipalityName,
      site_address,
      business_subcategory: businessSubcategory,
      radius_km: radius[0],
    };
  }, [
    shouldUseCustomBusinessMap,
    municipalityName,
    siteAddress,
    customBusinessQuery,
    radius,
    businessSubcategory,
  ]);

  // Fetch the market map on its own loading/error track. Never throws to the
  // caller, so scenario analysis and startup can proceed regardless of the map.
  const loadGeoContext = useCallback(async (payload: GeospatialMarketMapRequest) => {
    // Tag this request; only the latest one is allowed to update the map, so slow
    // out-of-order responses can't overwrite the current location (no flicker).
    // Duplicate-hit protection lives in the backend cache, so every change fetches.
    const seq = ++geoRequestSeq.current;
    setIsGeoLoading(true);
    setGeoError(null);
    try {
      const geoResponse = await fetchGeospatialMarketMap(payload);
      if (seq !== geoRequestSeq.current) return; // superseded by a newer request
      setGeoContext(geoResponse);
    } catch (error) {
      if (seq !== geoRequestSeq.current) return; // superseded — ignore this failure
      // Clear the previous result so we never keep showing a different location's
      // map (the old "I picked a new city but still see Kitchener" bug). The map
      // panel then shows a retry tied to the requested input.
      setGeoContext(null);
      setGeoError(
        error instanceof Error
          ? error.message
          : "The market map could not be loaded from the backend.",
      );
    } finally {
      if (seq === geoRequestSeq.current) setIsGeoLoading(false);
    }
  }, []);

  // One pick-or-type business field: a catalog pick runs the ML-safe path; a typed
  // idea drives the map via business_query and is resolved so the nearest trained
  // type can produce a (clearly-labelled) feasibility score.
  const handleBusinessChange = useCallback(
    (value: string) => {
      const isCatalog = businessOptions.some((b) => b.business_subcategory === value);
      if (isCatalog || !value.trim()) {
        setBusinessInputMode("catalog");
        setBusinessSubcategory(value);
        setUseCustomBusinessForMap(false);
        setCustomBusinessQuery("");
        setBusinessResolution(null);
        return;
      }
      setBusinessInputMode("custom");
      setCustomBusinessQuery(value.trim());
      setUseCustomBusinessForMap(true);
      resolveBusiness({ business_query: value.trim(), municipality_name: municipalityName })
        .then(setBusinessResolution)
        .catch(() => setBusinessResolution(null));
    },
    [businessOptions, municipalityName],
  );

  // Score wiring: a resolved free-text idea scores off its nearest trained type,
  // so the existing analyze-scenario calls (which read businessSubcategory) get it
  // for free. The map still uses business_query (shouldUseCustomBusinessMap).
  useEffect(() => {
    if (businessInputMode === "custom" && businessResolution?.nearest_catalog_subcategory) {
      setBusinessSubcategory(businessResolution.nearest_catalog_subcategory);
    }
  }, [businessInputMode, businessResolution]);

  useEffect(() => {
    async function loadStartupData() {
      try {
        setIsInitialLoading(true);

        // Only UI-critical calls block the initial render. The market map is
        // deliberately excluded so the analysis controls appear immediately
        // even when Overpass is slow.
        const [municipalitiesData, businessData, modelStatusData, historyData] = await Promise.all([
          fetchMunicipalities(),
          fetchBusinessSubcategories(),
          fetchModelStatus().catch(() => null),
          fetchScenarioHistory().catch(() => null),
        ]);

        setMunicipalityOptions(municipalitiesData.municipalities);
        setBusinessOptions(businessData.business_subcategories);
        setModelStatus(modelStatusData);
        setScenarioHistory(historyData?.scenarios ?? []);

        let firstDashboard: DashboardSummaryResponse;
        try {
          firstDashboard = await fetchDashboardSummary();
        } catch {
          firstDashboard = await analyzeScenario({
            municipality_name: DEFAULT_MUNICIPALITY,
            business_subcategory: DEFAULT_BUSINESS,
            radius_km: DEFAULT_RADIUS,
          });
        }

        setDashboardData(firstDashboard);
        setMunicipalityName(
          firstDashboard.municipality_name || DEFAULT_MUNICIPALITY,
        );
        setBusinessSubcategory(
          firstDashboard.business_subcategory || DEFAULT_BUSINESS,
        );
        setRadius([firstDashboard.radius_km || DEFAULT_RADIUS]);
        setLastUpdate(new Date());
        initialLoadDoneRef.current = true;

        // Kick off the map independently — do not await it on the critical path.
        void loadGeoContext({
          municipality_name: firstDashboard.municipality_name || DEFAULT_MUNICIPALITY,
          business_subcategory: firstDashboard.business_subcategory || DEFAULT_BUSINESS,
          radius_km: firstDashboard.radius_km || DEFAULT_RADIUS,
        });
      } catch (error) {
        toast({
          title: "Dashboard loading failed",
          description:
            error instanceof Error
              ? error.message
              : "Could not load the dashboard data from the backend.",
          variant: "destructive",
        });
      } finally {
        setIsInitialLoading(false);
      }
    }

    loadStartupData();
  }, [toast, loadGeoContext]);

  useEffect(() => {
    if (!initialLoadDoneRef.current) return;

    if (debounceRef.current) {
      window.clearTimeout(debounceRef.current);
    }

    debounceRef.current = window.setTimeout(async () => {
      try {
        setIsUpdating(true);

        const response = await analyzeScenario({
          municipality_name: municipalityName,
          business_subcategory: businessSubcategory,
          radius_km: radius[0],
        });

        setDashboardData(response);
        setLastUpdate(new Date());
      } catch (error) {
        toast({
          title: "Scenario analysis failed",
          description:
            error instanceof Error
              ? error.message
              : "Could not update the dashboard from the backend.",
          variant: "destructive",
        });
      } finally {
        setIsUpdating(false);
      }

      // Refresh the map independently. A map failure surfaces in the map panel
      // itself (with retry) and must not fail the scenario analysis above.
      void loadGeoContext(activeGeoPayload as GeospatialMarketMapRequest);
    }, 450);

    return () => {
      if (debounceRef.current) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [
    municipalityName,
    businessSubcategory,
    radius,
    activeGeoPayload,
    businessInputMode,
    customBusinessQuery,
    useCustomBusinessForMap,
    businessResolution?.status,
    toast,
    loadGeoContext,
  ]);

  // Real loading sequence: the progress bar tracks the ACTUAL backend work and
  // only completes once the analysis (and the map, within a bounded wait) is back,
  // so the workspace appears fully populated instead of animating on a fake timer.
  const handleStartAnalysis = async () => {
    setIsAnalyzing(true);
    setLoadingProgress(0);
    setLoadingStep("Loading Statistics Canada Census demographic datasets...");

    const stepMessages: Record<number, string> = {
      15: "Connecting to PostgreSQL; retrieving catchment populations...",
      35: "Running Random Forest ML estimators for feasibility & net revenue...",
      55: "Resolving the analysis location & business interpretation...",
      72: "Fetching live map evidence from OpenStreetMap...",
      88: "Compiling the decision-support recommendation...",
    };

    // Ease the bar toward 90% while the real work runs; hold there until data lands.
    const interval = window.setInterval(() => {
      setLoadingProgress((prev) => {
        const next = prev + 1;
        if (next >= 90) return 90;
        if (stepMessages[next]) setLoadingStep(stepMessages[next]);
        return next;
      });
    }, 45);

    try {
      // Feasibility numbers (ML/census) — fast, no external APIs.
      const response = await analyzeScenario({
        municipality_name: municipalityName,
        business_subcategory: businessSubcategory,
        radius_km: radius[0],
      });
      setDashboardData(response);
      setLastUpdate(new Date());

      // Every completed search lands in the signed-in user's history (fire and
      // forget — a failed save must never break the analysis), so returning
      // users see what they've already checked.
      saveScenarioToHistory({
        municipality_name: municipalityName,
        business_subcategory: businessSubcategory,
        radius_km: radius[0],
      })
        .then(() => fetchScenarioHistory())
        .then((history) => setScenarioHistory(history?.scenarios ?? []))
        .catch(() => {});

      // Map/competitors — bounded so a slow or rate-limited Overpass can't stall the
      // whole screen. If it isn't ready in time, the workspace still opens and the
      // map finishes (or shows its honest retry state) on its own.
      const mapLoad = loadGeoContext(activeGeoPayload as GeospatialMarketMapRequest);
      await Promise.race([
        mapLoad,
        new Promise((resolve) => window.setTimeout(resolve, 18000)),
      ]);
    } catch (error) {
      toast({
        title: "Analysis failed",
        description:
          error instanceof Error
            ? error.message
            : "Could not run the analysis. Make sure the backend is running.",
        variant: "destructive",
      });
    } finally {
      window.clearInterval(interval);
      setLoadingProgress(100);
      setLoadingStep("Ready.");
      setActiveTab("map"); // land on the map — the competitors ARE the excitement
      setIsScenarioSelected(true);
      setIsAnalyzing(false);
    }
  };

  const handleExport = async () => {
    try {
      setIsExporting(true);

      const report = await generateFeasibilityReport({
        municipality_name: municipalityName,
        business_subcategory: businessSubcategory,
        radius_km: radius[0],
      });

      const blob = new Blob([report.report_text], {
        type: report.content_type || "text/plain",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = report.filename || "bestspot-location-report.txt";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: "Report exported",
        description:
          "The feasibility report was generated from the latest backend scenario.",
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Report export failed",
        description:
          error instanceof Error
            ? error.message
            : "Could not generate the feasibility report.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleRunValidation = async () => {
    try {
      setIsValidating(true);
      const validation = await runSystemValidation();
      setSystemValidation(validation);

      toast({
        title:
          validation.overall_status === "passed"
            ? "System validation passed"
            : "System validation found issues",
        description: `${validation.passed_checks}/${validation.total_checks} validation checks passed.`,
        variant:
          validation.overall_status === "passed" ? "default" : "destructive",
        duration: 3500,
      });
    } catch (error) {
      toast({
        title: "System validation failed",
        description:
          error instanceof Error
            ? error.message
            : "Could not run the backend validation check.",
        variant: "destructive",
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleSaveScenario = async () => {
    try {
      setIsSavingScenario(true);
      const savedScenario = await saveScenarioToHistory({
        municipality_name: municipalityName,
        business_subcategory: businessSubcategory,
        radius_km: radius[0],
      });
      const history = await fetchScenarioHistory();
      setScenarioHistory(history.scenarios);

      toast({
        title: "Scenario saved",
        description: `${savedScenario.business_subcategory} in ${savedScenario.municipality_name} was added to comparison history.`,
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Could not save scenario",
        description:
          error instanceof Error
            ? error.message
            : "The scenario could not be saved to history.",
        variant: "destructive",
      });
    } finally {
      setIsSavingScenario(false);
    }
  };

  const handleCompareScenarios = async () => {
    try {
      setIsComparingScenarios(true);
      const comparison = await compareScenarioHistory();
      const history = await fetchScenarioHistory();
      setScenarioHistory(history.scenarios);
      setScenarioComparison(comparison);

      toast({
        title: comparison.compared_count > 1 ? "Scenario comparison ready" : "Save more scenarios",
        description: comparison.comparison_summary,
        duration: 4500,
      });
    } catch (error) {
      toast({
        title: "Scenario comparison failed",
        description:
          error instanceof Error
            ? error.message
            : "The saved scenarios could not be compared.",
        variant: "destructive",
      });
    } finally {
      setIsComparingScenarios(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      const history = await clearScenarioHistory();
      setScenarioHistory(history.scenarios);
      setScenarioComparison(null);
      toast({
        title: "Scenario history cleared",
        description: "Saved scenario comparisons were removed from the local backend history file.",
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Could not clear history",
        description:
          error instanceof Error
            ? error.message
            : "Scenario history could not be cleared.",
        variant: "destructive",
      });
    }
  };

  if (isInitialLoading) {
    return (
      <div className="app-loading-shell">
        <div className="app-loading-card">
          <span className="brand-pin text-5xl" aria-hidden />
          <div><h3>BestSpot</h3><p>Preparing your location workspace…</p></div>
          <div className="loading-track"><span /></div>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="app-loading-shell">
        <Card className="w-full max-w-md border-border bg-card p-7 text-center shadow-sm">
          <AlertTriangle className="mx-auto h-8 w-8 text-primary" />
          <h2 className="mt-4 text-2xl font-semibold">We could not load your market data.</h2>
          <p className="mt-2 text-sm text-muted-foreground">Check the connection and try once more. Your saved scenarios are not affected.</p>
          <Button className="mt-6 rounded-full" onClick={() => window.location.reload()}>Try again</Button>
        </Card>
      </div>
    );
  }

  if (isAnalyzing) {
    return (
      <div className="analysis-loading-shell">
        <div className="analysis-loading-card">
          <div className="analysis-loading-map" aria-hidden>
            <div className="analysis-road analysis-road-one" /><div className="analysis-road analysis-road-two" />
            <div className="analysis-radius" /><span className="brand-pin pin-drop text-5xl" />
          </div>
          <div className="analysis-loading-copy">
            <p className="eyebrow">Building your decision view</p>
            <h2>Checking {municipalityName} for your {businessSubcategory.toLowerCase()}.</h2>
            <p>{loadingStep}</p>
            <div className="analysis-progress"><span style={{ width: `${loadingProgress}%` }} /></div>
            <div className="flex items-center justify-between text-xs text-muted-foreground"><span>Map · competition · demand · costs</span><strong>{loadingProgress}%</strong></div>
          </div>
        </div>
      </div>
    );
  }

  if (!isScenarioSelected) {
    return (
      <div className="scenario-page">
        <header className="app-topbar">
          <div className="app-brand"><span className="brand-pin text-3xl" aria-hidden /><div><h1>BestSpot<span>.biz</span></h1><p>Location intelligence for your next business</p></div></div>
          <div className="flex items-center gap-3"><span className="region-badge">Ontario</span><AccountButton /></div>
        </header>

        <main className="scenario-main">
          <section className="scenario-intro">
            <p className="eyebrow">Start with the question that matters</p>
            <h2>Will your business work <em>there?</em></h2>
            <p className="scenario-lead">Choose the idea and location. We will show what surrounds it, what it may cost, and whether another spot looks stronger.</p>
            <div className="scenario-preview">
              <div className="scenario-preview-map">
                <div className="preview-street street-one" /><div className="preview-street street-two" /><div className="preview-street street-three" />
                <div className="preview-radius" /><span className="brand-pin text-4xl" aria-hidden />
                <i className="preview-dot dot-one" /><i className="preview-dot dot-two" /><i className="preview-dot dot-three" />
              </div>
              <div className="scenario-preview-copy">
                <span className="preview-number">82</span>
                <div><strong>A clear answer, not a data dump.</strong><p>Map first. Competition beside it. Costs and comparisons when you need them.</p></div>
              </div>
            </div>
            <div className="scenario-promises">
              <span><MapPin /> Exact address or city centre</span><span><Users /> Real local market context</span><span><GitCompare /> Compare every promising spot</span>
            </div>
          </section>

          <Card className="scenario-form-card">
            <CardHeader className="scenario-form-header"><p className="eyebrow">New location check</p><CardTitle>Tell us about the spot</CardTitle><p>Four quick choices. About a minute.</p></CardHeader>
            <CardContent className="space-y-5 p-6">
              <div className="form-field"><label><Navigation /> City or town</label><SearchableSelect value={municipalityName} onValueChange={setMunicipalityName} options={municipalityOptions.map((city) => ({ value: city.municipality_name, label: city.label }))} placeholder="Choose a municipality" searchPlaceholder="Search any Ontario city…" allowCustomValue /></div>
              <div className="form-field"><label><MapPin /> Exact storefront <small>optional</small></label><Input value={siteAddress} onChange={(event) => setSiteAddress(event.target.value)} placeholder="100 King St W" /><p>Leave blank to start from the city centre.</p></div>
              <div className="form-field"><label><Store /> Business idea</label><SearchableSelect value={businessInputMode === "custom" ? customBusinessQuery : businessSubcategory} onValueChange={handleBusinessChange} options={businessOptions.map((business) => ({ value: business.business_subcategory, label: business.label }))} placeholder="Choose or type an idea" searchPlaceholder="Try bakery, gym, dental clinic…" allowCustomValue />{businessInputMode === "custom" && businessResolution?.score_basis_note ? <p className="text-primary">{businessResolution.score_basis_note}</p> : null}</div>
              <div className="form-field"><div className="flex items-center justify-between"><label><Target /> Customer reach</label><strong className="radius-value">{radius[0]} km</strong></div><Slider value={radius} onValueChange={setRadius} min={1} max={25} step={1} className="py-2" /><div className="range-labels"><span>Neighbourhood</span><span>Regional</span></div></div>
              <Button className="scenario-submit" onClick={handleStartAnalysis} disabled={isUpdating}>Show me this spot<ChevronRight /></Button>
              <p className="form-assurance"><ShieldCheck /> Your searches stay inside your account.</p>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  const feasibilityScore = ml?.predicted_feasibility_score ?? 0;
  const recommendationLabel = recommendationDecision?.recommendation_label || readableRecommendation(ml?.recommendation);
  const competitorCount = competitionEvidence?.observed_competitor_count ?? geoContext?.real_competitor_count ?? 0;
  const demandScore = demandEvidence?.demand_pressure_index ?? breakdown?.demand_analysis?.score ?? 0;
  const competitionScore = competitionEvidence?.competition_pressure_index ?? breakdown?.competition_analysis?.score ?? 0;
  const costScore = leaseCostEvidence?.rent_pressure_index ?? breakdown?.lease_cost_analysis?.score ?? 0;

  const tabs = [
    { id: "map", label: "Map & competition", icon: MapPin },
    { id: "overview", label: "Verdict", icon: Gauge },
    { id: "benchmarks", label: "Costs & market", icon: DollarSign },
    { id: "history", label: "Compare spots", icon: GitCompare },
    { id: "evidence", label: "Data & setup", icon: ShieldCheck },
  ] as const;

  return (
    <div className="workspace-page">
      {isUpdating && <div className="workspace-sync-bar" />}
      <header className="workspace-header">
        <div className="app-brand"><span className="brand-pin text-3xl" aria-hidden /><div><h1>BestSpot<span>.biz</span></h1><p>Find the strongest place for your next move</p></div></div>
        <div className="workspace-actions">
          <span className="sync-status"><Signal className={isUpdating ? "animate-pulse" : ""} />{isUpdating ? "Updating your result" : `Updated ${lastUpdate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`}</span>
          <Button variant="outline" className="rounded-full" onClick={handleExport} disabled={isExporting}><Download />{isExporting ? "Preparing…" : "Export"}</Button>
          <AccountButton />
        </div>
      </header>

      <main className="workspace-shell">
        <section className="scenario-ribbon">
          <div className="scenario-ribbon-main"><span className="scenario-ribbon-pin"><MapPin /></span><div><p>Active location</p><h2>{businessInputMode === "custom" && customBusinessQuery ? customBusinessQuery : businessSubcategory} in {municipalityName}</h2><span>{siteAddress.trim() || "City-centre search"} · {radius[0]} km customer reach</span></div></div>
          <div className="scenario-ribbon-controls"><div className="mini-radius"><span>Reach</span><Slider value={radius} onValueChange={setRadius} min={1} max={25} step={1} /><strong>{radius[0]} km</strong></div><Button variant="ghost" className="rounded-full" onClick={() => setIsScenarioSelected(false)}>Change search</Button></div>
        </section>

        <nav className="workspace-tabs" aria-label="Analysis sections">
          {tabs.map(({ id, label, icon: Icon }) => <button key={id} type="button" className={activeTab === id ? "active" : ""} onClick={() => setActiveTab(id)}><Icon />{label}{id === "history" && scenarioHistory.length > 0 ? <span>{scenarioHistory.length}</span> : null}</button>)}
        </nav>

        <AnimatePresence mode="wait">
          <motion.section key={activeTab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.18 }} className="workspace-content">
            {activeTab === "map" && (
              <div className="space-y-5">
                <section className="decision-strip">
                  <div className="decision-score"><strong>{feasibilityScore.toFixed(0)}</strong><span>/100</span></div>
                  <div className="decision-copy"><p className="eyebrow">Your first read</p><h2>{recommendationLabel}</h2><p>{recommendationDecision?.decision_summary || explanation?.feasibility_explanation || "Your feasibility result is ready. Explore the map and evidence below."}</p></div>
                  <div className="decision-actions"><Button variant="outline" className="rounded-full" onClick={handleSaveScenario} disabled={isSavingScenario}><Save />{isSavingScenario ? "Saving…" : "Save spot"}</Button><Button className="rounded-full" onClick={() => setActiveTab("history")}><GitCompare />Compare</Button></div>
                </section>

                <div className="map-workspace-grid">
                  <div className="map-primary-column">
                    <div className="map-section-heading"><div><p className="eyebrow">See what surrounds the spot</p><h2>Competition on the map</h2></div><span className="map-source-badge"><span />{competitionIsLiveOsm ? "Live market evidence" : "Market evidence"}</span></div>
                    {geoContext ? <div className={`anchor-note ${geoContext.anchor_type === "address" ? "address" : "city"}`}><MapPin />{geoContext.anchor_note || (geoContext.anchor_type === "address" ? `Centred on ${geoContext.resolved_address}` : `Centred on ${geoContext.municipality_name} city centre.`)}</div> : null}
                    <div className="map-frame"><MarketMapPanel geoContext={geoContext} isLoading={isGeoLoading} error={geoError} onRetry={() => loadGeoContext(activeGeoPayload as GeospatialMarketMapRequest)} /></div>
                  </div>

                  <aside className="map-insight-rail">
                    <div className="insight-card insight-card-primary"><div className="insight-card-icon"><Store /></div><p>Nearby competition</p><strong>{formatNumber(competitorCount)}</strong><span>{competitionEvidence?.nearest_competitor_distance_km != null ? `Nearest is ${competitionEvidence.nearest_competitor_distance_km.toFixed(1)} km away` : "Inside your selected reach"}</span><div className="meter"><i style={{ width: `${Math.min(100, competitionScore)}%` }} /></div><small>{indicatorLabelForCompetition(dashboardData.competition_monitor.indicator)} pressure</small></div>
                    <div className="insight-card"><div className="insight-card-icon green"><Users /></div><p>Reachable people</p><strong>{formatNumber(populationValue)}</strong><span>{demandEvidence?.target_customer_pool_estimate ? `${formatNumber(demandEvidence.target_customer_pool_estimate)} likely target customers` : "Local population in the data view"}</span><div className="meter green"><i style={{ width: `${Math.min(100, demandScore)}%` }} /></div><small>Demand score {demandScore.toFixed(0)}/100</small></div>
                    <div className="insight-card"><div className="insight-card-icon ink"><DollarSign /></div><p>Monthly lease range</p><strong className="text-2xl">{leaseCostEvidence ? formatCurrency(leaseCostEvidence.median_monthly_lease_cost) : "N/A"}</strong><span>{leaseCostEvidence ? `${formatCurrency(leaseCostEvidence.low_monthly_lease_cost)} – ${formatCurrency(leaseCostEvidence.high_monthly_lease_cost)}` : "Open Costs & market for estimates"}</span><button type="button" onClick={() => setActiveTab("benchmarks")}>See cost picture <ChevronRight /></button></div>
                  </aside>
                </div>
              </div>
            )}

            {activeTab === "overview" && (
              <div className="verdict-layout">
                <section className="verdict-hero-card">
                  <div className="verdict-ring"><strong>{feasibilityScore.toFixed(0)}</strong><span>out of 100</span></div>
                  <div className="verdict-main"><p className="eyebrow">BestSpot verdict</p><h2>{recommendationLabel}</h2><p>{recommendationDecision?.decision_rationale || explanation?.feasibility_explanation}</p><div className="verdict-guidance"><Navigation /><span>{recommendationDecision?.action_guidance || "Use the evidence below to confirm the location before making a lease commitment."}</span></div></div>
                </section>
                <section className="metric-row">
                  <article><DollarSign /><p>Predicted monthly net</p><strong>{formatCurrency(ml?.predicted_monthly_net_revenue)}</strong><span className={indicatorTextClass(dashboardData.revenue_monitor.indicator)}>{indicatorLabelForRevenue(dashboardData.revenue_monitor.indicator)} outlook</span></article>
                  <article><AlertTriangle /><p>Business risk</p><strong>{ml?.predicted_risk_class?.replaceAll("_", " ") || "N/A"}</strong><span className={indicatorTextClass(dashboardData.risk_monitor.indicator)}>{indicatorLabelForRisk(dashboardData.risk_monitor.indicator)} risk</span></article>
                  <article><ShieldCheck /><p>Decision confidence</p><strong>{recommendationDecision?.decision_confidence_score?.toFixed(0) ?? credibility?.overall_confidence_score?.toFixed(0) ?? "N/A"}<small>/100</small></strong><span>{credibility?.confidence_level || "Evidence based"} confidence</span></article>
                </section>
                <div className="verdict-detail-grid">
                  <Card className="plain-card"><CardHeader><CardTitle>What helps this spot</CardTitle></CardHeader><CardContent className="factor-list positive">{(recommendationDecision?.major_strengths || explanation?.top_positive_factors || []).slice(0, 5).map((factor) => <p key={factor}><span><TrendingUp /></span>{factor}</p>)}</CardContent></Card>
                  <Card className="plain-card"><CardHeader><CardTitle>What needs a closer look</CardTitle></CardHeader><CardContent className="factor-list caution">{(recommendationDecision?.major_concerns || explanation?.top_negative_factors || []).slice(0, 5).map((factor) => <p key={factor}><span><AlertTriangle /></span>{factor}</p>)}</CardContent></Card>
                </div>
                <Card className="plain-card market-profile"><CardHeader><div><p className="eyebrow">People around the spot</p><CardTitle>Local market profile</CardTitle></div></CardHeader><CardContent className="profile-grid"><div><span>Population</span><strong>{formatNumber(populationValue)}</strong></div><div><span>Median household income</span><strong>{formatCurrency(medianIncome)}</strong></div><div><span>Population density</span><strong>{formatNumber(density)}<small>/km²</small></strong></div><div><span>Students</span><strong>{studentPct.toFixed(1)}%</strong></div><div><span>Families</span><strong>{familiesPct.toFixed(1)}%</strong></div><div><span>Retirees</span><strong>{retireesPct.toFixed(1)}%</strong></div></CardContent></Card>
              </div>
            )}

            {activeTab === "benchmarks" && (
              <div className="space-y-5">
                <div className="content-heading"><div><p className="eyebrow">Money and market pressure</p><h2>Know the operating picture before the lease.</h2><p>These ranges turn local evidence into planning numbers. They are estimates, clearly separated from observed data.</p></div></div>
                <section className="evidence-summary-grid">
                  <article><div className="summary-icon"><TrendingUp /></div><p>Demand</p><strong>{demandScore.toFixed(0)}<small>/100</small></strong><span>{demandEvidence?.demand_level || breakdown?.demand_analysis?.level || "Market signal"}</span></article>
                  <article><div className="summary-icon red"><Store /></div><p>Competition</p><strong>{competitionScore.toFixed(0)}<small>/100</small></strong><span>{competitorCount} observed nearby</span></article>
                  <article><div className="summary-icon ink"><DollarSign /></div><p>Rent pressure</p><strong>{costScore.toFixed(0)}<small>/100</small></strong><span>{leaseCostEvidence?.commercial_cost_pressure_level || breakdown?.lease_cost_analysis?.level || "Estimated"}</span></article>
                  <article><div className="summary-icon amber"><Activity /></div><p>Foot traffic</p><strong>{demandEvidence?.foot_traffic_proxy_index?.toFixed(0) ?? "N/A"}</strong><span>Public activity signal</span></article>
                </section>
                <OperatingProfilePanel municipalityName={municipalityName} radiusKm={radius[0]} businessSubcategory={businessSubcategory} businessQuery={customBusinessQuery} businessResolution={businessResolution as unknown as Record<string, unknown> | null} customBusinessMapActive={businessInputMode === "custom" && useCustomBusinessForMap} initialProfile={operatingProfile} />
              </div>
            )}

            {activeTab === "history" && (
              <div className="space-y-5">
                <div className="content-heading compare-heading"><div><p className="eyebrow">Your strongest decision tool</p><h2>Compare every spot on equal terms.</h2><p>Save this result, explore another city or radius, then rank the options together.</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" className="rounded-full" onClick={handleSaveScenario} disabled={isSavingScenario}><Save />{isSavingScenario ? "Saving…" : "Save current spot"}</Button><Button className="rounded-full" onClick={handleCompareScenarios} disabled={isComparingScenarios || scenarioHistory.length < 1}><GitCompare />{isComparingScenarios ? "Comparing…" : "Rank saved spots"}</Button></div></div>
                <LocationComparisonPanel municipalityName={municipalityName} businessSubcategory={businessSubcategory} radiusKm={radius[0]} onApplyScenario={({ municipality_name, business_subcategory, radius_km }) => { setMunicipalityName(municipality_name); setBusinessSubcategory(business_subcategory); setRadius([radius_km]); setActiveTab("map"); }} />
                <div className="saved-spots-layout">
                  <Card className="plain-card"><CardHeader className="flex-row items-center justify-between"><div><p className="eyebrow">Saved searches</p><CardTitle>{scenarioHistory.length} spot{scenarioHistory.length === 1 ? "" : "s"}</CardTitle></div>{scenarioHistory.length > 0 && <Button variant="ghost" size="sm" onClick={handleClearHistory}>Clear</Button>}</CardHeader><CardContent className="saved-list">{scenarioHistory.length === 0 ? <div className="empty-saved"><History /><strong>No saved spots yet</strong><p>Save this result, change the location, and you will have a comparison.</p></div> : scenarioHistory.map((item, index) => <article key={item.scenario_id}><span>{index + 1}</span><div><strong>{item.municipality_name}</strong><p>{item.business_subcategory} · {item.radius_km} km</p></div><div><strong>{item.predicted_feasibility_score?.toFixed(0) ?? "—"}</strong><small>/100</small></div></article>)}</CardContent></Card>
                  {scenarioComparison ? <Card className="plain-card comparison-result"><CardHeader><p className="eyebrow">BestSpot ranking</p><CardTitle>{scenarioComparison.comparison_summary}</CardTitle></CardHeader><CardContent>{scenarioComparison.rankings.map((item, index) => <article key={item.scenario_id} className={index === 0 ? "winner" : ""}><span>#{index + 1}</span><div><strong>{item.label}</strong><p>{item.key_tradeoff}</p></div><strong>{item.overall_score.toFixed(0)}</strong></article>)}</CardContent></Card> : <Card className="plain-card comparison-placeholder"><GitCompare /><h3>Your ranking will appear here.</h3><p>Save at least one spot and choose “Rank saved spots.”</p></Card>}
                </div>
              </div>
            )}

            {activeTab === "evidence" && (
              <div className="space-y-5">
                <div className="content-heading"><div><p className="eyebrow">Transparency behind the answer</p><h2>Understand the data and tune the setup.</h2><p>Advanced controls live here, away from the main decision flow but available whenever you need them.</p></div></div>
                <div className="data-setup-grid">
                  <BusinessResolverPanel municipalityName={municipalityName} radiusKm={radius[0]} currentCatalogBusinessSubcategory={businessSubcategory} businessInputMode={businessInputMode} onBusinessInputModeChange={setBusinessInputMode} customBusinessQuery={customBusinessQuery} onCustomBusinessQueryChange={setCustomBusinessQuery} useCustomBusinessForMap={useCustomBusinessForMap} onUseCustomBusinessForMapChange={setUseCustomBusinessForMap} onBusinessResolutionChange={setBusinessResolution} className="plain-card" />
                  <ScenarioSupportPanel municipalityName={municipalityName} businessSubcategory={businessSubcategory} radiusKm={radius[0]} businessInputMode={businessInputMode} customBusinessQuery={customBusinessQuery} useCustomBusinessForMap={useCustomBusinessForMap} businessResolution={businessResolution} />
                </div>
                <Card className="plain-card trust-card"><CardHeader><div><p className="eyebrow">Evidence confidence</p><CardTitle>What is observed and what is estimated</CardTitle></div><Badge variant="outline" className={credibilityClass(credibility?.confidence_level)}>{credibility?.overall_confidence_score?.toFixed(0) ?? "—"}/100 · {credibility?.confidence_level || "Unknown"}</Badge></CardHeader><CardContent className="trust-columns"><div><h3><Database />Observed inputs</h3>{(credibility?.observed_inputs ?? []).slice(0, 5).map((item) => <article key={item.field_name}><strong>{item.label}</strong><p>{item.user_note}</p></article>)}</div><div><h3><BrainCircuit />Estimated or modelled</h3>{(credibility?.proxy_estimated_inputs ?? []).slice(0, 5).map((item) => <article key={item.field_name}><strong>{item.label}</strong><p>{item.user_note}</p></article>)}</div></CardContent></Card>
                <div className="system-grid"><Card className="plain-card"><CardHeader><CardTitle>System check</CardTitle><p>Verify the services behind this workspace.</p></CardHeader><CardContent><Button variant="outline" className="rounded-full" onClick={handleRunValidation} disabled={isValidating}>{isValidating ? "Checking…" : "Run system check"}</Button>{systemValidation && <div className="validation-list">{systemValidation.checks.map((check) => <p key={check.name} className={check.status === "passed" ? "pass" : "fail"}>{check.status === "passed" ? "PASS" : "CHECK"}<span>{check.name}</span></p>)}</div>}</CardContent></Card><Card className="plain-card"><CardHeader><CardTitle>Prediction model</CardTitle><p>Health and freshness of the feasibility engine.</p></CardHeader><CardContent className="model-status"><span className={modelStatus?.status === "ready" ? "ready" : ""}>{modelStatus?.status || "Unavailable"}</span><p>{modelStatus?.important_note || "Model status details are not available."}</p></CardContent></Card></div>
              </div>
            )}
          </motion.section>
        </AnimatePresence>
      </main>

      <div className="assistant-dock">
        <AnimatePresence>{isChatOpen && <motion.div initial={{ opacity: 0, y: 18, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: 0.98 }} className="assistant-panel"><div className="assistant-panel-header"><div><span className="assistant-avatar"><BrainCircuit /></span><div><strong>BestSpot assistant</strong><p>Answers from this location</p></div></div><button type="button" onClick={() => setIsChatOpen(false)} aria-label="Close assistant"><X /></button></div><div className="assistant-panel-body"><ScenarioAIChat municipalityName={municipalityName} businessSubcategory={businessSubcategory} radiusKm={radius[0]} /></div></motion.div>}</AnimatePresence>
        <button type="button" className={`assistant-toggle ${isChatOpen ? "open" : ""}`} onClick={() => setIsChatOpen(!isChatOpen)} aria-label={isChatOpen ? "Close BestSpot assistant" : "Ask BestSpot assistant"}>{isChatOpen ? <X /> : <><MessageSquare /><span>Ask BestSpot</span></>}</button>
      </div>
    </div>
  );
}
