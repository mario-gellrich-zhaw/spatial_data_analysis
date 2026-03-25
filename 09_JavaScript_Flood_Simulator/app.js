/* ============================================================
   Swiss Flood Simulator
    Elevation data: AWS Terrain Tiles (free, CORS-enabled)
   Encoding: elevation = (R * 256 + G + B/256) - 32768  [metres]
   ============================================================ */

'use strict';

// ── City definitions (CH municipalities > 30 000 inhabitants) ─
// baseElevation = river / lake surface [m a.s.l.]
const CITIES = {
    bern:            { name: 'Bern',              river: 'Aare',                    center: [46.9480,  7.4474], zoom: 13, baseElevation: 511 },
    zuerich:         { name: 'Zürich',             river: 'Zürichsee / Limmat',      center: [47.3769,  8.5417], zoom: 13, baseElevation: 406 },
    genf:            { name: 'Genf',               river: 'Rhône / Lac Léman',       center: [46.2044,  6.1432], zoom: 13, baseElevation: 372 },
    basel:           { name: 'Basel',              river: 'Rhein',                   center: [47.5596,  7.5886], zoom: 13, baseElevation: 245 },
    lausanne:        { name: 'Lausanne',           river: 'Lac Léman',               center: [46.5197,  6.6323], zoom: 13, baseElevation: 372 },
    winterthur:      { name: 'Winterthur',         river: 'Eulach / Töss',           center: [47.5006,  8.7239], zoom: 13, baseElevation: 430 },
    luzern:          { name: 'Luzern',             river: 'Vierwaldstättersee',      center: [47.0502,  8.3093], zoom: 13, baseElevation: 434 },
    stgallen:        { name: 'St. Gallen',         river: 'Steinach / Sitter',       center: [47.4245,  9.3767], zoom: 13, baseElevation: 670 },
    lugano:          { name: 'Lugano',             river: 'Lago di Lugano',          center: [46.0037,  8.9511], zoom: 13, baseElevation: 271 },
    biel:            { name: 'Biel/Bienne',        river: 'Bielersee / Aare',        center: [47.1368,  7.2467], zoom: 13, baseElevation: 429 },
    thun:            { name: 'Thun',               river: 'Thunersee / Aare',        center: [46.7577,  7.6286], zoom: 13, baseElevation: 558 },
    koeniz:          { name: 'Köniz',              river: 'Schwarzenbach / Aare',    center: [46.9240,  7.4079], zoom: 13, baseElevation: 550 },
    lachauxdefonds:  { name: 'La Chaux-de-Fonds', river: 'La Suze',                 center: [47.1001,  6.8275], zoom: 13, baseElevation: 992 },
    fribourg:        { name: 'Fribourg',           river: 'Saane / Sarine',          center: [46.8065,  7.1620], zoom: 13, baseElevation: 630 },
    schaffhausen:    { name: 'Schaffhausen',       river: 'Rhein',                   center: [47.6965,  8.6343], zoom: 13, baseElevation: 390 },
    chur:            { name: 'Chur',               river: 'Rhein / Plessur',         center: [46.8499,  9.5329], zoom: 13, baseElevation: 585 },
    vernier:         { name: 'Vernier',            river: 'Rhône',                   center: [46.2168,  6.0850], zoom: 13, baseElevation: 375 },
    uster:           { name: 'Uster',              river: 'Greifensee',              center: [47.3480,  8.7191], zoom: 13, baseElevation: 435 },
    sion:            { name: 'Sion/Sitten',        river: 'Rhône',                   center: [46.2330,  7.3601], zoom: 13, baseElevation: 490 },
    emmen:           { name: 'Emmen',              river: 'Reuss / Kleine Emme',     center: [47.0736,  8.2972], zoom: 13, baseElevation: 440 },
    lancy:           { name: 'Lancy',              river: 'Rhône / Arve',            center: [46.1896,  6.1188], zoom: 13, baseElevation: 378 },
    zug:             { name: 'Zug',                river: 'Zugersee',                center: [47.1724,  8.5170], zoom: 13, baseElevation: 415 },
    kriens:          { name: 'Kriens',             river: 'Reuss / Krienbach',       center: [47.0355,  8.2887], zoom: 13, baseElevation: 440 },
    rapperswiljona:  { name: 'Rapperswil-Jona',   river: 'Zürichsee',               center: [47.2269,  8.8188], zoom: 13, baseElevation: 406 },
    meyrin:          { name: 'Meyrin',             river: 'Rhône',                   center: [46.2138,  6.0789], zoom: 13, baseElevation: 375 },
};

// Max flood rise on slider [m]
const MAX_FLOOD_M = 25;

// Terrain tile source (Terrarium format, CORS enabled)
const TERRARIUM_URL = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png';
const MAX_TERRAIN_ZOOM = 14;   // terrarium tiles exist up to z=15; cap at 14

// ── State ─────────────────────────────────────────────────────
let currentCity = CITIES.bern;
let floodRiseM  = 0;            // metres above base
let animating   = false;
let animFrame   = null;
let floodLayer  = null;
let pendingTiles = 0;

// ── DOM refs ──────────────────────────────────────────────────
const slider        = document.getElementById('flood-slider');
const floodValueEl  = document.getElementById('flood-value');
const refElevEl     = document.getElementById('ref-elevation');
const curElevEl     = document.getElementById('current-elevation');
const riverNameEl   = document.getElementById('river-name');
const animBtn       = document.getElementById('animate-btn');
const resetBtn      = document.getElementById('reset-btn');
const loadingEl     = document.getElementById('loading-overlay');
const zoomWarnEl    = document.getElementById('zoom-warning');

// ── Map initialisation ────────────────────────────────────────
const map = L.map('map', {
    center: currentCity.center,
    zoom:   currentCity.zoom,
    maxZoom: 16,
    minZoom: 10,
    zoomControl: true
});

// ESRI World Imagery (aerial photo background)
L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {
        attribution: 'Luftbild &copy; <a href="https://www.esri.com/">Esri</a>, Earthstar Geographics &mdash; ' +
                     'Höhendaten: <a href="https://registry.opendata.aws/terrain-tiles/">AWS Terrain Tiles</a>',
        maxZoom: 19
    }
).addTo(map);

// ── Flood GridLayer ───────────────────────────────────────────
/*
 * Each tile:
 *   1. Loads corresponding Terrarium elevation tile
 *   2. Decodes RGB → elevation (Float32Array, cached)
 *   3. Renders flooded pixels in depth-dependent blue
 *   4. Renders "at-risk" zone (within 0.5 m above flood line) in amber
 *
 * On flood level change: redraw all visible tiles from cache (no refetch).
 */
const FloodLayer = L.GridLayer.extend({
    options: {
        opacity:    0.9,
        tileSize:   256,
        zIndex:     400,
        pane:       'overlayPane'
    },

    initialize(options) {
        L.GridLayer.prototype.initialize.call(this, options);
        this._elevCache = {};   // key: "z/x/y" → Float32Array(256*256)
    },

    // ── createTile called by Leaflet for each visible tile ────
    createTile(coords, done) {
        const canvas = document.createElement('canvas');
        canvas.width  = 256;
        canvas.height = 256;

        // Clamp terrain zoom: use lower-res tile when zoomed in beyond MAX_TERRAIN_ZOOM
        const tz = Math.min(coords.z, MAX_TERRAIN_ZOOM);
        const scale = Math.pow(2, coords.z - tz);  // > 1 when zoomed beyond max
        const tx = Math.floor(coords.x / scale);
        const ty = Math.floor(coords.y / scale);

        // Pixel offset within the lower-res tile (for sub-tile crop)
        const subSize  = Math.floor(256 / scale);
        const subOffX  = (coords.x % scale) * subSize;
        const subOffY  = (coords.y % scale) * subSize;

        const key = `${tz}/${tx}/${ty}`;

        const render = (elevations) => {
            this._renderTile(canvas, elevations, subOffX, subOffY, subSize);
            done(null, canvas);
        };

        if (this._elevCache[key]) {
            render(this._elevCache[key]);
            return canvas;
        }

        setPending(+1);
        const img = new Image();
        img.crossOrigin = 'anonymous';

        img.onload = () => {
            try {
                const off  = document.createElement('canvas');
                off.width  = 256;
                off.height = 256;
                const ctx  = off.getContext('2d');
                ctx.drawImage(img, 0, 0);
                const data = ctx.getImageData(0, 0, 256, 256).data;

                const elevs = new Float32Array(256 * 256);
                for (let i = 0; i < 256 * 256; i++) {
                    const r = data[i * 4];
                    const g = data[i * 4 + 1];
                    const b = data[i * 4 + 2];
                    elevs[i] = (r * 256 + g + b / 256) - 32768;
                }
                this._elevCache[key] = elevs;
                render(elevs);
            } catch (e) {
                // CORS or taint error — render empty tile silently
                done(null, canvas);
            }
            setPending(-1);
        };

        img.onerror = () => {
            setPending(-1);
            done(null, canvas);
        };

        img.src = TERRARIUM_URL
            .replace('{z}', tz)
            .replace('{x}', tx)
            .replace('{y}', ty);

        return canvas;
    },

    // ── Pixel rendering ───────────────────────────────────────
    _renderTile(canvas, elevs, subOffX, subOffY, subSize) {
        const ctx    = canvas.getContext('2d');
        const imgOut = ctx.createImageData(256, 256);
        const d      = imgOut.data;

        const floodLine = currentCity.baseElevation + floodRiseM;
        const riskLine  = floodLine + 0.5;

        for (let py = 0; py < 256; py++) {
            for (let px = 0; px < 256; px++) {
                // Map this output pixel back to source elevation pixel
                const srcX = subOffX + Math.floor(px / 256 * subSize);
                const srcY = subOffY + Math.floor(py / 256 * subSize);
                const elev = elevs[srcY * 256 + srcX];

                if (elev < -500) continue; // no-data (ocean / void)

                const i = (py * 256 + px) * 4;

                if (floodRiseM > 0 && elev <= floodLine) {
                    // Flood depth → colour intensity
                    const depth  = floodLine - elev;
                    const t      = Math.min(depth / 10, 1); // 0..1 over 10 m depth

                    d[i]     = Math.round(64  - t * 49);  // R: 64 → 15
                    d[i + 1] = Math.round(164 - t * 84);  // G: 164 → 80
                    d[i + 2] = Math.round(223 - t * 63);  // B: 223 → 160
                    d[i + 3] = Math.round(120 + t * 115); // A: 120 → 235

                } else if (elev <= riskLine && floodRiseM > 0) {
                    // "At risk" zone — amber
                    const t = (riskLine - elev) / 0.5;   // 0..1 within risk band
                    d[i]     = 255;
                    d[i + 1] = Math.round(200 - t * 35);
                    d[i + 2] = 50;
                    d[i + 3] = Math.round(100 + t * 100);
                }
            }
        }

        ctx.putImageData(imgOut, 0, 0);
    },

    // ── Redraw all cached tiles without network fetch ─────────
    redrawAll() {
        const tiles = this._tiles;
        if (!tiles) return;

        Object.values(tiles).forEach(tile => {
            const c = tile.coords;
            const tz    = Math.min(c.z, MAX_TERRAIN_ZOOM);
            const scale = Math.pow(2, c.z - tz);
            const tx    = Math.floor(c.x / scale);
            const ty    = Math.floor(c.y / scale);
            const key   = `${tz}/${tx}/${ty}`;
            const elevs = this._elevCache[key];
            if (!elevs) return;

            const subSize = Math.floor(256 / scale);
            const subOffX = (c.x % scale) * subSize;
            const subOffY = (c.y % scale) * subSize;
            this._renderTile(tile.el, elevs, subOffX, subOffY, subSize);
        });
    }
});

// ── Loading counter ───────────────────────────────────────────
function setPending(delta) {
    pendingTiles = Math.max(0, pendingTiles + delta);
    loadingEl.classList.toggle('visible', pendingTiles > 0);
}

// ── Initialise flood layer ────────────────────────────────────
floodLayer = new FloodLayer();
floodLayer.addTo(map);

// ── UI helpers ────────────────────────────────────────────────
function updateElevationDisplay() {
    const current = currentCity.baseElevation + floodRiseM;
    floodValueEl.textContent = `+${floodRiseM.toFixed(1)} m`;
    refElevEl.textContent    = currentCity.baseElevation;
    curElevEl.textContent    = current.toFixed(1);
    riverNameEl.textContent  = currentCity.river;

    // Update slider gradient
    const pct = (floodRiseM / MAX_FLOOD_M) * 100;
    slider.style.setProperty('--progress', pct + '%');
}

function setFloodLevel(metres) {
    floodRiseM = Math.max(0, Math.min(MAX_FLOOD_M, metres));
    slider.value = Math.round(floodRiseM / MAX_FLOOD_M * 2000);
    updateElevationDisplay();
    floodLayer.redrawAll();
}

function switchCity(cityKey) {
    currentCity = CITIES[cityKey];

    document.getElementById('city-select').value = cityKey;

    stopAnimation();
    setFloodLevel(0);

    map.flyTo(currentCity.center, currentCity.zoom, { duration: 1.2 });
    updateElevationDisplay();
}

// ── Zoom-level guard ──────────────────────────────────────────
map.on('zoomend', () => {
    const z = map.getZoom();
    zoomWarnEl.classList.toggle('visible', z > MAX_TERRAIN_ZOOM);
    floodLayer.redrawAll();
});

// ── Animation ────────────────────────────────────────────────
const ANIM_DURATION_S = 25;   // seconds to rise from 0 to MAX_FLOOD_M
let animStart = null;

function animStep(ts) {
    if (!animating) return;
    if (!animStart) animStart = ts;
    const elapsed = (ts - animStart) / 1000;
    const level   = Math.min((elapsed / ANIM_DURATION_S) * MAX_FLOOD_M, MAX_FLOOD_M);
    setFloodLevel(level);
    if (level < MAX_FLOOD_M) {
        animFrame = requestAnimationFrame(animStep);
    } else {
        stopAnimation();
    }
}

function startAnimation() {
    animating  = true;
    animStart  = null;
    animBtn.textContent = '⏹ Stoppen';
    animBtn.classList.add('running');
    animFrame = requestAnimationFrame(animStep);
}

function stopAnimation() {
    animating = false;
    cancelAnimationFrame(animFrame);
    animBtn.textContent = '▶ Animieren';
    animBtn.classList.remove('running');
}

// ── Event listeners ───────────────────────────────────────────
slider.addEventListener('input', () => {
    stopAnimation();
    const metres = (slider.value / 2000) * MAX_FLOOD_M;
    setFloodLevel(metres);
});

animBtn.addEventListener('click', () => {
    if (animating) {
        stopAnimation();
    } else {
        if (floodRiseM >= MAX_FLOOD_M) setFloodLevel(0);
        startAnimation();
    }
});

resetBtn.addEventListener('click', () => {
    stopAnimation();
    setFloodLevel(0);
});

document.getElementById('city-select').addEventListener('change', e => {
    switchCity(e.target.value);
});

// ── Initial display ───────────────────────────────────────────
updateElevationDisplay();
