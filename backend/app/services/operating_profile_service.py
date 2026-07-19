from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List, Optional

from app.schemas.operating_profile import (
    OperatingProfileRange,
    OperatingProfileRequest,
    OperatingProfileResponse,
    OperatingProfileSection,
)
from app.services.local_ai_service import generate_with_ollama, generate_json_with_ollama

try:
    from app.ml.scenario_feature_builder import build_prediction_features
except Exception:  # pragma: no cover
    build_prediction_features = None  # type: ignore

try:
    from app.services.business_resolver_service import resolve_business_query
    from app.schemas.business_resolver import BusinessResolveRequest
except Exception:  # pragma: no cover
    resolve_business_query = None  # type: ignore
    BusinessResolveRequest = None  # type: ignore

try:
    from app.services.competition_data_service import get_competition_observation
    from app.services.demand_data_service import get_demand_evidence
    from app.services.lease_cost_data_service import get_lease_cost_evidence
except Exception:  # pragma: no cover
    get_competition_observation = None  # type: ignore
    get_demand_evidence = None  # type: ignore
    get_lease_cost_evidence = None  # type: ignore

from app.services.operating_profile_cache_service import (
    get_cached_operating_profile,
    save_operating_profile_cache,
)


SECTION_KEYS = {
    "space_requirement": "Space Requirement",
    "lease_cost": "Lease Cost Range",
    "staffing": "Staffing Pattern and Cost",
    "customer_economics": "Customer Economics",
    "utilities_marketing": "Utilities and Marketing Context",
}


# JSON schema passed to Ollama structured outputs. It forces the model to emit
# exactly 5 sections, each with a numeric low/median/high range — which is what
# fixes the previous "missing / $0 range" failures on small local models.
_SECTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "string"},
        "estimate_type": {"type": "string"},
        "confidence": {"type": "string"},
        "range": {
            "type": "object",
            "properties": {
                "low": {"type": "number"},
                "median": {"type": "number"},
                "high": {"type": "number"},
                "unit": {"type": "string"},
                "display_value": {"type": "string"},
            },
            "required": ["low", "median", "high", "unit"],
        },
        "summary": {"type": "string"},
        "reasoning": {"type": "array", "items": {"type": "string"}},
        "evidence_used": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["key", "range", "summary"],
}

OPERATING_PROFILE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "overall_confidence": {"type": "string"},
        "user_facing_note": {"type": "string"},
        "sections": {
            "type": "array",
            "items": _SECTION_JSON_SCHEMA,
            "minItems": 5,
            "maxItems": 5,
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
        "next_data_needed": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["sections"],
}


def _normalize_text(value: Any, max_length: int = 220) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_length]


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from an LLM response.

    Ollama JSON mode normally returns clean JSON, but smaller local models can
    still add whitespace, markdown fences, or occasionally trailing text. This
    extractor is intentionally conservative: it only returns a dict when Python's
    JSON parser can validate it.
    """
    if not text:
        return None

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    # First try the whole response.
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Then try balanced-brace extraction instead of naive first/last brace.
    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : index + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    return None

    return None

def _serializable(value: Any) -> Any:
    """Convert pydantic/dataclass-ish objects into JSON-friendly context."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return {str(k): _serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _build_context(request: OperatingProfileRequest) -> Dict[str, Any]:
    business_label = request.business_query or request.business_subcategory or "business"
    context: Dict[str, Any] = {
        "municipality_name": request.municipality_name,
        "radius_km": request.radius_km,
        "business_query": request.business_query,
        "business_subcategory": request.business_subcategory,
        "business_resolution": request.business_resolution,
        "available_evidence": {},
        "notes": [],
    }

    # Resolve business if caller did not already provide a resolution.
    if not context["business_resolution"] and request.business_query and resolve_business_query and BusinessResolveRequest:
        try:
            resolution = resolve_business_query(
                BusinessResolveRequest(
                    business_query=request.business_query,
                    municipality_name=request.municipality_name,
                    model=request.model,
                )
            )
            context["business_resolution"] = _serializable(resolution)
        except Exception as exc:
            context["notes"].append(f"Business resolution unavailable: {type(exc).__name__}")

    # Add current census/evidence context when the known catalog path can build features.
    # This does not calculate operating profile numbers. It only supplies existing data signals to the AI.
    if build_prediction_features and request.business_subcategory:
        try:
            features = build_prediction_features(
                municipality_name=request.municipality_name,
                business_subcategory=request.business_subcategory,
                radius_km=request.radius_km,
            )
            selected_feature_keys = [
                "population_2021",
                "population_density_per_km2",
                "household_median_total_income_2020",
                "employment_rate_pct",
                "unemployment_rate_pct",
                "renter_average_monthly_shelter_cost",
                "rent_pressure_index_0_100",
                "market_base_index_0_100",
                "demand_score_0_100",
                "monthly_lease_cost_estimate",
                "lease_cost_low_estimate",
                "lease_cost_high_estimate",
                "monthly_staff_cost_estimate",
                "monthly_utilities_cost_estimate",
                "monthly_marketing_cost_estimate",
                "average_ticket_size",
                "estimated_space_sqft",
                "gross_margin_pct",
            ]
            context["available_evidence"]["runtime_features"] = {
                key: features.get(key) for key in selected_feature_keys if key in features
            }

            population = float(features.get("population_2021", 0) or 0)
            if get_competition_observation:
                competition = get_competition_observation(
                    municipality_name=request.municipality_name,
                    business_subcategory=request.business_subcategory,
                    radius_km=request.radius_km,
                    population=population,
                )
                context["available_evidence"]["competition"] = _serializable(competition)
            if get_demand_evidence:
                demand = get_demand_evidence(
                    municipality_name=request.municipality_name,
                    business_subcategory=request.business_subcategory,
                    radius_km=request.radius_km,
                    features=features,
                )
                context["available_evidence"]["demand"] = _serializable(demand)
            if get_lease_cost_evidence:
                lease = get_lease_cost_evidence(
                    municipality_name=request.municipality_name,
                    business_subcategory=request.business_subcategory,
                    radius_km=request.radius_km,
                    features=features,
                )
                context["available_evidence"]["lease"] = _serializable(lease)
        except Exception as exc:
            context["notes"].append(f"Catalog evidence unavailable for {business_label}: {type(exc).__name__}")

    return context


def _build_prompt(context: Dict[str, Any]) -> str:
    """Compact strict JSON prompt for the operating-profile estimator.

    Do not include numeric zero examples in the schema. Small local models tend
    to copy example values literally, which produced $0 and 0 sq ft outputs.
    The prompt instead describes required fields and explicitly rejects zero
    operating ranges unless the scenario itself is impossible.
    """
    compact_context = json.dumps(context, ensure_ascii=False, default=str)[:6500]
    return f"""
You are Zonalyze's operating-profile estimator.
Return ONLY one valid JSON object. No markdown. No comments. No text outside JSON.

Task:
Generate practical planning estimate ranges for this business scenario. The user should NOT need to know rent, staffing, space, ticket size, utilities, or marketing upfront.

Non-negotiable rules:
- Every section must include numeric low, median, and high values greater than 0.
- Never return 0, 0.0, null, or placeholder ranges for an active business scenario.
- Use ranges, not single exact values.
- If exact evidence is weak, produce an AI benchmark planning range and label confidence as limited.
- Do not invent source names or URLs.
- Do not claim a value is observed unless the provided context contains that evidence.
- Use CAD for money and square feet for space.
- Use the scenario context and business model reasoning. If context includes evidence values, use them as evidence signals.
- For customer_economics, estimate average customer transaction spend in CAD/customer, not a percentage, probability, capture rate, or income fraction.
- Do not label a section as observed_evidence unless the scenario context directly contains that exact operating value and your evidence_used names the exact context field.
- If a value is inferred from available context plus AI reasoning, label it as evidence_assisted_ai_estimate or ai_benchmark_estimate, not observed_evidence.
- Ensure every range follows low <= median <= high.

Return exactly these top-level keys:
status, overall_confidence, user_facing_note, sections, warnings, next_data_needed

Return exactly 5 sections in this order:
1. space_requirement
2. lease_cost
3. staffing
4. customer_economics
5. utilities_marketing

Each section must be an object with:
key, title, status, estimate_type, confidence, range, summary, reasoning, evidence_used, limitations

Each range must be an object with:
low, median, high, unit, display_value

Required units:
- space_requirement: sq ft
- lease_cost: CAD/month
- staffing: CAD/month
- customer_economics: CAD/customer
- utilities_marketing: CAD/month

Use status values such as: estimated, evidence_supported, limited_estimate
Use estimate_type values such as: ai_benchmark_estimate, evidence_assisted_ai_estimate, observed_evidence
Use confidence values: limited, moderate, high

Scenario context JSON:
{compact_context}
""".strip()


def _coerce_section(raw: Dict[str, Any], fallback_key: str) -> OperatingProfileSection:
    key = _normalize_text(raw.get("key") or fallback_key, 80).lower() or fallback_key
    title = _normalize_text(raw.get("title") or SECTION_KEYS.get(key, key.replace("_", " ").title()), 120)
    raw_range = raw.get("range") if isinstance(raw.get("range"), dict) else None
    range_obj = None
    if raw_range:
        range_obj = OperatingProfileRange(
            low=_safe_float(raw_range.get("low")),
            median=_safe_float(raw_range.get("median")),
            high=_safe_float(raw_range.get("high")),
            unit=_normalize_text(raw_range.get("unit"), 40),
            display_value=_normalize_text(raw_range.get("display_value"), 120),
        )

    def clean_list(value: Any, limit: int = 5) -> List[str]:
        if not isinstance(value, list):
            return []
        output: List[str] = []
        for item in value[:limit]:
            text = _normalize_text(item, 220)
            if text:
                output.append(text)
        return output

    return OperatingProfileSection(
        key=key,
        title=title,
        status=_normalize_text(raw.get("status") or "estimated", 60),
        estimate_type=_normalize_text(raw.get("estimate_type") or "ai_benchmark_estimate", 80),
        confidence=_normalize_text(raw.get("confidence") or "limited", 40),
        range=range_obj,
        summary=_normalize_text(raw.get("summary") or "Zonalyze generated a planning estimate for this section.", 400),
        reasoning=clean_list(raw.get("reasoning")),
        evidence_used=clean_list(raw.get("evidence_used")),
        limitations=clean_list(raw.get("limitations")),
    )




def _format_range_display(section_key: str, range_obj: OperatingProfileRange) -> str:
    """Format AI-provided range values for display without estimating new values."""
    low = range_obj.low
    median = range_obj.median
    high = range_obj.high
    unit = range_obj.unit or ""
    if low is None or median is None or high is None:
        return range_obj.display_value or ""

    if "CAD" in unit:
        if "customer" in unit.lower():
            return f"${low:,.2f} - ${high:,.2f}/customer"
        return f"${low:,.0f} - ${high:,.0f}/month"
    if "sq" in unit.lower():
        return f"{low:,.0f} - {high:,.0f} sq ft"
    return f"{low:g} - {high:g} {unit}".strip()


def _postprocess_section_quality(section: OperatingProfileSection) -> None:
    """Normalize AI output without creating operating estimates.

    This function only repairs ordering/labels/formatting from values already
    provided by the model. It does not calculate lease, staffing, space, or ticket
    predictions.
    """
    if section.range is not None:
        values = [section.range.low, section.range.median, section.range.high]
        if all(isinstance(value, (int, float)) for value in values):
            ordered = sorted(float(value) for value in values)  # type: ignore[arg-type]
            section.range.low, section.range.median, section.range.high = ordered
            section.range.display_value = _format_range_display(section.key, section.range)

    # Do not let the AI overclaim observed evidence when it did not name evidence.
    if section.estimate_type == "observed_evidence" and not section.evidence_used:
        section.estimate_type = "evidence_assisted_ai_estimate"
        if section.confidence == "high":
            section.confidence = "moderate"
        section.limitations.append(
            "The model labeled this as observed evidence, but no exact evidence field was cited, so Zonalyze downgraded it to an evidence-assisted estimate."
        )


def _section_quality_issues(section: OperatingProfileSection) -> List[str]:
    """Detect unusable or clearly mismatched AI operating-profile output.

    These are sanity checks, not estimation formulas. They prevent obviously bad
    AI outputs such as $0 ranges or $0.05/customer grocery-ticket values from
    entering the dashboard as if they were useful estimates.
    """
    issues: List[str] = []
    if section.range is None:
        return [f"{section.key}: missing numeric range"]

    low = section.range.low
    median = section.range.median
    high = section.range.high
    values = [low, median, high]
    if any(value is None for value in values):
        issues.append(f"{section.key}: incomplete numeric range")
        return issues
    if any(float(value or 0) <= 0 for value in values):
        issues.append(f"{section.key}: range contains zero or negative value")
        return issues
    if not (float(low) <= float(median) <= float(high)):  # type: ignore[arg-type]
        issues.append(f"{section.key}: range is not ordered low <= median <= high")

    # Unit-specific sanity checks. These do not estimate values; they reject
    # outputs that are clearly the wrong measurement, e.g., percentage returned
    # as CAD/customer.
    median_value = float(median or 0)
    if section.key == "customer_economics" and median_value < 1:
        issues.append(
            "customer_economics: value appears to be a percentage/probability instead of CAD average transaction spend"
        )
    if section.key == "space_requirement" and median_value < 100:
        issues.append("space_requirement: value is too small to represent a business premises size in sq ft")
    if section.key in {"lease_cost", "staffing", "utilities_marketing"} and median_value < 100:
        issues.append(f"{section.key}: value is too small to represent a monthly operating cost in CAD")

    if section.estimate_type == "observed_evidence" and not section.evidence_used:
        issues.append(f"{section.key}: claimed observed_evidence without naming evidence_used")

    return issues


def _postprocess_response_quality(response: OperatingProfileResponse) -> List[str]:
    """Apply safe cleanups and return remaining quality issues."""
    for section in response.sections:
        _postprocess_section_quality(section)

    issues: List[str] = []
    for section in response.sections:
        issues.extend(_section_quality_issues(section))

    if issues:
        warning = "Operating profile quality guard detected and reviewed AI-generated ranges before dashboard use."
        if warning not in response.warnings:
            response.warnings.insert(0, warning)
    return issues

def _coerce_response(payload: Dict[str, Any], request: OperatingProfileRequest, context: Dict[str, Any], model: Optional[str]) -> OperatingProfileResponse:
    raw_sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
    sections: List[OperatingProfileSection] = []
    seen = set()

    for index, raw in enumerate(raw_sections):
        if not isinstance(raw, dict):
            continue
        fallback_key = list(SECTION_KEYS.keys())[min(index, len(SECTION_KEYS) - 1)]
        section = _coerce_section(raw, fallback_key)
        if section.key not in seen:
            sections.append(section)
            seen.add(section.key)

    # If the model omitted a section, ask the frontend to show a stable set by adding unavailable placeholders.
    # These placeholders do not invent values; they only prevent UI crashes.
    for key, title in SECTION_KEYS.items():
        if key not in seen:
            sections.append(
                OperatingProfileSection(
                    key=key,
                    title=title,
                    status="unavailable",
                    estimate_type="unavailable",
                    confidence="unavailable",
                    range=None,
                    summary="The local AI did not return this estimate in the required structured output.",
                    reasoning=[],
                    evidence_used=[],
                    limitations=["Retry operating profile generation or use a smaller/faster local model."],
                )
            )

    business_resolution = context.get("business_resolution") if isinstance(context.get("business_resolution"), dict) else {}
    normalized_business_name = business_resolution.get("normalized_business_name") or request.business_query or request.business_subcategory

    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    next_data_needed = payload.get("next_data_needed") if isinstance(payload.get("next_data_needed"), list) else []

    return OperatingProfileResponse(
        status=_normalize_text(payload.get("status") or "estimated", 50),
        municipality_name=request.municipality_name,
        business_query=request.business_query,
        business_subcategory=request.business_subcategory,
        normalized_business_name=_normalize_text(normalized_business_name, 180),
        radius_km=request.radius_km,
        source_method="local_ai_benchmark_operating_profile_with_available_context",
        cache_status="miss",
        model=model,
        overall_confidence=_normalize_text(payload.get("overall_confidence") or "limited", 40),
        user_facing_note=_normalize_text(
            payload.get("user_facing_note")
            or "Zonalyze generated an AI benchmark operating profile for planning. Treat limited-confidence sections as estimates, not verified quotes.",
            500,
        ),
        sections=sections,
        warnings=[_normalize_text(item, 220) for item in warnings[:8] if _normalize_text(item, 220)],
        next_data_needed=[_normalize_text(item, 220) for item in next_data_needed[:8] if _normalize_text(item, 220)],
        raw_ai_available=True,
        raw_ai_error=None,
    )



def _section_has_unusable_zero_range(section: OperatingProfileSection) -> bool:
    """Detect the exact bad outcome where the model copied zero placeholders.

    This validation does not generate fallback numbers. It only rejects unusable
    AI output and asks the local model to try again with clearer instructions.
    """
    if section.range is None:
        return True
    values = [section.range.low, section.range.median, section.range.high]
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    if len(numeric_values) < 3:
        return True
    return any(value is None or value <= 0 for value in values if value is not None) or all(float(value or 0) == 0.0 for value in values)


def _response_has_unusable_ranges(response: OperatingProfileResponse) -> bool:
    if not response.sections:
        return True
    required = set(SECTION_KEYS.keys())
    present = {section.key for section in response.sections}
    if not required.issubset(present):
        return True
    return bool(_postprocess_response_quality(response))


def _retry_nonzero_operating_profile(
    *,
    original_prompt: str,
    invalid_answer: str,
    context: Dict[str, Any],
    model: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Ask the AI to regenerate estimates when it returned valid JSON but copied zeros.

    This is still AI estimation, not a static fallback. The backend does not fill
    any business cost numbers itself.
    """
    compact_context = json.dumps(context, ensure_ascii=False, default=str)[:6500]
    retry_prompt = f"""
Return ONLY valid JSON.
Your previous operating-profile response contained unusable or mismatched ranges.
Regenerate the operating profile with realistic non-zero AI benchmark planning ranges.

Rules:
- Every range.low, range.median, and range.high must be greater than 0.
- Use conservative realistic ranges for the business type and municipality context.
- For customer_economics, provide average transaction spend in CAD/customer, not a percentage or probability.
- Do not label observed_evidence unless evidence_used names exact context fields.
- Do not use placeholder 0 values.
- Do not ask the user for inputs.
- Do not invent source names or URLs.
- Label confidence as limited if evidence is weak.
- Use the same required 5 sections: space_requirement, lease_cost, staffing, customer_economics, utilities_marketing.
- Return top-level keys: status, overall_confidence, user_facing_note, sections, warnings, next_data_needed.

Scenario context JSON:
{compact_context}

Invalid previous response:
{invalid_answer[:5000]}
""".strip()
    retried = generate_json_with_ollama(
        prompt=retry_prompt,
        model=model,
        timeout_seconds=180,
        num_predict=2200,
        json_schema=OPERATING_PROFILE_JSON_SCHEMA,
    )
    if not retried.available:
        return None
    return _extract_json_object(retried.answer)


def _ai_unavailable_response(request: OperatingProfileRequest, error: Optional[str]) -> OperatingProfileResponse:
    return OperatingProfileResponse(
        status="ai_unavailable",
        municipality_name=request.municipality_name,
        business_query=request.business_query,
        business_subcategory=request.business_subcategory,
        normalized_business_name=request.business_query or request.business_subcategory,
        radius_km=request.radius_km,
        source_method="local_ai_unavailable_no_static_formula_fallback",
        cache_status="not_saved",
        model=request.model,
        overall_confidence="unavailable",
        user_facing_note=(
            "The operating profile requires the local AI estimator. Zonalyze did not create static fallback numbers because operating costs must not be hardcoded."
        ),
        sections=[
            OperatingProfileSection(
                key=key,
                title=title,
                status="unavailable",
                estimate_type="unavailable",
                confidence="unavailable",
                range=None,
                summary="Local AI was unavailable, so Zonalyze did not generate an operating-cost estimate.",
                limitations=["Start Ollama or select a faster local model, then retry."],
            )
            for key, title in SECTION_KEYS.items()
        ],
        warnings=["Local AI was unavailable. No static operating-cost fallback was used."],
        next_data_needed=["Reliable operating profile generation requires local AI and, later, public wage/lease benchmark datasets."],
        raw_ai_available=False,
        raw_ai_error=error,
    )



def _repair_operating_profile_json(raw_answer: str, model: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retry once by asking Ollama JSON mode to repair its own output.

    This is not a numeric fallback. It only repairs formatting when the model
    produced a reasonable answer wrapped in invalid JSON.
    """
    if not raw_answer:
        return None

    repair_prompt = f"""
Return ONLY valid JSON. Repair the following operating-profile response into the required JSON object.
Do not add markdown. Do not explain.
Keep the same business estimates if present. If a required section is missing, add it with conservative AI benchmark values.

Required top-level keys:
status, overall_confidence, user_facing_note, sections, warnings, next_data_needed
Required section keys:
space_requirement, lease_cost, staffing, customer_economics, utilities_marketing
Each section must include: key,title,status,estimate_type,confidence,range,summary,reasoning,evidence_used,limitations.

Broken response:
{raw_answer[:9000]}
""".strip()
    repaired = generate_json_with_ollama(
        prompt=repair_prompt,
        model=model,
        timeout_seconds=120,
        num_predict=1800,
        json_schema=OPERATING_PROFILE_JSON_SCHEMA,
    )
    if not repaired.available:
        return None
    return _extract_json_object(repaired.answer)

def build_operating_profile(request: OperatingProfileRequest) -> OperatingProfileResponse:
    business_query = _normalize_text(request.business_query, 240) or None
    business_subcategory = _normalize_text(request.business_subcategory, 180) or None

    cached = get_cached_operating_profile(
        municipality_name=request.municipality_name,
        radius_km=request.radius_km,
        business_query=business_query,
        business_subcategory=business_subcategory,
        model=request.model,
    )
    if cached:
        return cached

    clean_request = OperatingProfileRequest(
        municipality_name=_normalize_text(request.municipality_name, 160),
        radius_km=request.radius_km,
        business_query=business_query,
        business_subcategory=business_subcategory,
        business_resolution=request.business_resolution,
        model=request.model,
    )

    context = _build_context(clean_request)
    prompt = _build_prompt(context)

    # Use Ollama's native JSON mode for this endpoint. Scenario chat can return prose,
    # but the operating-profile endpoint must parse structured JSON.
    ai_result = generate_json_with_ollama(
        prompt=prompt,
        model=clean_request.model,
        timeout_seconds=180,
        num_predict=1800,
        json_schema=OPERATING_PROFILE_JSON_SCHEMA,
    )

    # Backward compatibility for older Ollama installs/models that may not support
    # `format: json` cleanly. This still asks for JSON and does not create static values.
    if not ai_result.available:
        ai_result = generate_with_ollama(prompt=prompt, model=clean_request.model, timeout_seconds=180)

    if not ai_result.available:
        return _ai_unavailable_response(clean_request, ai_result.error)

    payload = _extract_json_object(ai_result.answer)
    if not payload:
        payload = _repair_operating_profile_json(ai_result.answer, clean_request.model)

    if not payload:
        return _ai_unavailable_response(
            clean_request,
            "Local AI responded, but its operating-profile JSON could not be parsed after one repair attempt.",
        )

    response = _coerce_response(payload, clean_request, context, clean_request.model)

    # Valid JSON is not enough. The AI can still return impossible units/values,
    # such as $0.05/customer for grocery average-ticket economics. Reject bad
    # structured output and retry once with stronger quality instructions.
    quality_issues = _postprocess_response_quality(response)
    if quality_issues:
        issue_note = "; ".join(quality_issues[:6])
        retry_payload = _retry_nonzero_operating_profile(
            original_prompt=prompt,
            invalid_answer=(
                f"Quality issues: {issue_note}\n\n"
                f"Previous answer:\n{ai_result.answer}"
            ),
            context=context,
            model=clean_request.model,
        )
        if retry_payload:
            retried_response = _coerce_response(retry_payload, clean_request, context, clean_request.model)
            retried_issues = _postprocess_response_quality(retried_response)
            if not retried_issues:
                response = retried_response
            else:
                response.raw_ai_error = "Local AI returned structured operating-profile JSON, but quality guard still found issues after retry: " + "; ".join(retried_issues[:6])
                response.warnings.insert(0, "Some operating-profile values need review because the local AI returned implausible or mislabeled ranges after retry.")
        else:
            response.raw_ai_error = "Local AI returned structured operating-profile JSON, but quality guard retry failed: " + issue_note
            response.warnings.insert(0, "Some operating-profile values need review because the local AI returned implausible or mislabeled ranges.")

    saved = save_operating_profile_cache(
        municipality_name=clean_request.municipality_name,
        radius_km=clean_request.radius_km,
        business_query=clean_request.business_query,
        business_subcategory=clean_request.business_subcategory,
        model=clean_request.model,
        response=response,
    )
    response.cache_status = "miss_saved" if saved else "miss_not_saved"
    return response
