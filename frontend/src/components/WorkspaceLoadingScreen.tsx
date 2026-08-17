import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";

import BrandLogo from "@/components/BrandLogo";

type WorkspaceLoadingScreenProps = {
  mode?: "workspace" | "analysis";
  municipalityName?: string;
  businessName?: string;
  progress?: number;
  statusMessage?: string;
};

export default function WorkspaceLoadingScreen({
  mode = "workspace",
  municipalityName = "your area",
  businessName = "business",
  progress,
  statusMessage,
}: WorkspaceLoadingScreenProps) {
  const isAnalysis = mode === "analysis";
  const [messageIndex, setMessageIndex] = useState(0);
  const progressValue = Math.max(0, Math.min(100, Math.round(progress ?? 0)));
  const isComplete = isAnalysis && progressValue >= 100;
  const analysisMessages = [
    `Checking ${municipalityName} for your ${businessName.toLowerCase()}.`,
    "Mapping nearby businesses and your selected customer radius.",
    "Reading local demand, footfall, competition, and cost signals.",
    "Testing the evidence against your business model.",
    "Almost done — shaping your BestSpot recommendation.",
  ];

  useEffect(() => {
    setMessageIndex(0);
    if (!isAnalysis) return;
    const interval = window.setInterval(() => {
      setMessageIndex((current) => Math.min(current + 1, analysisMessages.length - 1));
    }, 2000);
    return () => window.clearInterval(interval);
  }, [isAnalysis, municipalityName, businessName, analysisMessages.length]);

  const headline = isComplete
    ? "Your BestSpot results are ready."
    : isAnalysis
      ? analysisMessages[messageIndex]
      : "Bringing your next location into focus.";
  const description = isAnalysis
    ? statusMessage || "Connecting local evidence into one clear decision view."
    : "Connecting your map, saved spots, and local market signals into one clear decision view.";
  const signals = isAnalysis
    ? ["Mapping the area", "Reading local signals", "Shaping your recommendation"]
    : ["Mapping the area", "Reading local signals", "Shaping your workspace"];
  const activeSignal = progressValue >= 90 ? 2 : progressValue >= 55 ? 1 : 0;

  return (
    <main className="app-loading-shell" aria-busy="true">
      <section className="workspace-loader" role="status" aria-live="polite" aria-atomic="true">
        <div className="workspace-loader-map" aria-hidden="true">
          <span className="workspace-loader-road workspace-loader-road--one" />
          <span className="workspace-loader-road workspace-loader-road--two" />
          <span className="workspace-loader-road workspace-loader-road--three" />
          <span className="workspace-loader-scan" />
          <span className="workspace-loader-radius workspace-loader-radius--outer" />
          <span className="workspace-loader-radius workspace-loader-radius--inner" />
          <span className="workspace-loader-orbit"><i /></span>
          <span className="workspace-loader-node workspace-loader-node--one" />
          <span className="workspace-loader-node workspace-loader-node--two" />
          <span className="workspace-loader-node workspace-loader-node--three" />
          <span className="workspace-loader-pin"><MapPin /></span>
          <span className="workspace-loader-map-label">
            <i /> {isComplete ? "Analysis complete" : isAnalysis ? "Live market scan" : "Live location scan"}
          </span>
        </div>

        <div className="workspace-loader-copy">
          <BrandLogo size="large" />
          <p className="eyebrow">{isAnalysis ? "Building your decision view" : "Location intelligence in motion"}</p>
          <h1 key={headline} className="workspace-loader-headline">{headline}</h1>
          <p className="workspace-loader-description">{description}</p>

          <div
            className={`workspace-loader-track${isAnalysis ? " is-determinate" : ""}${isComplete ? " is-complete" : ""}`}
            role={isAnalysis ? "progressbar" : undefined}
            aria-label={isAnalysis ? "Location analysis progress" : undefined}
            aria-valuemin={isAnalysis ? 0 : undefined}
            aria-valuemax={isAnalysis ? 100 : undefined}
            aria-valuenow={isAnalysis ? progressValue : undefined}
            aria-hidden={isAnalysis ? undefined : true}
          >
            <span style={isAnalysis ? { width: `${progressValue}%` } : undefined} />
          </div>
          <div className={`workspace-loader-signals${isAnalysis ? " is-staged" : ""}`} aria-hidden="true">
            {signals.map((signal, index) => (
              <span
                key={signal}
                className={
                  isAnalysis
                    ? index < activeSignal || isComplete
                      ? "is-complete"
                      : index === activeSignal
                        ? "is-active"
                        : ""
                    : undefined
                }
              >
                <i /> {signal}
              </span>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
