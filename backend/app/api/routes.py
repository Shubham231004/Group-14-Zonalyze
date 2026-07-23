import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.test_connection import test_database_connection
from app.db.dependencies import get_db
from app.schemas.bus import RegisteredSensorsResponse, PacketHistoryResponse
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.report import FeasibilityReportResponse
from app.schemas.scenario import AnalyzeScenarioRequest
from app.schemas.validation import SystemValidationResponse
from app.schemas.model_status import ModelStatusResponse
from app.schemas.feature_alignment import FeatureAlignmentResponse
from app.schemas.dashboard import PredictionCredibilityResponse
from app.schemas.competition import CompetitionObservationCatalogResponse, CompetitionObservationEvidence
from app.schemas.lease import LeaseCostCatalogResponse, LeaseCostEvidence
from app.schemas.demand import DemandEvidenceCatalogResponse, DemandEvidence
from app.schemas.recommendation import RecommendationDecision
from app.schemas.scenario_history import ScenarioComparisonResponse, ScenarioHistoryItem, ScenarioHistoryResponse
from app.schemas.geospatial import GeospatialMarketContext, GeospatialMarketRequest
from app.schemas.location_comparison import LocationComparisonRequest, LocationComparisonResponse
from app.schemas.site_address import SiteAddressAnalysisRequest, SiteAddressAnalysisResponse
from app.schemas.sensor_packet import SensorPacket
from app.schemas.ai_assistant import LocalAIStatusResponse, ScenarioChatRequest, ScenarioChatResponse
from app.schemas.business_resolver import BusinessResolveRequest, BusinessResolveResponse
from app.schemas.storage_status import MongoStatusResponse
from app.schemas.scenario_support import ScenarioSupportRequest, ScenarioSupportResponse
from app.services.storage_status_service import get_mongo_status
from app.services.scenario_support_service import evaluate_scenario_support
from app.services.business_resolver_service import resolve_business_query
from app.schemas.operating_profile import OperatingProfileRequest, OperatingProfileResponse
from app.services.operating_profile_service import build_operating_profile
from app.services.ai_assistant_service import answer_scenario_question
from app.services.local_ai_service import get_local_ai_status
from app.services.catalog_service import get_municipalities, get_business_subcategories
from app.services.dashboard_service import get_dashboard_summary, analyze_scenario
from app.services.location_comparison_service import compare_locations
from app.services.message_bus_service import (
    get_registered_sensors,
    get_latest_packet,
    get_packet_history,
)
from app.services.report_service import build_feasibility_report
from app.services.validation_service import run_system_validation
from app.services.model_status_service import get_model_status
from app.services.feature_alignment_service import run_feature_alignment
from app.ml.scenario_feature_builder import build_prediction_features
from app.ml.predictor import get_predictor
from app.services.credibility_service import build_prediction_credibility
from app.services.competition_data_service import get_competition_observation, list_competition_observations
from app.services.lease_cost_data_service import get_lease_cost_evidence, list_lease_cost_observations
from app.services.demand_data_service import get_demand_evidence, list_demand_observations
from app.services.recommendation_service import build_recommendation_decision

from app.services.scenario_history_service import (
    clear_saved_scenarios,
    compare_saved_scenarios,
    list_saved_scenarios,
    save_dashboard_to_history,
)
from app.services.geospatial_service import build_geospatial_market_context
from app.services.site_address_service import analyze_site_address
from app.services.osm_service import fetch_osm_competitors, fetch_osm_transit, fetch_osm_commercial_activity


logger = logging.getLogger(__name__)

router = APIRouter()

# Public router: endpoints that must stay reachable without authentication
# (liveness checks, load balancers). Everything on `router` is auth-protected
# when Clerk is configured; these two are not.
public_router = APIRouter()


@public_router.get("/")
def root():
    return {
        "message": "Zonalyze backend is running"
    }


@public_router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "backend"
    }


@router.get("/db-check")
def db_check():
    success, detail = test_database_connection()

    if not success:
        # Log the underlying error server-side; return a generic message so the
        # response never exposes connection internals.
        logger.warning("Database connectivity check failed: %s", detail)
        return {
            "database_connected": False,
            "message": "Database connection failed.",
        }

    return {
        "database_connected": True,
        "message": "Database connection successful",
    }


@router.get("/storage/mongo-status", response_model=MongoStatusResponse)
def mongo_status_route():
    return get_mongo_status()


@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
def dashboard_summary(db: Session = Depends(get_db)):
    return get_dashboard_summary(db)


@router.post("/analyze-scenario", response_model=DashboardSummaryResponse)
def analyze_scenario_route(
    request: AnalyzeScenarioRequest,
    db: Session = Depends(get_db),
):
    return analyze_scenario(request=request, db=db)


@router.post("/reports/feasibility", response_model=FeasibilityReportResponse)
def feasibility_report_route(
    request: AnalyzeScenarioRequest,
    db: Session = Depends(get_db),
):
    dashboard = analyze_scenario(request=request, db=db)
    return build_feasibility_report(dashboard)



@router.get("/ml/model-status", response_model=ModelStatusResponse)
def model_status_route():
    return get_model_status()


@router.get("/ml/feature-alignment", response_model=FeatureAlignmentResponse)
def feature_alignment_default_route():
    return run_feature_alignment()


@router.post("/ml/feature-alignment", response_model=FeatureAlignmentResponse)
def feature_alignment_route(request: AnalyzeScenarioRequest):
    return run_feature_alignment(request)


@router.post("/ml/prediction-credibility", response_model=PredictionCredibilityResponse)
def prediction_credibility_route(request: AnalyzeScenarioRequest):
    features = build_prediction_features(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )
    features["municipality_name"] = request.municipality_name
    # Evidence overrides are display-only; the model scores the clean, training-
    # consistent feature row built by the shared pipeline.
    prediction_result = get_predictor().predict(features)
    return build_prediction_credibility(
        features=features,
        prediction_result=prediction_result,
    )

@router.post("/business/resolve", response_model=BusinessResolveResponse)
def resolve_business_route(request: BusinessResolveRequest):
    return resolve_business_query(request)

@router.post("/business/operating-profile", response_model=OperatingProfileResponse)
def operating_profile_route(request: OperatingProfileRequest):
    return build_operating_profile(request)

@router.post("/scenario/support-coverage", response_model=ScenarioSupportResponse)
def scenario_support_coverage_route(request: ScenarioSupportRequest):
    return evaluate_scenario_support(request)

@router.post("/scenario/location-comparison", response_model=LocationComparisonResponse)
def location_comparison_route(request: LocationComparisonRequest):
    # Compare Locations: the service/schemas existed but this route was never
    # registered, so the frontend's call 404'd. Wiring it fixes the feature.
    return compare_locations(request)

@router.post("/recommendation/decision", response_model=RecommendationDecision)
def recommendation_decision_route(request: AnalyzeScenarioRequest):
    features = build_prediction_features(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )
    features["municipality_name"] = request.municipality_name
    # Evidence is display/decision context only; the model scores the clean,
    # training-consistent feature row (evidence must not mutate model inputs).
    competition_evidence = get_competition_observation(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        population=float(features.get("population_2021", 0) or 0),
    )
    lease_cost_evidence = get_lease_cost_evidence(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        features=features,
    )
    demand_evidence = get_demand_evidence(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        features=features,
    )
    prediction_result = get_predictor().predict(features)
    credibility = build_prediction_credibility(
        features=features,
        prediction_result=prediction_result,
    )
    return build_recommendation_decision(
        features=features,
        prediction_result=prediction_result,
        credibility=credibility,
        competition_evidence=competition_evidence,
        lease_cost_evidence=lease_cost_evidence,
        demand_evidence=demand_evidence,
    )

@router.get("/ai/status", response_model=LocalAIStatusResponse)
def local_ai_status_route():
    return get_local_ai_status()


@router.post("/ai/scenario-chat", response_model=ScenarioChatResponse)
def scenario_chat_route(
    request: ScenarioChatRequest,
    db: Session = Depends(get_db),
):
    return answer_scenario_question(request=request, db=db)

@router.get("/validation/system", response_model=SystemValidationResponse)
def system_validation_route(db: Session = Depends(get_db)):
    return run_system_validation(db)


@router.get("/market/competition-observations", response_model=CompetitionObservationCatalogResponse)
def competition_observations_route():
    observations = list_competition_observations()
    return CompetitionObservationCatalogResponse(
        count=len(observations),
        observations=observations,
    )


@router.post("/market/competition-evidence", response_model=CompetitionObservationEvidence | None)
def competition_evidence_route(request: AnalyzeScenarioRequest):
    # Same store-first source as the map/dashboard so this endpoint never
    # disagrees with them (it used to return the seed, or null when no seed row).
    from app.services.competition_data_service import build_osm_competition_evidence
    from app.services.geospatial_service import _center_for_municipality
    from app.services.osm_service import fetch_osm_competitors

    features = build_prediction_features(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )
    population = float(features.get("population_2021", 0) or 0)
    center_lat, center_lon = _center_for_municipality(request.municipality_name)
    osm_competitors = fetch_osm_competitors(
        request.business_subcategory, center_lat, center_lon, request.radius_km, store_only=True
    )
    return build_osm_competition_evidence(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        population=population,
        osm_elements=osm_competitors.elements,
        is_live=osm_competitors.status == "live_osm",
    ) or get_competition_observation(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        population=population,
    )




@router.get("/market/lease-cost-observations", response_model=LeaseCostCatalogResponse)
def lease_cost_observations_route():
    observations = list_lease_cost_observations()
    return LeaseCostCatalogResponse(
        count=len(observations),
        observations=observations,
    )


@router.post("/market/lease-cost-evidence", response_model=LeaseCostEvidence)
def lease_cost_evidence_route(request: AnalyzeScenarioRequest):
    features = build_prediction_features(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )
    features["municipality_name"] = request.municipality_name
    return get_lease_cost_evidence(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        features=features,
    )


@router.get("/market/demand-observations", response_model=DemandEvidenceCatalogResponse)
def demand_observations_route():
    observations = list_demand_observations()
    return DemandEvidenceCatalogResponse(
        count=len(observations),
        observations=observations,
    )


@router.post("/market/demand-evidence", response_model=DemandEvidence)
def demand_evidence_route(request: AnalyzeScenarioRequest):
    # Pass city-centre coords so the indices ground in the real POI store, same
    # as the dashboard/map (it used to return the ungrounded proxy).
    from app.services.geospatial_service import _center_for_municipality

    features = build_prediction_features(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )
    features["municipality_name"] = request.municipality_name
    center_lat, center_lon = _center_for_municipality(request.municipality_name)
    return get_demand_evidence(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        features=features,
        center_lat=center_lat,
        center_lon=center_lon,
    )




@router.post("/geo/market-map", response_model=GeospatialMarketContext)
def geospatial_market_map_route(request: GeospatialMarketRequest):
    return build_geospatial_market_context(request)


@router.post("/geo/site-address-analysis", response_model=SiteAddressAnalysisResponse)
def site_address_analysis_route(request: SiteAddressAnalysisRequest):
    return analyze_site_address(request)




@router.post("/geo/osm-pois")
def osm_pois_route(request: AnalyzeScenarioRequest):
    from app.services.geospatial_service import _center_for_municipality

    center_lat, center_lng = _center_for_municipality(request.municipality_name)
    competitors = fetch_osm_competitors(
        business_subcategory=request.business_subcategory,
        center_lat=center_lat,
        center_lon=center_lng,
        radius_km=request.radius_km,
        limit=60,
    )
    transit = fetch_osm_transit(
        center_lat=center_lat,
        center_lon=center_lng,
        radius_km=request.radius_km,
        limit=30,
    )
    commercial = fetch_osm_commercial_activity(
        center_lat=center_lat,
        center_lon=center_lng,
        radius_km=request.radius_km,
        limit=20,
    )
    return {
        "municipality_name": request.municipality_name,
        "business_subcategory": request.business_subcategory,
        "radius_km": request.radius_km,
        "center": {"latitude": center_lat, "longitude": center_lng},
        "competitors": {"status": competitors.status, "note": competitors.note, "count": len(competitors.elements), "items": competitors.elements},
        "transit": {"status": transit.status, "note": transit.note, "count": len(transit.elements), "items": transit.elements},
        "commercial_activity": {"status": commercial.status, "note": commercial.note, "count": len(commercial.elements), "items": commercial.elements},
    }


@router.post("/scenario-history/save", response_model=ScenarioHistoryItem)
def save_scenario_history_route(
    request: AnalyzeScenarioRequest,
    db: Session = Depends(get_db),
):
    dashboard = analyze_scenario(request=request, db=db)
    return save_dashboard_to_history(dashboard, db)


@router.get("/scenario-history", response_model=ScenarioHistoryResponse)
def list_scenario_history_route(db: Session = Depends(get_db)):
    return list_saved_scenarios(db)


@router.delete("/scenario-history", response_model=ScenarioHistoryResponse)
def clear_scenario_history_route(db: Session = Depends(get_db)):
    return clear_saved_scenarios(db)


@router.post("/scenario-history/compare", response_model=ScenarioComparisonResponse)
def compare_scenario_history_route(db: Session = Depends(get_db)):
    return compare_saved_scenarios(db)


@router.get("/municipalities")
def municipalities_route():
    return {"municipalities": get_municipalities()}


@router.get("/business-subcategories")
def business_subcategories_route():
    return {"business_subcategories": get_business_subcategories()}


@router.get("/bus/registered-sensors", response_model=RegisteredSensorsResponse)
def bus_registered_sensors():
    return RegisteredSensorsResponse(
        sensors=get_registered_sensors()
    )


@router.get("/bus/latest/{sensor_type}", response_model=SensorPacket | None)
def bus_latest_packet(sensor_type: str):
    return get_latest_packet(sensor_type)


@router.get("/bus/history/{sensor_type}", response_model=PacketHistoryResponse)
def bus_packet_history(sensor_type: str):
    packets = get_packet_history(sensor_type)

    return PacketHistoryResponse(
        sensor_type=sensor_type,
        count=len(packets),
        packets=packets
    )
