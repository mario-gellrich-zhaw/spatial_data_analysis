# 08 · Swiss Flood Simulator

A client-side web application that simulates rising water levels over Swiss cities
using a freely available digital elevation model (DEM). Move a slider (or press
**▶ Animieren**) and see which areas along the river or lake would be flooded.

No backend, no build step and no API key required — just static HTML, CSS and JavaScript.

---

## What is in this folder

| File | Purpose |
| --- | --- |
| `index.html` | Page layout: map, city selector, slider, buttons, legend. |
| `app.js` | Map setup, elevation tile decoding, flood rendering, animation. |
| `style.css` | Styling of the app. |
| `README.md` | This file. |

---

## Running the app

**Requirements:** a web browser, internet access and any local web server
(Python is already available in the devcontainer).

```bash
cd /workspaces/spatial_data_analysis/08_JS_Flood_Simulator

# Start
python -m http.server 8080

# Stop: Ctrl+C in the terminal, or from another terminal:
pkill -f "http.server 8080"
```

Then open **http://localhost:8080** in your browser.

- **VS Code devcontainer:** port 8080 is forwarded automatically — click
  *Open in Browser* in the notification or use the **Ports** tab.
- **GitHub Codespaces:** go to the **Ports** tab → port **8080** → click the globe icon.

Alternative with Node.js: `npx serve .`

> **Do not open `index.html` directly via `file://`.** The app reads the pixel
> values of the elevation tiles on a canvas, which browsers may block for pages
> loaded from the local file system. Always use a web server.

---

## Using the app

1. The app starts with a view of **Zürich**. **Select another city** in the
   dropdown (top right). The map flies to the city and
   the reference level of its river or lake is shown below the slider.
2. **Move the slider** to raise the water level from 0 to 25 m above the
   reference level. The current absolute level (m a.s.l.) is displayed.
3. Press **▶ Animieren** to let the water rise automatically from 0 to 25 m
   (≈ 25 s). Press again to stop, **↻ Reset** returns to 0 m.
4. Pan and zoom freely. Above zoom level 13 the elevation tiles are upscaled;
   above zoom level 14 a warning appears.

### Legend

| Colour | Meaning |
| --- | --- |
| Amber | At risk — terrain less than 0.5 m above the current water level |
| Light blue | Flooded, shallow |
| Dark blue | Flooded, deep (colour saturates at 10 m water depth) |

### Cities

25 Swiss municipalities with more than ~26 000 inhabitants: Bern, Zürich, Genf,
Basel, Lausanne, Winterthur, Luzern, St. Gallen, Lugano, Biel/Bienne, Thun, Köniz,
La Chaux-de-Fonds, Fribourg, Schaffhausen, Chur, Vernier, Uster, Sion/Sitten,
Emmen, Lancy, Zug, Kriens, Rapperswil-Jona and Meyrin.

The reference levels (`baseElevation`) and map centres are defined in the
`CITIES` object at the top of `app.js` — add new cities there and in the
`<select>` in `index.html`.

---

## How it works

### Data sources

| Layer | Source |
| --- | --- |
| Background | [Esri World Imagery](https://www.esri.com/) (aerial photos) |
| Elevation | [AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/), Terrarium format, ~10 m resolution in Switzerland |
| Map library | [Leaflet 1.9.4](https://leafletjs.com/) (loaded from unpkg CDN) |

### Elevation decoding

Each Terrarium tile is a PNG image that encodes the height in its RGB values:

```
elevation [m] = (R × 256 + G + B / 256) − 32768
```

### Flood rendering

A custom Leaflet `GridLayer` (`FloodLayer` in `app.js`) does the following for
every visible map tile:

1. Loads the matching Terrarium tile with CORS enabled. Elevation tiles are
   fetched at max. zoom 13 (z14 adds almost no detail but 4× the requests);
   when zoomed in further, one elevation tile is shared by several map tiles
   and fetched only once. No tiles are loaded for intermediate zoom levels
   while the map is flying to another city.
   Because the S3 bucket only supports HTTP/1.1 (max. 6 parallel downloads per
   hostname), the tiles are spread over 4 hostnames of the same bucket, and
   downloads for tiles that were panned out of view are cancelled.
2. Draws it on an off-screen canvas and decodes all 256 × 256 pixels into a
   `Float32Array` of elevations, which is cached per tile.
3. Compares each pixel with the flood line
   `baseElevation + floodRise`:
   - `elevation ≤ flood line` → blue, darker with increasing depth
   - `elevation ≤ flood line + 0.5 m` → amber risk zone
4. When the slider moves, all visible tiles are re-coloured from the cache —
   no tiles are fetched again, so the update is instant.

---

## Limitations

This is a **teaching tool**, not a hydrological model:

- It is a simple "bathtub" model: every pixel below the water level is shown as
  flooded, even if it is not hydraulically connected to the river or lake
  (e.g. depressions behind a hill).
- Flow dynamics, discharge, dams, levees and drainage are not considered.
- The DEM (~10 m) is a surface model of limited accuracy; buildings, bridges
  and small embankments are not resolved properly.
- The reference levels per city are approximate mean water levels.

For official flood hazard information in Switzerland see the hazard maps on
[map.geo.admin.ch](https://map.geo.admin.ch).
