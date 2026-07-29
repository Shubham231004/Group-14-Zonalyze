import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BrainCircuit, Loader2, Send, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type ScenarioAIChatProps = {
  municipalityName: string;
  businessSubcategory: string;
  radiusKm: number;
};

type AIStatusResponse = {
  status?: string;
  provider?: string;
  default_model?: string;
  defaultModel?: string;
  message?: string;
  // Assistant availability details
  ollama_version?: string | null;
  model_installed?: boolean;
  structured_outputs?: boolean;
  structured_outputs_note?: string | null;
  warnings?: string[];
};

type ScenarioChatResponse = {
  status?: string;
  answer?: string;
  used_signals?: string[];
  usedSignals?: string[];
  limitations?: string[];
  raw_ai_available?: boolean;
  rawAiAvailable?: boolean;
  provider?: string;
  model?: string;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_BACKEND_URL ||
  "http://127.0.0.1:8000";

const SUGGESTED_QUESTIONS = [
  "Why is this scenario recommended or not recommended?",
  "What is the biggest risk in this scenario?",
  "What can I change to improve feasibility?",
  "Which values are real data and which are estimated?",
  "How reliable is this prediction?",
];

function normalizeSignals(response: ScenarioChatResponse | null): string[] {
  if (!response) return [];
  return response.used_signals || response.usedSignals || [];
}

function normalizeLimitations(response: ScenarioChatResponse | null): string[] {
  if (!response) return [];
  return response.limitations || [];
}

export default function ScenarioAIChat({
  municipalityName,
  businessSubcategory,
  radiusKm,
}: ScenarioAIChatProps) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<ScenarioChatResponse | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scenarioLabel = useMemo(
    () => `${businessSubcategory} in ${municipalityName} (${radiusKm} km)`,
    [businessSubcategory, municipalityName, radiusKm],
  );

  useEffect(() => {
    setAnswer(null);
    setQuestion("");
    setError(null);
  }, [municipalityName, businessSubcategory, radiusKm]);

  useEffect(() => {
    let cancelled = false;

    async function checkAIStatus() {
      try {
        setIsCheckingStatus(true);
        const response = await fetch(`${API_BASE_URL}/ai/status`);
        if (!response.ok) {
          throw new Error(`AI status check failed with ${response.status}`);
        }
        const data = (await response.json()) as AIStatusResponse;
        if (!cancelled) setAiStatus(data);
      } catch (err) {
        if (!cancelled) {
          setAiStatus({
            status: "unavailable",
            provider: "ollama",
            message: err instanceof Error ? err.message : "AI status unavailable",
          });
        }
      } finally {
        if (!cancelled) setIsCheckingStatus(false);
      }
    }

    checkAIStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  async function askQuestion(questionText?: string) {
    const finalQuestion = (questionText || question).trim();
    if (!finalQuestion || isAsking) return;

    try {
      setIsAsking(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/ai/scenario-chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          municipality_name: municipalityName,
          business_subcategory: businessSubcategory,
          radius_km: radiusKm,
          question: finalQuestion,
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `AI request failed with ${response.status}`);
      }

      const data = (await response.json()) as ScenarioChatResponse;
      setAnswer(data);
      setQuestion(finalQuestion);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI request failed.");
    } finally {
      setIsAsking(false);
    }
  }

  const isReady = aiStatus?.status === "ready";
  const statusLabel = isCheckingStatus
    ? "checking"
    : aiStatus?.status === "model_missing"
      ? "model missing"
      : aiStatus?.status || "unknown";
  const modelLabel = aiStatus?.default_model || aiStatus?.defaultModel || answer?.model || "local model";
  const usedSignals = normalizeSignals(answer);
  const limitations = normalizeLimitations(answer);

  // Assistant availability: structured outputs are what keep local-model JSON reliable.
  const structuredOutputs = aiStatus?.structured_outputs === true;
  const ollamaVersion = aiStatus?.ollama_version || null;
  const healthWarnings = aiStatus?.warnings ?? [];

  return (
    <Card className="scada-panel border-border overflow-hidden">
      <CardHeader className="border-b border-border pb-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-foreground">
              <BrainCircuit className="h-5 w-5 text-primary" />
              Ask BestSpot
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Ask follow-up questions about {scenarioLabel}. Answers use BestSpot scenario data, evidence, credibility, and recommendations.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={
                isReady
                  ? "border-emerald-400/30 text-emerald-700"
                  : "border-accent/30 text-accent"
              }
            >
              Assistant {statusLabel}
            </Badge>
            <Badge variant="outline" className="border-border text-muted-foreground">
              {modelLabel}
            </Badge>
            {ollamaVersion && (
              <Badge variant="outline" className="border-border text-muted-foreground">
                Ollama {ollamaVersion}
              </Badge>
            )}
            {aiStatus && !isCheckingStatus && (
              <Badge
                variant="outline"
                title={aiStatus.structured_outputs_note ?? undefined}
                className={
                  structuredOutputs
                    ? "border-emerald-400/30 text-emerald-700"
                    : "border-accent/30 text-accent"
                }
              >
                {structuredOutputs ? "Structured JSON on" : "Structured JSON off"}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 p-5">
        {healthWarnings.length > 0 && (
          <div className="rounded-xl border border-accent/30 bg-accent/10 p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-accent">
              <AlertTriangle className="h-4 w-4" />
              Assistant availability
            </div>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-accent/90">
              {healthWarnings.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {SUGGESTED_QUESTIONS.map((item) => (
            <Button
              key={item}
              type="button"
              variant="outline"
              size="sm"
              className="justify-start border-border bg-white/[0.03] text-left text-[11px] text-muted-foreground hover:bg-primary/10"
              onClick={() => askQuestion(item)}
              disabled={isAsking}
            >
              <Sparkles className="mr-2 h-3.5 w-3.5 shrink-0 text-primary" />
              <span className="truncate">{item}</span>
            </Button>
          ))}
        </div>

        <div className="flex flex-col gap-2 md:flex-row">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question about this scenario..."
            className="min-h-[86px] flex-1 resize-none rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground outline-none ring-0 placeholder:text-muted-foreground focus:border-primary/50"
          />
          <Button
            type="button"
            className="h-auto min-h-[44px] md:w-36"
            onClick={() => askQuestion()}
            disabled={!question.trim() || isAsking}
          >
            {isAsking ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Send className="mr-2 h-4 w-4" />
            )}
            {isAsking ? "Asking" : "Ask BestSpot"}
          </Button>
        </div>

        {error && (
          <div className="flex gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {answer?.answer && (
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
            <p className="text-xs font-mono uppercase tracking-widest text-primary/80">
              BestSpot response
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">
              {answer.answer}
            </p>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {usedSignals.length > 0 && (
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                    Used signals
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {usedSignals.slice(0, 8).map((signal) => (
                      <Badge key={signal} variant="outline" className="border-border text-muted-foreground">
                        {signal}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {limitations.length > 0 && (
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">
                    Limitations
                  </p>
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                    {limitations.slice(0, 3).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
