from pathlib import Path
from typing import Dict, List

import pandas as pd

from app.catalogs.business_subcategories import list_business_subcategory_options


CITY_FEATURES_PATH = Path("app/data/processed/ontario_csd_selected_features_2021.csv")


def get_municipalities() -> List[Dict[str, str]]:
    """
    Return municipalities from the processed census dataset only.

    This intentionally does not add fallback/demo municipalities. If a
    municipality appears in the app, it should come from the census-derived
    feature dataset so the location list remains data-driven.
    """
    if not CITY_FEATURES_PATH.exists():
        raise FileNotFoundError(f"City feature file not found: {CITY_FEATURES_PATH}")

    df = pd.read_csv(CITY_FEATURES_PATH)

    municipalities = (
        df[["municipality_name", "municipality_type"]]
        .dropna(subset=["municipality_name"])
        .drop_duplicates()
        .sort_values("municipality_name")
    )

    return [
        {
            "municipality_name": str(row["municipality_name"]),
            "municipality_type": str(row["municipality_type"]),
            "label": f"{row['municipality_name']} ({row['municipality_type']})",
        }
        for _, row in municipalities.iterrows()
    ]


def get_business_subcategories() -> List[Dict[str, str]]:
    """
    Return supported business subcategories from the shared business catalog.

    This expands business-type coverage without hardcoding scenarios or
    municipalities. The values here are catalog metadata used by the feature
    builder and OSM lookup layer.
    """
    return list_business_subcategory_options()
