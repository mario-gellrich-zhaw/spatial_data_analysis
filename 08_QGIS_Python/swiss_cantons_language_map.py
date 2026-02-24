"""
Swiss Cantons – Language Region Map
=====================================
PyQGIS script that builds a styled QGIS project file.

Steps
-----
  1. Download Swiss cantonal boundaries from GADM 4.1 (cached after first run)
  2. Add 'language_region' field to every feature (pure Python / JSON)
  3. Initialize QGIS in headless mode
  4. Load the processed GeoJSON as a QgsVectorLayer
  5. Apply categorised symbology (colour per language region)
  6. Save a QGIS project file  →  swiss_cantons_language_regions.qgz

Open swiss_cantons_language_regions.qgz in QGIS Desktop to view the map.

Usage
-----
  conda activate qgisenv
  python swiss_cantons_language_map.py
"""

import os
import sys
import json
import pathlib
import requests

SCRIPT_DIR   = pathlib.Path(__file__).parent.resolve()
CONDA_PREFIX = pathlib.Path(os.environ.get("CONDA_PREFIX", sys.prefix))

# ── Windows: expose QGIS / Qt DLLs that conda puts in Library\bin ────────────
if sys.platform == "win32":
    dll_dir = CONDA_PREFIX / "Library" / "bin"
    if dll_dir.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_dir))
    QGIS_PREFIX = str(CONDA_PREFIX / "Library")
else:
    QGIS_PREFIX = str(CONDA_PREFIX)

# Headless Qt (no display server needed)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ── QGIS imports (must follow DLL / env setup above) ─────────────────────────
try:
    from qgis.core import (  # type: ignore[import-untyped]
        QgsApplication,
        QgsVectorLayer,
        QgsProject,
        QgsCoordinateReferenceSystem,
        QgsReferencedRectangle,
        QgsCategorizedSymbolRenderer,
        QgsRendererCategory,
        QgsFillSymbol,
    )
except ImportError as exc:
    raise ImportError(
        "QGIS Python bindings not found. "
        "Activate the 'qgisenv' conda environment first:\n"
        "  conda activate qgisenv\n"
        "  python swiss_cantons_language_map.py"
    ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Language-region reference data
#     Source: Swiss Federal Chancellery  https://www.bk.admin.ch
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_REGIONS: dict[str, str] = {
    # German-speaking (17 cantons)
    "ZH": "German",  "LU": "German",  "UR": "German",  "SZ": "German",
    "OW": "German",  "NW": "German",  "GL": "German",  "ZG": "German",
    "SO": "German",  "BS": "German",  "BL": "German",  "SH": "German",
    "AR": "German",  "AI": "German",  "SG": "German",  "AG": "German",
    "TG": "German",
    # French-speaking – Romandy (4 cantons)
    "VD": "French",  "NE": "French",  "GE": "French",  "JU": "French",
    # Italian-speaking – Ticino (1 canton)
    "TI": "Italian",
    # Bilingual German / French (3 cantons)
    "BE": "Mixed DE/FR",  "FR": "Mixed DE/FR",  "VS": "Mixed DE/FR",
    # Trilingual German / Romansh / Italian (1 canton)
    "GR": "Mixed DE/RM/IT",
}

REGION_COLORS: dict[str, str] = {
    "German":          "#4472C4",   # blue
    "French":          "#E74C3C",   # red
    "Italian":         "#27AE60",   # green
    "Mixed DE/FR":     "#9B59B6",   # purple
    "Mixed DE/RM/IT":  "#F39C12",   # amber
}

REGION_LABELS: dict[str, str] = {
    "German":          "German (17 cantons)",
    "French":          "French — Romandy (4 cantons)",
    "Italian":         "Italian — Ticino (1 canton)",
    "Mixed DE/FR":     "Bilingual DE/FR  (BE, FR, VS)",
    "Mixed DE/RM/IT":  "Trilingual DE/RM/IT  (GR)",
}


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Data preparation  (pure Python, no QGIS required)
# ─────────────────────────────────────────────────────────────────────────────

GADM_URL          = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_CHE_1.json"
RAW_GEOJSON       = SCRIPT_DIR / "swiss_cantons_gadm.geojson"
PROCESSED_GEOJSON = SCRIPT_DIR / "swiss_cantons_processed.geojson"
PROJECT_FILE      = SCRIPT_DIR / "swiss_cantons_language_regions.qgz"


def download_boundaries() -> None:
    """Download Swiss canton boundaries from GADM (skipped if already cached)."""
    if RAW_GEOJSON.exists():
        print(f"Using cached data: {RAW_GEOJSON.name}")
        return
    print("Downloading canton boundaries from GADM 4.1 …")
    resp = requests.get(GADM_URL, timeout=120)
    resp.raise_for_status()
    RAW_GEOJSON.write_text(resp.text, encoding="utf-8")
    print(f"  → saved {RAW_GEOJSON.name}")


def add_language_region_field() -> None:
    """Inject 'language_region' into every GeoJSON feature and write a new file."""
    print("Adding language_region field …")
    geojson = json.loads(RAW_GEOJSON.read_text(encoding="utf-8"))

    for feature in geojson["features"]:
        hasc  = feature["properties"].get("HASC_1") or ""     # guard against JSON null
        abbr  = hasc.replace("-", ".").split(".")[-1].upper()  # "CH.ZH" → "ZH"
        region = LANGUAGE_REGIONS.get(abbr, "Unknown")
        feature["properties"]["language_region"] = region

    PROCESSED_GEOJSON.write_text(json.dumps(geojson), encoding="utf-8")
    print(f"  → saved {PROCESSED_GEOJSON.name}")


# ─────────────────────────────────────────────────────────────────────────────
# 3.  PyQGIS: symbology + project
# ─────────────────────────────────────────────────────────────────────────────

def apply_symbology(layer) -> None:
    """Assign a distinct fill colour to each language region."""
    categories = []
    for region, color in REGION_COLORS.items():
        symbol = QgsFillSymbol.createSimple({
            "color":         color,
            "outline_color": "#FFFFFF",
            "outline_width": "0.5",
        })
        label = REGION_LABELS.get(region, region)
        categories.append(QgsRendererCategory(region, symbol, label))

    layer.setRenderer(
        QgsCategorizedSymbolRenderer("language_region", categories)
    )


def build_project() -> None:
    """Load the processed layer, style it, and write a QGIS project file."""
    layer = QgsVectorLayer(
        str(PROCESSED_GEOJSON),
        "Swiss Cantons – Language Regions",
        "ogr",
    )
    if not layer.isValid():
        raise RuntimeError(f"Layer could not be loaded: {PROCESSED_GEOJSON}")
    print(f"Layer loaded: {layer.featureCount()} features, CRS {layer.crs().authid()}")

    apply_symbology(layer)
    print("Symbology applied.")

    project = QgsProject.instance()
    project.addMapLayer(layer)
    project.setTitle("Swiss Cantons – Language Regions")
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    project.viewSettings().setDefaultViewExtent(
        QgsReferencedRectangle(layer.extent(), layer.crs())
    )

    if project.write(str(PROJECT_FILE)):
        print(f"\nProject saved: {PROJECT_FILE}")
        print("→ Open this file in QGIS Desktop to explore the styled map.")
    else:
        print("ERROR: project could not be saved.")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Build a styled QGIS project file for the Swiss cantons language region map."""
    # Step 1 – data preparation (no QGIS engine needed)
    download_boundaries()
    add_language_region_field()

    # Step 2 – QGIS initialisation
    # setPrefixPath must be called as a static method BEFORE instantiation
    QgsApplication.setPrefixPath(QGIS_PREFIX, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    print("QGIS initialised.")

    try:
        build_project()
    finally:
        qgs.exitQgis()
        print("QGIS shut down.")


if __name__ == "__main__":
    main()
