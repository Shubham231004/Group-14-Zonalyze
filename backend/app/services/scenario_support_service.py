from __future__ import annotations

from app.schemas.scenario_support import (
    ScenarioSupportRequest,
    ScenarioSupportResponse,
    ScenarioSupportSection,
)
from app.services.catalog_service import get_business_subcategories, get_municipalities


def _catalog_business_supported(business_subcategory: str) -> bool:
    try:
        supported = {
            str(item.get("business_subcategory", "")).strip().lower()
            for item in get_business_subcategories()
        }
        return business_subcategory.strip().lower() in supported
    except Exception:
        # If the catalog cannot be loaded, do not crash the support validator.
        return False


def _municipality_supported(municipality_name: str) -> bool:
    try:
        supported = {
            str(item.get("municipality_name", "")).strip().lower()
            for item in get_municipalities()
        }
        return municipality_name.strip().lower() in supported
    except Exception:
        return False


def _section(status: str, label: str, summary: str, reasons=None, required_next_steps=None) -> ScenarioSupportSection:
    return ScenarioSupportSection(
        status=status,
        label=label,
        summary=summary,
        reasons=list(reasons or []),
        required_next_steps=list(required_next_steps or []),
    )


def evaluate_scenario_support(request: ScenarioSupportRequest) -> ScenarioSupportResponse:
    """
    Trust/coverage gate for user-governed scenarios.

    This does not run predictions and does not invent missing data. It only
    explains what is currently supported by the existing model and map-evidence
    pipeline.
    """
    warnings: list[str] = []
    notes: list[str] = []
    actions: list[str] = []

    municipality_ok = _municipality_supported(request.municipality_name)
    catalog_business_ok = _catalog_business_supported(request.business_subcategory)

    if municipality_ok:
        notes.append("Municipality is available in the census-derived dataset.")
    else:
        warnings.append("Selected municipality was not found in the census-backed municipality list.")

    if catalog_business_ok:
        prediction_support = _section(
            status="supported",
            label="ML prediction supported through catalog business",
            summary=(
                "The current ML prediction flow can run because it uses the selected "
                "catalog-backed business subcategory."
            ),
            reasons=[
                f"Prediction business subcategory: {request.business_subcategory}",
                "The model still depends on catalog-backed business assumptions, so arbitrary custom business text is not sent into prediction yet.",
            ],
        )
        actions.append("Run catalog-backed prototype prediction.")
    else:
        prediction_support = _section(
            status="needs_review",
            label="ML prediction not supported",
            summary="The selected catalog business was not found in the supported business catalog.",
            reasons=["The model requires a supported business_subcategory for prediction."],
            required_next_steps=["Select a supported catalog business before running ML prediction."],
        )
        warnings.append("ML prediction should not run until the catalog business input is supported.")

    mode = (request.business_input_mode or "catalog").lower().strip()
    has_custom_query = bool((request.custom_business_query or "").strip())
    resolver_status = (request.business_resolution_status or "").lower().strip()
    resolver_confidence = (request.business_resolution_confidence or "").lower().strip()
    has_tags = request.resolved_osm_tag_count > 0

    if mode == "custom":
        if not has_custom_query:
            map_evidence_support = _section(
                status="needs_review",
                label="Custom map evidence needs a business idea",
                summary="Custom business mode is selected, but no custom business idea was entered.",
                required_next_steps=["Enter a custom business idea and resolve it before using custom map evidence."],
            )
            warnings.append("Custom business mode has no business query yet.")
        elif resolver_status != "resolved" or not has_tags:
            map_evidence_support = _section(
                status="needs_review",
                label="Custom map evidence needs validated OSM tags",
                summary=(
                    "The custom business idea cannot safely drive OSM map evidence until the resolver "
                    "returns validated searchable OSM category tags."
                ),
                reasons=[
                    f"Resolver status: {request.business_resolution_status or 'not resolved'}",
                    f"Validated OSM tag count: {request.resolved_osm_tag_count}",
                ],
                required_next_steps=["Resolve the custom business idea and review the OSM tags before using it for map evidence."],
            )
            warnings.append("Custom business map evidence is not ready because OSM tags are unresolved or missing.")
        elif request.use_custom_business_for_map:
            map_evidence_support = _section(
                status="supported_limited",
                label="Custom map evidence active",
                summary=(
                    "The map can use the custom business idea because validated OSM tags are available. "
                    "Evidence strength still depends on OSM/Overpass coverage."
                ),
                reasons=[
                    f"Custom business query: {request.custom_business_query}",
                    f"Validated OSM tag count: {request.resolved_osm_tag_count}",
                    f"Resolver confidence: {resolver_confidence or 'not provided'}",
                ],
            )
            notes.append("Custom business idea is supported for map evidence, not yet for ML prediction.")
            actions.append("Use custom business query for OSM/Mapbox evidence.")
        else:
            map_evidence_support = _section(
                status="available_not_active",
                label="Custom map evidence available but disabled",
                summary=(
                    "The custom business idea has validated OSM tags, but the user has not enabled it "
                    "for map evidence yet."
                ),
                reasons=[f"Validated OSM tag count: {request.resolved_osm_tag_count}"],
                required_next_steps=["Enable custom map evidence if you want the map to use this business idea."],
            )
            actions.append("Enable custom map evidence after reviewing the interpretation.")
    else:
        map_evidence_support = _section(
            status="supported",
            label="Catalog map evidence active",
            summary="The map evidence uses the selected catalog-backed business subcategory.",
            reasons=[f"Map business subcategory: {request.business_subcategory}"],
        )
        actions.append("Use catalog business for map evidence.")

    if not municipality_ok:
        overall_status = "needs_review"
        overall_label = "Scenario location needs review"
    elif prediction_support.status == "needs_review" or map_evidence_support.status == "needs_review":
        overall_status = "needs_review"
        overall_label = "Scenario needs review before full confidence"
    elif map_evidence_support.status in {"supported_limited", "available_not_active"}:
        overall_status = "limited_supported"
        overall_label = "Scenario is partially supported"
    else:
        overall_status = "supported"
        overall_label = "Scenario is supported"

    notes.append(
        "Custom free-text business ideas are currently supported for business interpretation and map evidence first."
    )
    notes.append(
        "ML prediction remains catalog-backed until user-entered financial assumptions and stronger training coverage are added."
    )

    summary = (
        "Zonalyze separates catalog-backed prediction support from custom business map-evidence support "
        "so arbitrary user-entered ideas are not treated as fully validated model inputs."
    )

    return ScenarioSupportResponse(
        overall_status=overall_status,
        overall_label=overall_label,
        summary=summary,
        prediction_support=prediction_support,
        map_evidence_support=map_evidence_support,
        data_trust_notes=notes,
        warnings=warnings,
        allowed_next_actions=list(dict.fromkeys(actions)),
    )
