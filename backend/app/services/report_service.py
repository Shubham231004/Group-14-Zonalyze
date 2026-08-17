from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.dashboard import DashboardSummaryResponse


BRAND_RED = colors.HexColor("#d80d0d")
INK = colors.HexColor("#171313")
MUTED = colors.HexColor("#6f6662")
PAPER = colors.HexColor("#fbf8f3")
LINE = colors.HexColor("#e6ddd4")
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "bestspot-logo.png"
TEAM_MEMBERS = "Shubham Patel | Girish Bhuteja | Kalp Mehta | Jainish Prajapati"


def _plain(value: Any, fallback: str = "Not available") -> str:
    if value is None or value == "":
        return fallback
    return (
        str(value)
        .replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
        .replace("\u00b2", "2")
    )


def _money(value: float | int | None) -> str:
    return "Not available" if value is None else f"${value:,.0f}"


def _pct(value: float | int | None) -> str:
    return "Not available" if value is None else f"{value:.1f}%"


def _score(value: float | int | None) -> str:
    return "Not available" if value is None else f"{value:.1f}/100"


def _number(value: float | int | None, decimals: int = 0) -> str:
    return "Not available" if value is None else f"{value:,.{decimals}f}"


def _metric_lookup(dashboard: DashboardSummaryResponse, *keys: str) -> float | None:
    metrics = getattr(getattr(dashboard, "people_location_packet", None), "metrics", []) or []
    for key in keys:
        for metric in metrics:
            if getattr(metric, "key", None) == key:
                return getattr(metric, "value", None)
    return None


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=26, leading=29, textColor=INK, alignment=0, spaceAfter=7,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=12, leading=16, textColor=MUTED, spaceAfter=18,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=BRAND_RED, spaceBefore=12, spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.8, leading=12, textColor=INK,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8.1, leading=11, textColor=MUTED,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9, textColor=MUTED, spaceAfter=5,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=14, leading=17, textColor=INK,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.8, leading=12, leftIndent=12, firstLineIndent=-9,
            textColor=INK, spaceAfter=4,
        ),
        "note": ParagraphStyle(
            "Note", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.1, leading=11.5, textColor=MUTED,
        ),
    }


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_plain(value)).replace("\n", "<br/>"), style)


def _section(title: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(escape(title.upper()), styles["section"])


def _data_table(rows: Iterable[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [_paragraph(label, styles["label"]), _paragraph(value, styles["body"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=[1.72 * inch, 5.0 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, PAPER]),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _metrics_table(metrics: list[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    cells = [
        [
            _paragraph(label.upper(), styles["metric_label"]),
            _paragraph(value, styles["metric_value"]),
        ]
        for label, value in metrics
    ]
    table = Table([cells[:2], cells[2:]], colWidths=[3.36 * inch, 3.36 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 13),
        ("RIGHTPADDING", (0, 0), (-1, -1), 13),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return table


def _bullets(items: Iterable[str], styles: dict[str, ParagraphStyle]) -> list[Paragraph]:
    values = [_plain(item) for item in items if item] or ["Not available"]
    return [Paragraph(f"- {escape(value)}", styles["bullet"]) for value in values]


def _draw_letterhead(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    width, height = LETTER
    canvas.saveState()
    canvas.setTitle("BestSpot Location Feasibility Report")
    canvas.setAuthor("BestSpot.biz")
    canvas.setFillColor(BRAND_RED)
    canvas.rect(0, height - 7, width, 7, stroke=0, fill=1)
    if LOGO_PATH.exists():
        canvas.drawImage(
            str(LOGO_PATH), doc.leftMargin, height - 82, width=176, height=64,
            preserveAspectRatio=True, anchor="w", mask="auto",
        )
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawRightString(width - doc.rightMargin, height - 34, "LOCATION INTELLIGENCE")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(width - doc.rightMargin, height - 48, "BIG IDEAS DESERVE THE RIGHT PLACE.")
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, height - 93, width - doc.rightMargin, height - 93)

    canvas.line(doc.leftMargin, 58, width - doc.rightMargin, 58)
    if LOGO_PATH.exists():
        canvas.drawImage(
            str(LOGO_PATH), doc.leftMargin, 19, width=78, height=29,
            preserveAspectRatio=True, anchor="w", mask="auto",
        )
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 7.2)
    canvas.drawRightString(width - doc.rightMargin, 39, TEAM_MEMBERS)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - doc.rightMargin, 25, f"BestSpot.biz | Page {doc.page}")
    canvas.restoreState()


def build_feasibility_report(dashboard: DashboardSummaryResponse) -> tuple[str, bytes]:
    ml = dashboard.ml_prediction
    explanation = dashboard.prediction_explanation
    breakdown = dashboard.analysis_breakdown
    credibility = dashboard.prediction_credibility
    competition = dashboard.competition_evidence
    lease = dashboard.lease_cost_evidence
    demand = dashboard.demand_evidence
    recommendation = dashboard.recommendation_decision

    safe_city = dashboard.municipality_name.lower().replace(" ", "-")
    safe_business = dashboard.business_subcategory.lower().replace(" ", "-").replace("/", "-")
    filename = f"bestspot-feasibility-report-{safe_city}-{safe_business}.pdf"
    generated_at = datetime.now().astimezone().strftime("%B %d, %Y at %I:%M %p %Z")

    population = _metric_lookup(dashboard, "population_total")
    density = _metric_lookup(dashboard, "population_density_per_km2")
    income = _metric_lookup(dashboard, "median_total_income", "household_median_total_income_2020")
    diversity = _metric_lookup(dashboard, "diversity_index_0_100")
    students = _metric_lookup(dashboard, "students_pct")
    families = _metric_lookup(dashboard, "families_pct")
    retirees = _metric_lookup(dashboard, "retirees_pct")
    recommendation_label = (
        recommendation.recommendation_label
        if recommendation
        else ml.recommendation.replace("_", " ").title() if ml
        else "Not available"
    )

    styles = _styles()
    story: list[Any] = [
        Paragraph("Location Feasibility Report", styles["title"]),
        Paragraph(
            f"{escape(_plain(dashboard.business_subcategory))} in {escape(_plain(dashboard.municipality_name))} "
            f"- {dashboard.radius_km:g} km customer reach<br/>Generated {escape(generated_at)}",
            styles["subtitle"],
        ),
        _metrics_table([
            ("Recommendation", recommendation_label),
            ("Feasibility estimate", _score(ml.predicted_feasibility_score if ml else None)),
            ("Monthly net estimate", _money(ml.predicted_monthly_net_revenue if ml else None)),
            ("Decision confidence", _score(recommendation.decision_confidence_score if recommendation else None)),
        ], styles),
        Spacer(1, 8),
        _section("Scenario", styles),
        _data_table([
            ("Municipality", dashboard.municipality_name),
            ("Business type", dashboard.business_subcategory),
            ("Search radius", f"{dashboard.radius_km:g} km"),
            ("Project phase", dashboard.project_phase),
            ("Risk class", ml.predicted_risk_class.replace("_", " ").title() if ml else None),
            ("Prediction confidence", f"{_score(credibility.overall_confidence_score if credibility else None)} ({_plain(credibility.confidence_level).title() if credibility else 'Not available'})"),
        ], styles),
        _section("Recommendation decision", styles),
        _data_table([
            ("Decision summary", recommendation.decision_summary if recommendation else None),
            ("Rationale", recommendation.decision_rationale if recommendation else None),
            ("Action guidance", recommendation.action_guidance if recommendation else None),
            ("Caution", recommendation.caution_note if recommendation else None),
        ], styles),
        PageBreak(),
        _section("Major strengths", styles),
        *_bullets(recommendation.major_strengths if recommendation else [], styles),
        _section("Major concerns", styles),
        *_bullets(recommendation.major_concerns if recommendation else [], styles),
        _section("Market snapshot", styles),
        _data_table([
            ("Population", _number(population)),
            ("Population density", f"{_number(density, 1)} people/km2"),
            ("Median household income", _money(income)),
            ("Diversity index", _score(diversity)),
            ("Student share", _pct(students)),
            ("Family share", _pct(families)),
            ("Retiree share", _pct(retirees)),
            ("Location summary", dashboard.people_location_packet.summary_text),
        ], styles),
        _section("Competition evidence", styles),
        _data_table([
            ("Source", competition.source_name if competition else None),
            ("Credibility", competition.credibility.title() if competition else "Limited"),
            ("Observed competitors", competition.observed_competitor_count if competition else None),
            ("Density per 10,000", _number(competition.competitor_density_per_10k if competition else None, 2)),
            ("Nearest competitor", f"{_number(competition.nearest_competitor_distance_km if competition else None, 2)} km"),
            ("Competition pressure", _score(competition.competition_pressure_index if competition else None)),
            ("Data quality note", competition.data_quality_note if competition else None),
        ], styles),
        PageBreak(),
        _section("Demand evidence", styles),
        _data_table([
            ("Source", demand.source_name if demand else None),
            ("Reachable population", _number(demand.reachable_population_estimate if demand else None)),
            ("Target customer pool", _number(demand.target_customer_pool_estimate if demand else None)),
            ("Foot traffic proxy", _score(demand.foot_traffic_proxy_index if demand else None)),
            ("Demand pressure", _score(demand.demand_pressure_index if demand else None)),
            ("Demand level", demand.demand_level.title() if demand else None),
            ("Data quality note", demand.data_quality_note if demand else None),
        ], styles),
        _section("Lease and operating picture", styles),
        _data_table([
            ("Source", lease.source_name if lease else None),
            ("Estimated space", f"{_number(lease.estimated_space_sqft if lease else None)} sq ft"),
            ("Monthly lease range", f"{_money(lease.low_monthly_lease_cost if lease else None)} to {_money(lease.high_monthly_lease_cost if lease else None)}"),
            ("Median monthly lease", _money(lease.median_monthly_lease_cost if lease else None)),
            ("Annual lease / sq ft", _money(lease.lease_cost_per_sqft_year if lease else None)),
            ("Cost pressure", lease.commercial_cost_pressure_level.title() if lease else None),
            ("Data quality note", lease.data_quality_note if lease else None),
        ], styles),
        PageBreak(),
        _section("Model factors", styles),
        _data_table([
            ("Competition pressure", _score(explanation.competition_score if explanation else None)),
            ("Demand proxy", _score(explanation.demand_score if explanation else None)),
            ("Demographic fit", _score(explanation.demographic_fit_score if explanation else None)),
            ("Estimated competitor count", explanation.estimated_competitor_count if explanation else None),
            ("Monthly operating cost", _money(explanation.monthly_operating_cost_estimate if explanation else None)),
            ("Demand analysis", breakdown.demand_analysis.summary if breakdown else None),
            ("Competition analysis", breakdown.competition_analysis.summary if breakdown else None),
            ("Lease analysis", breakdown.lease_cost_analysis.summary if breakdown else None),
        ], styles),
        _section("Positive factors", styles),
        *_bullets(explanation.top_positive_factors if explanation else [], styles),
        _section("Negative factors", styles),
        *_bullets(explanation.top_negative_factors if explanation else [], styles),
        _section("Credibility and next data needed", styles),
        _data_table([
            ("Confidence level", credibility.confidence_level.title() if credibility else None),
            ("Data quality score", _score(credibility.data_quality_score if credibility else None)),
            ("Model signal score", _score(credibility.model_signal_score if credibility else None)),
            ("Proxy dependency", _score(credibility.proxy_dependency_score if credibility else None)),
            ("Important note", credibility.user_facing_disclaimer if credibility else None),
        ], styles),
        *_bullets(credibility.next_data_needed if credibility else [], styles),
        Spacer(1, 8),
        Table(
            [[Paragraph(
                "This BestSpot report is decision support, not a guarantee of commercial performance. "
                "It separates observed inputs, model predictions, proxy estimates, and derived metrics.",
                styles["note"],
            )]],
            colWidths=[6.72 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]),
        ),
    ]

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch,
        topMargin=1.52 * inch, bottomMargin=0.92 * inch,
        title="BestSpot Location Feasibility Report", author="BestSpot.biz",
    )
    document.build(story, onFirstPage=_draw_letterhead, onLaterPages=_draw_letterhead)
    return filename, buffer.getvalue()
