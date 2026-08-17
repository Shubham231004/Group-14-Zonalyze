"""Build the committed Ontario pedestrian-count snapshot from official sources.

Run from ``backend`` with::

    python -m app.scripts.update_observed_footfall

Only measured pedestrian observations are included. Bicycle-only counters, vehicle
counts, inferred activity, and municipalities without published observations are
deliberately omitted.
"""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import requests


OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "market"
    / "observed_footfall_counts.csv"
)

TORONTO_DATA_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/"
    "6afa3b1f-f6a5-4235-8bd6-7568411c19f4"
)
TORONTO_SOURCE_URL = (
    "https://open.toronto.ca/dataset/"
    "traffic-volumes-at-intersections-for-all-modes/"
)
WATERLOO_LAYER_URL = (
    "https://services.arcgis.com/ZpeBVw5o1kjit7LT/arcgis/rest/services/"
    "EcoCounters/FeatureServer/0"
)
WATERLOO_SOURCE_URL = (
    "https://www.arcgis.com/home/item.html?id=a5e1adba2e5545a9b4f0a1d198cd0498"
)
BARRIE_LAYER_URL = (
    "https://gispublic.barrie.ca/arcgis/rest/services/Open_Data/"
    "FacilitiesStreets/MapServer/5"
)
BARRIE_SOURCE_URL = (
    "https://gispublic.barrie.ca/arcgis/rest/services/Open_Data/"
    "FacilitiesStreets/MapServer/5"
)
LENNOX_LAYER_URL = (
    "https://services.arcgis.com/YmmKxwNVvLQW5zcm/arcgis/rest/services/"
    "Intersection_Turning_Movement_Data_Station_(Public)/FeatureServer/0"
)
LENNOX_SOURCE_URL = (
    "https://www.arcgis.com/home/item.html?id=0d3b7f5587b84d2a8f46f2461787a1ca"
)
HAMILTON_DATA_URL = "https://cityofhamiltonmobility.eco-counter.com/"
HAMILTON_SOURCE_URL = (
    "https://www.hamilton.ca/home-neighbourhood/getting-around/biking-cyclists/"
    "active-transportation-benchmarking-program"
)

FIELDNAMES = (
    "municipality",
    "site_id",
    "label",
    "latitude",
    "longitude",
    "observed_count",
    "observed_unit",
    "observation_period",
    "source",
    "source_url",
)


def _get(url: str, **kwargs: Any) -> requests.Response:
    response = requests.get(url, timeout=60, **kwargs)
    response.raise_for_status()
    return response


def _arcgis_features(layer_url: str, *, where: str = "1=1") -> list[dict[str, Any]]:
    response = _get(
        f"{layer_url}/query",
        params={
            "where": where,
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultRecordCount": "10000",
            "f": "json",
        },
    ).json()
    if response.get("error"):
        raise RuntimeError(f"ArcGIS query failed for {layer_url}: {response['error']}")
    return response.get("features", [])


def _static_kitchener_rows() -> Iterable[dict[str, Any]]:
    yield {
        "municipality": "Kitchener",
        "site_id": "100021132",
        "label": "Iron Horse Trail - Queen Street",
        "latitude": 43.443488819,
        "longitude": -80.496073865,
        "observed_count": 423,
        "observed_unit": "average pedestrians/day",
        "observation_period": "2025 daily average",
        "source": "City of Kitchener trail counters",
        "source_url": (
            "https://www.kitchener.ca/strategic-plans-and-projects/strategic-plan/"
            "2023-2026-strategic-plan-progress/"
        ),
    }


def _waterloo_rows() -> Iterable[dict[str, Any]]:
    for feature in _arcgis_features(WATERLOO_LAYER_URL):
        attributes = feature["attributes"]
        weekday = attributes.get("WKDY_PED")
        weekend = attributes.get("WKND_PED")
        if weekday is None or weekend is None or (weekday <= 0 and weekend <= 0):
            continue
        geometry = feature.get("geometry", {})
        yield {
            "municipality": "Waterloo",
            "site_id": str(int(attributes["ID"])),
            "label": attributes["LOCATION"],
            "latitude": geometry.get("y") or float(attributes["LAT"]),
            "longitude": geometry.get("x") or float(attributes["LONG"]),
            "observed_count": round((weekday * 5 + weekend * 2) / 7, 2),
            "observed_unit": "average pedestrians/day",
            "observation_period": (
                "Published weighted weekday/weekend average; source is updated monthly"
            ),
            "source": "City of Waterloo EcoCounters",
            "source_url": WATERLOO_SOURCE_URL,
        }


def _hamilton_rows() -> Iterable[dict[str, Any]]:
    html = _get(HAMILTON_DATA_URL).text
    year_match = re.search(
        r'dateRange\\":\{\\"value\\":\\"currentYear\\",\\"year\\":(\d{4})',
        html,
    )
    if not year_match:
        raise RuntimeError("Hamilton Eco-Counter page did not expose its current-year range")
    reporting_year = int(year_match.group(1))

    site_pattern = re.compile(
        r'\{\\"id\\":(?P<id>\d+),\\"name\\":\\"(?P<name>.*?)\\"'
        r'.*?\\"location\\":\{\\"lat\\":(?P<lat>-?[\d.]+),'
        r'\\"lon\\":(?P<lon>-?[\d.]+)\}'
        r'.*?\\"firstData\\":\\"(?P<first>\d{4}-\d{2}-\d{2})T.*?\\"'
        r'.*?\\"lastData\\":\\"(?P<last>\d{4}-\d{2}-\d{2})T.*?\\"'
        r'.*?\\"travelModes\\":\[(?P<modes>.*?)\]'
        r'.*?\\"travelModesAndValues\\":\{(?P<values>[^}]*)\}',
        re.DOTALL,
    )
    seen: set[str] = set()
    for match in site_pattern.finditer(html):
        site_id = match.group("id")
        if site_id in seen or '\\"pedestrian\\"' not in match.group("modes"):
            continue
        count_match = re.search(r'\\"pedestrian\\":([\d.]+)', match.group("values"))
        if not count_match:
            continue
        observed_total = float(count_match.group(1))
        first_day = date.fromisoformat(match.group("first"))
        last_day = date.fromisoformat(match.group("last"))
        period_start = max(first_day, date(reporting_year, 1, 1))
        if last_day < period_start or last_day.year != reporting_year or observed_total <= 0:
            continue
        seen.add(site_id)
        reporting_days = (last_day - period_start).days + 1
        yield {
            "municipality": "Hamilton",
            "site_id": site_id,
            "label": match.group("name").replace("\\u0026", "&"),
            "latitude": float(match.group("lat")),
            "longitude": float(match.group("lon")),
            "observed_count": round(observed_total / reporting_days, 2),
            "observed_unit": "average pedestrians/day",
            "observation_period": (
                f"{period_start.isoformat()} to {last_day.isoformat()} current-year average; "
                f"derived from {observed_total:g} published pedestrian passages"
            ),
            "source": "City of Hamilton Active Transportation Benchmarking Program",
            "source_url": HAMILTON_SOURCE_URL,
        }


def _toronto_rows() -> Iterable[dict[str, Any]]:
    reader = csv.DictReader(_get(TORONTO_DATA_URL).text.splitlines())
    for row in reader:
        duration_match = re.match(r"\d+", row.get("count_duration", ""))
        if not duration_match or not row.get("latitude") or not row.get("longitude"):
            continue
        duration_hours = int(duration_match.group())
        pedestrian_total = float(row.get("total_pedestrian") or 0)
        if duration_hours <= 0 or pedestrian_total <= 0:
            continue
        yield {
            "municipality": "Toronto",
            "site_id": row["latest_count_id"],
            "label": row["location_name"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "observed_count": round(pedestrian_total / duration_hours, 2),
            "observed_unit": "average pedestrians/hour during count",
            "observation_period": (
                f"Latest {duration_hours}-hour count on {row['latest_count_date']}; "
                f"derived from {pedestrian_total:g} published pedestrians"
            ),
            "source": "City of Toronto Multimodal Intersection Counts",
            "source_url": TORONTO_SOURCE_URL,
        }


def _barrie_rows() -> Iterable[dict[str, Any]]:
    for feature in _arcgis_features(BARRIE_LAYER_URL, where="PEDESTRIANS > 0"):
        attributes = feature["attributes"]
        geometry = feature.get("geometry", {})
        yield {
            "municipality": "Barrie",
            "site_id": str(attributes["OBJECTID"]),
            "label": attributes["LOCATION"],
            "latitude": geometry["y"],
            "longitude": geometry["x"],
            "observed_count": attributes["PEDESTRIANS"],
            "observed_unit": "pedestrians/turning-movement count",
            "observation_period": f"{attributes['DATE_YEAR']} published count",
            "source": "City of Barrie Traffic Counts",
            "source_url": BARRIE_SOURCE_URL,
        }


LENNOX_PEDESTRIAN_FIELDS = (
    (2021, "PED21"),
    (2020, "PED20"),
    (2019, "Ped19"),
    (2018, "Ped18"),
    (2017, "Ped17"),
    (2016, "Ped16"),
    (2015, "X015PED"),
    (2014, "X014PED"),
    (2013, "X013PED"),
    (2012, "X012PED"),
    (2011, "X011PED"),
    (2010, "X010PED"),
    (2009, "X009PED"),
    (2008, "X008PED"),
    (2007, "X007PED"),
)


def _lennox_rows() -> Iterable[dict[str, Any]]:
    municipality_names = {"Loyalist Township": "Loyalist"}
    for feature in _arcgis_features(LENNOX_LAYER_URL):
        attributes = feature["attributes"]
        latest = next(
            (
                (year, float(attributes[field]))
                for year, field in LENNOX_PEDESTRIAN_FIELDS
                if attributes.get(field) is not None and float(attributes[field]) > 0
            ),
            None,
        )
        if not latest:
            continue
        year, count = latest
        geometry = feature.get("geometry", {})
        municipality = municipality_names.get(
            attributes.get("Municipality"), attributes.get("Municipality")
        )
        if not municipality:
            continue
        yield {
            "municipality": municipality,
            "site_id": attributes["TM"],
            "label": attributes["Location"],
            "latitude": geometry["y"],
            "longitude": geometry["x"],
            "observed_count": count,
            "observed_unit": "pedestrians/turning-movement count",
            "observation_period": f"Latest published pedestrian count ({year})",
            "source": "County of Lennox and Addington Turning Movement Counts",
            "source_url": LENNOX_SOURCE_URL,
        }


def build_rows() -> list[dict[str, Any]]:
    rows = [
        *list(_static_kitchener_rows()),
        *list(_waterloo_rows()),
        *list(_hamilton_rows()),
        *list(_toronto_rows()),
        *list(_barrie_rows()),
        *list(_lennox_rows()),
    ]
    deduplicated = {
        (str(row["municipality"]), str(row["site_id"])): row for row in rows
    }
    return sorted(
        deduplicated.values(),
        key=lambda row: (
            str(row["municipality"]),
            str(row["label"]),
            str(row["site_id"]),
        ),
    )


def main() -> None:
    rows = build_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    municipalities = sorted({str(row["municipality"]) for row in rows})
    print(
        f"Wrote {len(rows)} observed pedestrian locations across "
        f"{len(municipalities)} municipalities to {OUTPUT_PATH}"
    )
    print(", ".join(municipalities))


if __name__ == "__main__":
    main()
