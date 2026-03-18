# 08 · QGIS Python – Swiss Cantons Language Region Map

Uses **PyQGIS** (Python API of QGIS) to build a styled QGIS project file
showing all 26 Swiss cantons coloured by official language region.

The script runs **headless** (no QGIS Desktop needed to execute it).
Open the resulting `.qgz` file in QGIS Desktop to view and interact with the map.

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

## Setup

QGIS Python bindings cannot be installed via `pip`. The setup differs by platform.

### Linux / GitHub Codespace (Debian/Ubuntu)

Install the QGIS bindings from `apt`, then create a virtual environment that
inherits them via `--system-site-packages`:

```bash
# 1. Install QGIS Python bindings and venv support
sudo apt-get install -y python3-qgis python3-venv

# 2. Create a virtual environment (from the repo root)
python3 -m venv .venv --system-site-packages

# 3. Activate it
source .venv/bin/activate

# 4. Run the script
cd 08_Python_QGIS
python swiss_cantons_language_map.py
```

> **VSCode users:** after creating the venv, open the Command Palette →
> **Python: Select Interpreter** and choose `.venv`. The workspace already has
> `"python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"` set,
> so "Run Python File in Terminal" will use the correct interpreter automatically.

### macOS / Windows

Requires [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda.

```bash
# 1. Create and activate the conda environment (installs QGIS + Python)
conda env create -f 08_Python_QGIS/environment.yml
conda activate qgisenv

# 2. Run the script
cd 08_Python_QGIS
python swiss_cantons_language_map.py
```

> **Note:** on first run the script downloads ~3 MB of canton boundary data
> from GADM. The file is cached locally and reused on subsequent runs.

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
08_Python_QGIS/
├── environment.yml                    # conda environment  (macOS / Windows)
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

## Data Sources

| Dataset | Provider | Licence |
|---------|----------|---------|
| Swiss cantonal boundaries | [GADM 4.1](https://gadm.org) | Free for non-commercial use |
| Language region classification | [Swiss Federal Chancellery](https://www.bk.admin.ch) | Public domain |
