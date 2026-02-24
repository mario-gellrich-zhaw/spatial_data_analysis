# 08 · QGIS Python – Swiss Cantons Language Region Map

Uses **PyQGIS** (Python API of QGIS) to build a styled QGIS project file
showing all 26 Swiss cantons coloured by official language region.

The script runs headless (no QGIS Desktop needed to execute it).
The resulting `.qgz` project file is opened in **QGIS Desktop** to view and
interact with the map.

---

## Language Regions

| Region | Colour | Cantons |
|--------|--------|---------|
| German | blue | ZH, LU, UR, SZ, OW, NW, GL, ZG, SO, BS, BL, SH, AR, AI, SG, AG, TG |
| French (Romandy) | red | VD, NE, GE, JU |
| Italian (Ticino) | green | TI |
| Bilingual DE/FR | purple | BE, FR, VS |
| Trilingual DE/RM/IT | amber | GR |

*Source: [Swiss Federal Chancellery](https://www.bk.admin.ch/bk/en/home/documentation/languages.html)*

---

## Prerequisites

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda
- [QGIS Desktop](https://qgis.org) (to open the generated project file)
- Internet access on first run (~3 MB canton boundary download)

---

## Setup

```bash
# 1. Create and activate the conda environment
conda env create -f environment.yml
conda activate qgisenv

# 2. Run the script
python swiss_cantons_language_map.py

# 3. Open the generated project in QGIS Desktop
#    File → Open Project → swiss_cantons_language_regions.qgz
```

---

## What the Script Does

| Step | Code / API | Description |
|------|-----------|-------------|
| 1 | `requests` | Download canton boundaries from GADM 4.1 (cached) |
| 2 | `json` | Inject `language_region` field into every GeoJSON feature |
| 3 | `QgsApplication` | Initialise QGIS engine in headless mode |
| 4 | `QgsVectorLayer` | Load processed GeoJSON |
| 5 | `QgsCategorizedSymbolRenderer` | Colour each canton by language region |
| 6 | `QgsProject.write()` | Save styled project as `.qgz` |

---

## Generated Files

```
08_QGIS_Python/
├── environment.yml                    # conda environment  (qgisenv)
├── swiss_cantons_language_map.py      # PyQGIS script
├── swiss_cantons_gadm.geojson         # raw download      (created on first run)
├── swiss_cantons_processed.geojson    # with language_region field
└── swiss_cantons_language_regions.qgz # QGIS project file (open in QGIS Desktop)
```

---

## Key PyQGIS Classes Used

| Class | Purpose |
|-------|---------|
| `QgsApplication` | QGIS engine entry point; must be created before any other class |
| `QgsVectorLayer` | Loads a vector dataset (GeoJSON, GeoPackage, Shapefile, …) |
| `QgsCategorizedSymbolRenderer` | Symbolises features by unique attribute value |
| `QgsFillSymbol` | Polygon fill with colour + outline |
| `QgsRendererCategory` | One symbol → one category value |
| `QgsProject` | Manages layers, CRS, title; serialises to `.qgs` / `.qgz` |

---

## Data Source

| Dataset | Provider | Licence |
|---------|----------|---------|
| Swiss cantonal boundaries | [GADM 4.1](https://gadm.org) | Free for non-commercial use |
| Language region classification | [Swiss Federal Chancellery](https://www.bk.admin.ch) | Public domain |
