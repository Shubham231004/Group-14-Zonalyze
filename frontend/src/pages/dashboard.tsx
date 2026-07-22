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
import BusinessResolverPanel, {
  type BusinessInputMode,
  type BusinessResolutionResponse,
} from "@/components/BusinessResolverPanel";

import OperatingProfilePanel from "@/components/OperatingProfilePanel";
import LocationComparisonPanel from "@/components/LocationComparisonPanel";
import SiteAddressAnalysisPanel from "@/components/SiteAddressAnalysisPanel";

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
  runSystemValidation,
  saveScenarioToHistory,
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
  if (indicator === "green") return "text-emerald-400";
  if (indicator === "yellow") return "text-accent";
  if (indicator === "red") return "text-destructive";
  return "text-white";
}

function indicatorBadgeClass(indicator: string) {
  if (indicator === "green") return "text-emerald-400 border-emerald-400/30 bg-emerald-500/5";
  if (indicator === "yellow") return "text-accent border-accent/30 bg-accent/5";
  if (indicator === "red") return "text-destructive border-destructive/30 bg-destructive/5";
  return "text-white border-white/20";
}

function recommendationBadgeClass(recommendation?: string) {
  if (recommendation === "recommended")
    return "text-emerald-400 border-emerald-400/30 bg-emerald-500/5";
  if (recommendation === "borderline") return "text-accent border-accent/30 bg-accent/5";
  if (recommendation === "not_recommended")
    return "text-destructive border-destructive/30 bg-destructive/5";
  return "text-white border-white/20";
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
  if (level === "strong") return "text-emerald-400 border-emerald-400/30 bg-emerald-500/5";
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
      <Card className="scada-panel border-white/5">
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
      className="scada-panel border-white/5 shadow-2xl rounded-2xl overflow-hidden min-h-[500px]"
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
  const [activeTab, setActiveTab] = useState<"overview" | "map" | "evidence" | "benchmarks" | "history">("overview");
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
      link.download = report.filename || "zonalyze-feasibility-report.txt";
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

  if (isInitialLoading || !dashboardData) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center relative overflow-hidden">
        <div className="scanline" />
        <div className="scada-panel px-8 py-6 rounded-2xl flex flex-col items-center gap-4 max-w-sm text-center">
          <BrainCircuit className="w-12 h-12 text-primary animate-pulse" />
          <div>
            <h3 className="font-display font-bold text-white text-lg tracking-wider">ZONALYZE CORE</h3>
            <p className="lcd-text text-[11px] text-primary mt-1">Initializing ML Prediction Models...</p>
          </div>
        </div>
      </div>
    );
  }

  // --- RENDERING PROGRESS LOADER SCREEN ---
  if (isAnalyzing) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center font-sans p-6 relative overflow-hidden">
        <div className="scanline" />
        <div className="absolute top-10 left-10 w-72 h-72 bg-primary/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-accent/5 rounded-full blur-[120px] pointer-events-none" />

        <Card className="scada-panel border-white/10 rounded-2xl shadow-2xl p-8 max-w-md w-full text-center space-y-6">
          <img src="/logo.jpg" className="w-48 mx-auto rounded-2xl border border-white/15 shadow-xl shadow-primary/5" alt="Logo" />
          
          <div className="space-y-2">
            <h3 className="text-lg font-display text-white tracking-wider uppercase">Analyzing Feasibility</h3>
            <p className="text-xs text-slate-400">Running advanced geospatial and ML algorithms</p>
          </div>

          <div className="space-y-3 pt-2">
            <div className="w-full h-3 rounded-full bg-white/10 overflow-hidden border border-white/5 p-0.5">
              <div
                className="h-full bg-gradient-to-r from-primary to-cyan-400 rounded-full transition-all duration-100 ease-out"
                style={{ width: `${loadingProgress}%` }}
              />
            </div>
            <div className="flex justify-between text-xs font-mono text-slate-400">
              <span className="lcd-text text-primary">Progress</span>
              <span>{loadingProgress}%</span>
            </div>
          </div>

          <div className="bg-slate-950/70 rounded-xl border border-white/5 p-4 min-h-[72px] flex items-center justify-center">
            <p className="text-[11px] font-mono text-slate-300 leading-relaxed text-center">
              {loadingStep}
            </p>
          </div>

          <div className="flex items-center justify-center gap-2 pt-2">
            <Cpu className="w-4 h-4 text-cyan-400 animate-spin" />
            <span className="text-[9px] font-mono lcd-text text-slate-500 uppercase tracking-widest">
              Zonalyze Engine Processing
            </span>
          </div>
        </Card>
      </div>
    );
  }

  // --- RENDERING LANDING SCREEN (Scenario Selection) ---
  if (!isScenarioSelected) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col font-sans p-4 md:p-8 relative overflow-hidden">
        <div className="scanline" />
        
        {/* Floating background blobs */}
        <div className="absolute top-10 left-10 w-72 h-72 bg-primary/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-accent/5 rounded-full blur-[120px] pointer-events-none" />

        <header className="flex items-center justify-between pb-6 mb-8 border-b border-white/10">
          <div className="flex items-center gap-3">
            <img src="/logo.jpg" className="w-10 h-10 object-contain rounded-md border border-white/10" alt="Logo" />
            <div>
              <h1 className="text-xl font-display font-bold tracking-wider text-white">ZONALYZE</h1>
              <p className="text-[10px] lcd-text text-muted-foreground">Feasibility intelligence Engine</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="border-white/10 text-white/50 text-[10px] font-mono">
              v{dashboardData.project_phase ? "1.0.0" : "0.1.0"}
            </Badge>
          </div>
        </header>

        <main className="flex-1 flex flex-col lg:flex-row items-center justify-center gap-12 max-w-6xl mx-auto w-full z-10 py-6">
          <div className="flex-1 max-w-lg space-y-6 text-center lg:text-left">
            <Badge className="bg-primary/20 text-primary hover:bg-primary/30 border border-primary/40 uppercase tracking-widest text-[10px] font-mono py-1 px-3">
              Decision Support System
            </Badge>
            <h2 className="text-4xl md:text-5xl font-display font-black text-white leading-tight tracking-tight">
              Evaluate Location <br />
              <span className="bg-gradient-to-r from-primary to-cyan-400 bg-clip-text text-transparent">
                Feasibility Instantly
              </span>
            </h2>
            <p className="text-slate-400 text-sm md:text-base leading-relaxed">
              Analyze commercial spaces, competitor densities, daytime activities, and localized demographic mixes. Make data-driven decisions powered by machine learning algorithms.
            </p>
            
            <div className="grid grid-cols-2 gap-4 text-left pt-2">
              <div className="border border-white/5 bg-white/[0.02] p-4 rounded-xl">
                <Users className="w-5 h-5 text-primary mb-2" />
                <h4 className="text-xs font-display text-white tracking-wide uppercase">Demographics</h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-snug">Statistics Canada 2021 census mapping subdivisions.</p>
              </div>
              <div className="border border-white/5 bg-white/[0.02] p-4 rounded-xl">
                <MapPin className="w-5 h-5 text-accent mb-2" />
                <h4 className="text-xs font-display text-white tracking-wide uppercase">Competitors</h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-snug">Live geographic mapping via OpenStreetMap Overpass.</p>
              </div>
            </div>
          </div>

          <div className="w-full max-w-md">
            <Card className="scada-panel border-white/10 rounded-2xl shadow-2xl p-6 space-y-6">
              <div className="border-b border-white/5 pb-4">
                <img src="/logo.jpg" className="w-32 mx-auto rounded-xl border border-white/10 shadow-md mb-4" alt="Logo" />
                <h3 className="text-base font-display text-white text-center tracking-wider uppercase">
                  Setup Scenario
                </h3>
              </div>

              <div className="space-y-5">
                <div className="space-y-2">
                  <label className="text-xs lcd-text text-muted-foreground flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5" /> Target Municipality
                  </label>
                  <SearchableSelect
                    value={municipalityName}
                    onValueChange={setMunicipalityName}
                    options={municipalityOptions.map((city) => ({
                      value: city.municipality_name,
                      label: city.label,
                    }))}
                    placeholder="Select municipality"
                    searchPlaceholder="Search or type any Ontario city..."
                    allowCustomValue
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs lcd-text text-muted-foreground flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5" /> Specific Address <span className="opacity-60">(optional)</span>
                  </label>
                  <Input
                    value={siteAddress}
                    onChange={(event) => setSiteAddress(event.target.value)}
                    placeholder="e.g. 100 King St W — anchors the radius here"
                    className="bg-background/50 border-white/10 font-mono text-sm h-11 rounded-xl focus-visible:ring-primary"
                  />
                  <p className="text-[10px] text-muted-foreground/70">
                    Leave blank to analyse from the city centre. Add an address to centre the radius on a specific storefront.
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-xs lcd-text text-muted-foreground flex items-center gap-1.5">
                    <Store className="w-3.5 h-3.5" /> Business Subcategory
                  </label>
                  <SearchableSelect
                    value={businessSubcategory}
                    onValueChange={setBusinessSubcategory}
                    options={businessOptions.map((business) => ({
                      value: business.business_subcategory,
                      label: business.label,
                    }))}
                    placeholder="Select business"
                    searchPlaceholder="Search business types..."
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs lcd-text text-muted-foreground flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5" /> Catchment Radius
                    </label>
                    <span className="text-primary font-mono text-sm font-bold">
                      {radius[0]} km
                    </span>
                  </div>
                  <Slider
                    value={radius}
                    onValueChange={setRadius}
                    max={25}
                    min={1}
                    step={1}
                    className="py-2 [&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                  />
                </div>

                <Button
                  className="w-full bg-gradient-to-r from-primary to-cyan-500 hover:from-primary/95 hover:to-cyan-500/95 text-white font-mono uppercase tracking-widest text-sm py-6 rounded-xl shadow-lg shadow-primary/20 transition-all duration-300 font-bold mt-4"
                  onClick={handleStartAnalysis}
                  disabled={isUpdating}
                >
                  <ChevronRight className="w-5 h-5 mr-2" />
                  Analyze Location Feasibility
                </Button>
              </div>
            </Card>
          </div>
        </main>

        <footer className="py-6 border-t border-white/5 text-center text-[10px] lcd-text text-slate-600">
          ZONALYZE FEASIBILITY PLATFORM • CAPSTONE PROTOTYPE
        </footer>
      </div>
    );
  }

  // --- RENDERING WORKSPACE SCREEN (Redesigned Tabbed Layout) ---
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans p-4 lg:p-6 overflow-x-hidden relative">
      <div className="scanline" />

      {/* Styled Top Syncing Progress Bar */}
      <style>{`
        @keyframes gradientSlide {
          0% { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
      `}</style>
      <AnimatePresence>
        {isUpdating && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-primary via-cyan-400 to-primary z-50 shadow-md shadow-primary/30"
            style={{
              backgroundSize: "200% 100%",
              animation: "gradientSlide 1.5s linear infinite"
            }}
          />
        )}
      </AnimatePresence>

      {/* Header Panel */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between mb-6 pb-4 border-b border-white/10 gap-4">
        <div className="flex items-center gap-3">
          <img src="/logo.jpg" className="w-12 h-12 rounded-md object-contain border border-white/10" alt="Logo" />
          <div>
            <h1 className="text-2xl font-display font-bold tracking-wider text-white">
              ZONALYZE{" "}
              <span className="text-primary text-xs tracking-widest uppercase">
                ML.Core
              </span>
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="border-primary/20 text-primary-foreground text-[9px] uppercase font-mono py-0.5 px-2 bg-primary/5">
                {municipalityName} • {businessSubcategory} • {radius[0]} km
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 text-[9px] font-mono text-muted-foreground hover:text-white uppercase px-1 underline"
                onClick={() => setIsScenarioSelected(false)}
              >
                Change Scenario
              </Button>
            </div>
          </div>
        </div>

        {/* Sync/Status Indicators */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 bg-card/40 px-3 py-1.5 rounded-md border border-white/5 backdrop-blur-md">
            <Signal
              className={`w-3.5 h-3.5 ${isUpdating ? "text-accent animate-pulse" : "text-emerald-400"}`}
            />
            <span className="text-[10px] lcd-text text-white/80">
              {isUpdating ? "ENGINE SYNCING..." : `SYNCED: ${lastUpdate.toLocaleTimeString()}`}
            </span>
          </div>
          <Button
            variant="outline"
            className="bg-primary/10 hover:bg-primary/20 border-primary/30 text-primary-foreground font-mono text-xs uppercase tracking-wider"
            onClick={handleExport}
            disabled={isExporting}
          >
            <Download
              className={`w-3.5 h-3.5 mr-2 ${isExporting ? "animate-pulse" : ""}`}
            />
            {isExporting ? "Exporting..." : "Export Report"}
          </Button>
        </div>
      </header>

      {/* Main Workspace Area */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Sidebar (Control Center) */}
        <div className="lg:col-span-3 flex flex-col gap-4">
          
          {/* Quick Dials */}
          <Card className="scada-panel border-white/5">
            <CardHeader className="pb-3 border-b border-white/5">
              <CardTitle className="text-xs font-display tracking-wider uppercase text-white/90 flex justify-between items-center">
                <span>Active Target</span>
                <Badge variant="outline" className="border-white/10 text-[9px] font-mono">{radius[0]} km</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div>
                <p className="text-[10px] lcd-text text-muted-foreground">Location</p>
                <p className="font-mono text-sm text-white mt-0.5">{municipalityName}</p>
              </div>
              <div>
                <p className="text-[10px] lcd-text text-muted-foreground">Business Subcategory</p>
                <p className="font-mono text-sm text-white mt-0.5">{businessSubcategory}</p>
              </div>
              <div className="pt-2">
                <div className="flex justify-between items-center mb-1">
                  <label className="text-[10px] lcd-text text-muted-foreground">Adjust Radius</label>
                  <span className="text-primary font-mono text-xs font-bold">{radius[0]} km</span>
                </div>
                <Slider
                  value={radius}
                  onValueChange={setRadius}
                  max={25}
                  min={1}
                  step={1}
                  className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                />
              </div>
            </CardContent>
          </Card>

          {/* Dynamic Business Resolver Panel */}
          <BusinessResolverPanel
            municipalityName={municipalityName}
            radiusKm={radius[0]}
            currentCatalogBusinessSubcategory={businessSubcategory}
            businessInputMode={businessInputMode}
            onBusinessInputModeChange={setBusinessInputMode}
            customBusinessQuery={customBusinessQuery}
            onCustomBusinessQueryChange={setCustomBusinessQuery}
            useCustomBusinessForMap={useCustomBusinessForMap}
            onUseCustomBusinessForMapChange={setUseCustomBusinessForMap}
            onBusinessResolutionChange={setBusinessResolution}
            className="scada-panel border-white/5 shadow-md"
          />

          {/* Validation Panel */}
          <Card className="scada-panel border-white/5">
            <CardHeader className="pb-3 border-b border-white/5">
              <CardTitle className="text-xs font-display tracking-wider uppercase text-white/95 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  System Diagnostics
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-3">
              <Button
                variant="outline"
                size="sm"
                className="w-full bg-emerald-400/10 hover:bg-emerald-400/20 border-emerald-400/30 text-emerald-100 font-mono text-xs uppercase"
                onClick={handleRunValidation}
                disabled={isValidating}
              >
                {isValidating ? "Validating..." : "Run System Validation"}
              </Button>
              {systemValidation && (
                <div className="space-y-1 max-h-24 overflow-y-auto pr-1">
                  {systemValidation.checks.map((check) => (
                    <p
                      key={check.name}
                      className={`text-[10px] font-mono ${check.status === "passed" ? "text-emerald-300" : "text-destructive"}`}
                    >
                      {check.status === "passed" ? "PASS" : "FAIL"}: {check.name}
                    </p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* ML Model Status */}
          <Card className="scada-panel border-white/5">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <BrainCircuit
                  className={`w-4 h-4 ${modelStatus?.status === "ready" ? "text-primary" : "text-accent"}`}
                />
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    Model Status
                  </p>
                  <p className="text-xs font-mono text-white/80 uppercase">
                    {modelStatus?.status ?? "unknown"}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="rounded border border-white/10 bg-white/[0.03] p-1.5 text-center">
                  <p className="text-muted-foreground">Rows</p>
                  <p className="font-mono text-white mt-0.5">{modelStatus ? formatNumber(modelStatus.row_count) : "N/A"}</p>
                </div>
                <div className="rounded border border-white/10 bg-white/[0.03] p-1.5 text-center">
                  <p className="text-muted-foreground">Accuracy</p>
                  <p className="font-mono text-primary mt-0.5">{formatPercent(modelStatus?.risk_accuracy)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Workspace (Tabbed Content View) */}
        <div className="lg:col-span-9 flex flex-col gap-6">
          
          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 bg-slate-950/80 p-1.5 rounded-xl border border-white/10 overflow-x-auto scrollbar-hide">
            {[
              { id: "overview", label: "Overview", icon: BarChart4 },
              { id: "map", label: "Geospatial Map", icon: MapPin },
              { id: "evidence", label: "Evidence Indicators", icon: Database },
              { id: "benchmarks", label: "Benchmarks Profile", icon: DollarSign },
              { id: "history", label: "Compare Locations", icon: GitCompare },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-mono text-xs uppercase tracking-wider transition-all duration-200 shrink-0 ${
                    isActive
                      ? "bg-primary text-white shadow-lg shadow-primary/20 font-bold"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Active Tab Panel Render */}
          <div className="min-h-[500px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
              >
                
                {/* 1. OVERVIEW TAB */}
                {activeTab === "overview" && (
                  <>
                    {/* Recommendation Decision Card */}
                    {recommendationDecision && (
                      <Card className="scada-panel border-white/10 bg-primary/[0.02]">
                        <CardContent className="p-6 space-y-4">
                          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/5 pb-3">
                            <div>
                              <p className="text-[10px] text-primary uppercase tracking-widest font-mono">
                                Unified Feasibility Recommendation
                              </p>
                              <h3 className="text-xl font-bold text-white mt-1">
                                {recommendationDecision.decision_summary}
                              </h3>
                            </div>
                            <Badge
                              variant="outline"
                              className={`text-sm py-1 px-3 rounded-full font-mono uppercase ${recommendationBadgeClass(recommendationDecision.final_recommendation)}`}
                            >
                              {recommendationDecision.recommendation_label}
                            </Badge>
                          </div>
                          
                          <p className="text-sm text-slate-300 leading-relaxed">
                            {recommendationDecision.action_guidance}
                          </p>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                            <div className="space-y-2">
                              <p className="text-xs font-mono text-emerald-400 uppercase tracking-wider">
                                Primary Strengths
                              </p>
                              <ul className="space-y-1.5">
                                {recommendationDecision.major_strengths.map((item) => (
                                  <li key={item} className="text-xs text-slate-300 flex items-start gap-2">
                                    <span className="text-emerald-400 font-bold">•</span>
                                    <span>{item}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div className="space-y-2">
                              <p className="text-xs font-mono text-destructive uppercase tracking-wider">
                                Risk Factors / Concerns
                              </p>
                              <ul className="space-y-1.5">
                                {recommendationDecision.major_concerns.map((item) => (
                                  <li key={item} className="text-xs text-slate-300 flex items-start gap-2">
                                    <span className="text-destructive font-bold">•</span>
                                    <span>{item}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {/* KPI Cards Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="scada-panel">
                        <CardContent className="p-5">
                          <p className="text-[10px] lcd-text text-muted-foreground">Total Population</p>
                          <p className="text-3xl data-value mt-1">{formatNumber(populationValue)}</p>
                          <p className="text-[10px] text-slate-500 mt-2 font-mono">{municipalityName}</p>
                        </CardContent>
                      </Card>
                      <Card className="scada-panel">
                        <CardContent className="p-5">
                          <p className="text-[10px] lcd-text text-muted-foreground">Feasibility Score</p>
                          <p className="text-3xl data-value-accent mt-1">
                            {ml?.predicted_feasibility_score?.toFixed(1) ?? "N/A"}/100
                          </p>
                          <p className="text-[10px] text-slate-500 mt-2 font-mono">Simulated Score</p>
                        </CardContent>
                      </Card>
                      <Card className="scada-panel">
                        <CardContent className="p-5">
                          <p className="text-[10px] lcd-text text-muted-foreground">Revenue Estimate</p>
                          <p className={`text-2xl font-mono mt-1.5 font-bold ${indicatorTextClass(dashboardData.revenue_monitor.indicator)}`}>
                            {formatCurrency(ml?.predicted_monthly_net_revenue)}
                          </p>
                          <p className="text-[10px] text-slate-500 mt-2 font-mono">Net Profit/Month</p>
                        </CardContent>
                      </Card>
                      <Card className="scada-panel">
                        <CardContent className="p-5">
                          <p className="text-[10px] lcd-text text-muted-foreground">Risk Forecast</p>
                          <p className={`text-3xl font-mono mt-1 font-bold ${indicatorTextClass(dashboardData.risk_monitor.indicator)}`}>
                            {ml?.predicted_risk_class?.toUpperCase() ?? "N/A"}
                          </p>
                          <p className="text-[10px] text-slate-500 mt-2 font-mono">ML Risk Index</p>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Chart visualizations */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[300px]">
                      <Card className="scada-panel flex flex-col h-full">
                        <CardHeader className="pb-0 pt-4 px-5">
                          <CardTitle className="text-xs lcd-text text-white/80">Population Coverage Area</CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 p-0 px-2 pb-2 mt-2">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={populationTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                              <defs>
                                <linearGradient id="colorPop" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                              <XAxis dataKey="time" stroke="rgba(255,255,255,0.2)" fontSize={10} tickLine={false} axisLine={false} />
                              <YAxis stroke="rgba(255,255,255,0.2)" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(val) => `${Math.round(Number(val) / 1000)}k`} />
                              <RechartsTooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.9)", borderColor: "rgba(6, 182, 212, 0.3)", borderRadius: "4px" }} itemStyle={{ color: "#06b6d4" }} formatter={(value: number) => [`${value.toLocaleString()} people`, "Population"]} />
                              <Area type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} fillOpacity={1} fill="url(#colorPop)" />
                            </AreaChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>

                      <Card className="scada-panel flex flex-col h-full">
                        <CardHeader className="pb-0 pt-4 px-5">
                          <CardTitle className="text-xs lcd-text text-white/80">Demographic Segment Distribution</CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 p-0 px-2 pb-4 mt-2">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={demographicChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                              <XAxis dataKey="group" stroke="rgba(255,255,255,0.3)" fontSize={10} tickLine={false} axisLine={false} />
                              <YAxis stroke="rgba(255,255,255,0.2)" fontSize={10} tickLine={false} axisLine={false} />
                              <RechartsTooltip contentStyle={{ backgroundColor: "rgba(15, 23, 42, 0.9)", borderColor: "rgba(255,255,255,0.1)", borderRadius: "4px" }} cursor={{ fill: "rgba(255,255,255,0.05)" }} formatter={(value: number) => [`${value}%`, "Value"]} />
                              <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                                {demographicChartData.map((_, index) => (
                                  <Cell key={`cell-${index}`} fill={index % 2 === 0 ? "hsl(var(--primary))" : "hsl(var(--accent))"} fillOpacity={0.8} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Explanations & Driver breakdown */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <Card className="scada-panel md:col-span-2">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-xs font-display tracking-wider uppercase text-white/90">Prediction Explanation Summary</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4 text-xs text-slate-300 leading-relaxed">
                          <p>{explanation?.revenue_explanation}</p>
                          <p>{explanation?.risk_explanation}</p>
                          <p>{explanation?.feasibility_explanation}</p>
                        </CardContent>
                      </Card>

                      <Card className="scada-panel">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-xs font-display tracking-wider uppercase text-white/90">Main Drivers</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <p className="text-[9px] text-emerald-400 font-mono uppercase tracking-widest mb-1.5">Positive Factors</p>
                            <div className="space-y-1">
                              {(explanation?.top_positive_factors ?? []).map((factor) => (
                                <p key={factor} className="text-xs text-slate-300 border-l border-emerald-400/30 pl-2">{factor}</p>
                              ))}
                            </div>
                          </div>
                          <div>
                            <p className="text-[9px] text-destructive font-mono uppercase tracking-widest mb-1.5">Negative Factors</p>
                            <div className="space-y-1">
                              {(explanation?.top_negative_factors ?? []).map((factor) => (
                                <p key={factor} className="text-xs text-slate-300 border-l border-destructive/30 pl-2">{factor}</p>
                              ))}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </>
                )}

                {/* 2. GEOSPATIAL MAP TAB */}
                {activeTab === "map" && (
                  <>
                    {geoContext ? (
                      <div className="mb-3 space-y-2">
                        {/* Honest reference-point banner: address anchor vs city centre */}
                        <div
                          className={`rounded-xl border px-4 py-2.5 text-xs font-mono flex items-start gap-2 ${
                            geoContext.anchor_type === "address"
                              ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-200"
                              : "border-amber-500/25 bg-amber-500/5 text-amber-200"
                          }`}
                        >
                          <MapPin className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                          <span>
                            {geoContext.anchor_note ||
                              (geoContext.anchor_type === "address"
                                ? `Centred on ${geoContext.resolved_address}`
                                : `Centred on ${geoContext.municipality_name} city centre.`)}
                            {geoContext.municipality_match === false
                              ? " ⚠ This address may be outside the selected municipality — confirm before trusting the numbers."
                              : ""}
                          </span>
                        </div>
                        {/* Honest feasibility-score basis banner */}
                        {geoContext.score_basis &&
                        geoContext.score_basis !== "exact_catalog" &&
                        geoContext.score_basis_note ? (
                          <div
                            className={`rounded-xl border px-4 py-2.5 text-xs font-mono flex items-start gap-2 ${
                              geoContext.score_basis === "unavailable"
                                ? "border-rose-500/25 bg-rose-500/5 text-rose-200"
                                : "border-sky-500/25 bg-sky-500/5 text-sky-200"
                            }`}
                          >
                            <Store className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                            <span>{geoContext.score_basis_note}</span>
                          </div>
                        ) : null}
                      </div>
                    ) : null}

                    <MarketMapPanel
                      geoContext={geoContext}
                      isLoading={isGeoLoading}
                      error={geoError}
                      onRetry={() => loadGeoContext(activeGeoPayload as GeospatialMarketMapRequest)}
                    />
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Site Address Panel */}
                      <SiteAddressAnalysisPanel
                        municipalityName={municipalityName}
                        businessSubcategory={businessSubcategory}
                        businessQuery={customBusinessQuery}
                        radiusKm={radius[0]}
                      />
                      
                      {/* Spatial Support Level */}
                      <ScenarioSupportPanel
                        municipalityName={municipalityName}
                        businessSubcategory={businessSubcategory}
                        radiusKm={radius[0]}
                        businessInputMode={businessInputMode}
                        customBusinessQuery={customBusinessQuery}
                        useCustomBusinessForMap={useCustomBusinessForMap}
                        businessResolution={businessResolution}
                      />
                    </div>
                  </>
                )}

                {/* 3. EVIDENCE INDICATORS TAB */}
                {activeTab === "evidence" && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Demand Card */}
                    <Card className="scada-panel border-white/5">
                      <CardContent className="p-5 space-y-4">
                        <div className="flex items-center justify-between border-b border-white/5 pb-2">
                          <div className="flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-emerald-400" />
                            <div>
                              <p className="text-[10px] text-muted-foreground uppercase font-mono">Demand Evidence</p>
                              <p className="text-xs font-mono text-white/80">{demandEvidence ? demandEvidence.credibility : "Fallback Proxy"}</p>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-emerald-400 border-emerald-400/30 uppercase font-mono text-[10px]">
                            {demandEvidence ? demandEvidence.demand_level : "Proxy"}
                          </Badge>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">DEMAND INDEX</p>
                            <p className="text-sm text-emerald-400 mt-0.5">{demandEvidence?.demand_pressure_index?.toFixed(1) ?? "N/A"}</p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">CUSTOMER POOL</p>
                            <p className="text-sm text-white mt-0.5">{demandEvidence ? formatNumber(demandEvidence.target_customer_pool_estimate) : "N/A"}</p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">FOOT TRAFFIC</p>
                            <p className="text-sm text-white mt-0.5">{demandEvidence?.foot_traffic_proxy_index?.toFixed(1) ?? "N/A"}</p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">TRANSIT INDEX</p>
                            <p className="text-sm text-white mt-0.5">{demandEvidence?.transit_access_proxy_index?.toFixed(1) ?? "N/A"}</p>
                          </div>
                        </div>

                        <p className="text-xs text-slate-400 leading-relaxed border-t border-white/5 pt-3">
                          {demandEvidence ? demandEvidence.data_quality_note : "No catalog row exists for this selected scenario. Using explicit fallback proxy index."}
                        </p>
                      </CardContent>
                    </Card>

                    {/* Competition Card */}
                    <Card className="scada-panel border-white/5">
                      <CardContent className="p-5 space-y-4">
                        <div className="flex items-center justify-between border-b border-white/5 pb-2">
                          <div className="flex items-center gap-2">
                            <Database className="w-5 h-5 text-primary" />
                            <div>
                              <p className="text-[10px] text-muted-foreground uppercase font-mono">Competition Evidence</p>
                              <p className="text-xs font-mono text-white/80">
                                {competitionIsLiveOsm
                                  ? (competitionEvidence?.source_name ?? "OpenStreetMap")
                                  : competitionEvidence
                                    ? competitionEvidence.credibility
                                    : "Fallback Proxy"}
                              </p>
                            </div>
                          </div>
                          <Badge
                            variant="outline"
                            className={
                              competitionIsLiveOsm
                                ? "text-emerald-300 border-emerald-400/40 uppercase font-mono text-[10px]"
                                : "text-primary border-primary/30 uppercase font-mono text-[10px]"
                            }
                          >
                            {competitionIsLiveOsm ? "Live OSM" : competitionEvidence ? "Catalog" : "Proxy"}
                          </Badge>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">COMPETITORS</p>
                            <p className="text-sm text-white mt-0.5">{competitionEvidence?.observed_competitor_count ?? "N/A"}</p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">DENSITY / 10K</p>
                            <p className="text-sm text-white mt-0.5">{competitionEvidence?.competitor_density_per_10k?.toFixed(2) ?? "N/A"}</p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">NEAREST POI</p>
                            <p className="text-sm text-white mt-0.5">
                              {competitionEvidence?.nearest_competitor_distance_km != null ? `${competitionEvidence.nearest_competitor_distance_km.toFixed(1)} km` : "N/A"}
                            </p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">COMP. PRESSURE</p>
                            <p className="text-sm text-primary mt-0.5">{competitionEvidence?.competition_pressure_index?.toFixed(1) ?? "N/A"}</p>
                          </div>
                        </div>

                        <p className="text-xs text-slate-400 leading-relaxed border-t border-white/5 pt-3">
                          {competitionEvidence ? competitionEvidence.source_method : "No catalog row exists for this selected scenario. Using explicit fallback proxy distance."}
                        </p>
                      </CardContent>
                    </Card>

                    {/* Lease Cost Card */}
                    <Card className="scada-panel border-white/5">
                      <CardContent className="p-5 space-y-4">
                        <div className="flex items-center justify-between border-b border-white/5 pb-2">
                          <div className="flex items-center gap-2">
                            <DollarSign className="w-5 h-5 text-accent" />
                            <div>
                              <p className="text-[10px] text-muted-foreground uppercase font-mono">Lease Cost Evidence</p>
                              <p className="text-xs font-mono text-white/80">{leaseCostEvidence ? leaseCostEvidence.credibility : "Fallback Proxy"}</p>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-accent border-accent/30 uppercase font-mono text-[10px]">
                            {leaseCostEvidence ? leaseCostEvidence.commercial_cost_pressure_level : "Proxy"}
                          </Badge>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">MEDIAN LEASE</p>
                            <p className="text-sm text-white mt-0.5">{formatCurrency(leaseCostEvidence?.median_monthly_lease_cost)}</p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded">
                            <p className="text-[9px] text-muted-foreground">COST / SQFT / YR</p>
                            <p className="text-sm text-white mt-0.5">
                              {leaseCostEvidence?.lease_cost_per_sqft_year != null ? `$${leaseCostEvidence.lease_cost_per_sqft_year.toFixed(2)}` : "N/A"}
                            </p>
                          </div>
                          <div className="border border-white/5 bg-white/[0.02] p-2 rounded col-span-2">
                            <p className="text-[9px] text-muted-foreground">MONTHLY ESTIMATE RANGE</p>
                            <p className="text-xs text-white mt-0.5">
                              {leaseCostEvidence ? `${formatCurrency(leaseCostEvidence.low_monthly_lease_cost)} - ${formatCurrency(leaseCostEvidence.high_monthly_lease_cost)}` : "N/A"}
                            </p>
                          </div>
                        </div>

                        <p className="text-xs text-slate-400 leading-relaxed border-t border-white/5 pt-3">
                          {leaseCostEvidence ? leaseCostEvidence.data_quality_note : "No lease evidence row exists for this selected scenario. Using explicit fallback range."}
                        </p>
                      </CardContent>
                    </Card>

                    {/* Data Credibility Audits */}
                    <Card className="scada-panel border-white/5 md:col-span-3">
                      <CardHeader className="pb-2">
                        <div className="flex justify-between items-center">
                          <CardTitle className="text-xs font-display tracking-wider uppercase text-white/90">Prediction Credibility Audit</CardTitle>
                          <Badge variant="outline" className={credibilityClass(credibility?.confidence_level)}>
                            {credibility?.confidence_level?.toUpperCase()} CONFIDENCE · {credibility?.overall_confidence_score?.toFixed(1)}/100
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4 text-xs">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <p className="text-[10px] text-emerald-400 font-mono uppercase tracking-widest">Observed Real Data</p>
                            <div className="space-y-1">
                              {(credibility?.observed_inputs ?? []).slice(0, 3).map((item) => (
                                <p key={item.field_name} className="p-2 border border-white/5 bg-white/[0.01] rounded">
                                  <strong className="text-white font-mono">{item.label}:</strong> {item.user_note}
                                </p>
                              ))}
                            </div>
                          </div>
                          <div className="space-y-2">
                            <p className="text-[10px] text-accent font-mono uppercase tracking-widest">Estimated Proxy Data</p>
                            <div className="space-y-1">
                              {(credibility?.proxy_estimated_inputs ?? []).slice(0, 3).map((item) => (
                                <p key={item.field_name} className="p-2 border border-accent/10 bg-accent/[0.01] rounded">
                                  <strong className="text-accent font-mono">{item.label}:</strong> {item.user_note}
                                </p>
                              ))}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* 4. OPERATING BENCHMARKS TAB */}
                {activeTab === "benchmarks" && (
                  <div className="space-y-6">
                    <OperatingProfilePanel
                      municipalityName={municipalityName}
                      radiusKm={radius[0]}
                      businessSubcategory={businessSubcategory}
                      businessQuery={customBusinessQuery}
                      businessResolution={businessResolution as unknown as Record<string, unknown> | null}
                      customBusinessMapActive={businessInputMode === "custom" && useCustomBusinessForMap}
                      initialProfile={operatingProfile}
                    />
                  </div>
                )}

                {/* 5. HISTORY & COMPARISONS TAB */}
                {activeTab === "history" && (
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    {/* Left comparison control and history list */}
                    <Card className="scada-panel border-white/5 lg:col-span-4 h-full">
                      <CardHeader className="pb-3 border-b border-white/5">
                        <CardTitle className="text-xs font-display tracking-wider uppercase text-white/90">Scenario Controls</CardTitle>
                      </CardHeader>
                      <CardContent className="p-4 space-y-4">
                        <div className="grid grid-cols-2 gap-2">
                          <Button
                            variant="outline"
                            className="bg-primary/10 hover:bg-primary/20 border-primary/30 text-primary-foreground font-mono text-xs uppercase"
                            onClick={handleSaveScenario}
                            disabled={isSavingScenario}
                          >
                            <Save className={`w-3.5 h-3.5 mr-1.5 ${isSavingScenario ? "animate-pulse" : ""}`} />
                            {isSavingScenario ? "Saving" : "Save Active"}
                          </Button>
                          <Button
                            variant="outline"
                            className="bg-white/[0.03] hover:bg-white/[0.07] border-white/10 text-white font-mono text-xs uppercase"
                            onClick={handleCompareScenarios}
                            disabled={isComparingScenarios || scenarioHistory.length < 1}
                          >
                            <GitCompare className={`w-3.5 h-3.5 mr-1.5 ${isComparingScenarios ? "animate-pulse" : ""}`} />
                            Run Compare
                          </Button>
                        </div>

                        {scenarioHistory.length > 0 && (
                          <Button
                            variant="ghost"
                            className="w-full text-[10px] text-white/50 hover:text-white/80 uppercase font-mono"
                            onClick={handleClearHistory}
                          >
                            Clear Comparison History
                          </Button>
                        )}

                        <div className="space-y-2 border-t border-white/5 pt-4">
                          <p className="text-[10px] text-muted-foreground uppercase font-mono">Saved Scenarios ({scenarioHistory.length})</p>
                          <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                            {scenarioHistory.map((item) => (
                              <div key={item.scenario_id} className="rounded border border-white/10 bg-white/[0.02] p-3 text-xs">
                                <p className="font-mono text-white font-semibold">{item.business_subcategory}</p>
                                <p className="text-[10px] text-slate-400 mt-0.5">{item.municipality_name} • {item.radius_km} km</p>
                                <p className="text-[10px] text-primary font-mono mt-1">
                                  {formatCurrency(item.predicted_monthly_net_revenue)} • Score: {item.predicted_feasibility_score?.toFixed(1) ?? "N/A"}
                                </p>
                              </div>
                            ))}
                            {scenarioHistory.length === 0 && (
                              <p className="text-[10px] text-slate-500 italic">No saved scenarios yet. Click &apos;Save Active&apos; to add the current workspace parameters.</p>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Right comparison matrix view */}
                    <div className="lg:col-span-8 space-y-6">
                      <LocationComparisonPanel
                        municipalityName={municipalityName}
                        businessSubcategory={businessSubcategory}
                        radiusKm={radius[0]}
                        onApplyScenario={({ municipality_name, business_subcategory, radius_km }) => {
                          setMunicipalityName(municipality_name);
                          setBusinessSubcategory(business_subcategory);
                          setRadius([radius_km]);
                        }}
                      />

                      {scenarioComparison && (
                        <Card className="scada-panel border-white/10 bg-accent/[0.01]">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-xs font-display tracking-wider uppercase text-accent">Comparison Summary Insights</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <p className="text-xs text-slate-300 leading-relaxed">
                              {scenarioComparison.comparison_summary}
                            </p>
                            
                            <div className="space-y-2 border-t border-white/5 pt-3">
                              <p className="text-[10px] text-muted-foreground uppercase font-mono">Rankings Matrix</p>
                              {scenarioComparison.rankings.map((item, index) => (
                                <div key={item.scenario_id} className="flex justify-between items-center p-2.5 rounded bg-white/[0.01] border border-white/5 text-xs">
                                  <span className="font-mono text-slate-300">
                                    <strong className="text-white">#{index + 1}</strong> {item.label}
                                  </span>
                                  <span className="font-mono text-accent font-bold">{item.overall_score.toFixed(1)}/100</span>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </div>
                )}

              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* --- FLOATING AI CHATBOT SYSTEM --- */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
        <AnimatePresence>
          {isChatOpen && (
            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 30, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="w-[90vw] sm:w-[420px] shadow-2xl rounded-2xl overflow-hidden border border-white/10 bg-slate-950/95 backdrop-blur-xl"
            >
              <div className="bg-primary/20 p-3 flex justify-between items-center border-b border-white/10">
                <div className="flex items-center gap-2">
                  <BrainCircuit className="w-5 h-5 text-primary" />
                  <span className="font-display text-xs text-white font-bold tracking-wider">Zonalyze AI Assistant</span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsChatOpen(false)}
                  className="p-1 rounded-md hover:bg-white/10 text-muted-foreground hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="max-h-[500px] overflow-y-auto p-2">
                <ScenarioAIChat
                  municipalityName={municipalityName}
                  businessSubcategory={businessSubcategory}
                  radiusKm={radius[0]}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Floating circular toggle button */}
        <button
          type="button"
          onClick={() => setIsChatOpen(!isChatOpen)}
          className={`w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 shadow-lg ${
            isChatOpen
              ? "bg-destructive text-white hover:bg-destructive/90"
              : "bg-primary text-white hover:bg-primary/95 shadow-primary/20 hover:scale-105"
          }`}
          title="Toggle Assistant"
        >
          {isChatOpen ? <X className="w-6 h-6" /> : <MessageSquare className="w-6 h-6 animate-pulse" />}
        </button>
      </div>
    </div>
  );
}
