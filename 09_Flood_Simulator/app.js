const swissCities = [
  {
    name: 'Zürich',
    center: [47.3769, 8.5417],
    zoom: 12,
    referenceWaterLevel: 406,
    seedPoints: [
      [47.3665, 8.5481],
      [47.3738, 8.541],
      [47.348, 8.529],
      [47.3125, 8.5965],
    ],
  },
  {
    name: 'Genf',
    center: [46.2044, 6.1432],
    zoom: 12,
    referenceWaterLevel: 372,
    seedPoints: [
      [46.2103, 6.1427],
      [46.222, 6.158],
      [46.1975, 6.1295],
      [46.204, 6.114],
    ],
  },
  {
    name: 'Basel',
    center: [47.5596, 7.5886],
    zoom: 12,
    referenceWaterLevel: 247,
    seedPoints: [
      [47.561, 7.592],
      [47.558, 7.61],
      [47.566, 7.58],
      [47.57, 7.6],
    ],
  },
  {
    name: 'Bern',
    center: [46.9481, 7.4474],
    zoom: 12,
    referenceWaterLevel: 505,
    seedPoints: [
      [46.947, 7.455],
      [46.952, 7.442],
      [46.944, 7.465],
      [46.957, 7.46],
    ],
  },
  {
    name: 'Lausanne',
    center: [46.5197, 6.6323],
    zoom: 12,
    referenceWaterLevel: 372,
    seedPoints: [
      [46.509, 6.624],
      [46.514, 6.637],
      [46.503, 6.61],
      [46.52, 6.65],
    ],
  },
];

function terrariumToElevation(r, g, b) {
  return r * 256 + g + b / 256 - 32768;
}

function latLngToTileXY(lat, lng, zoom) {
  const latRad = (lat * Math.PI) / 180;
  const scale = 2 ** zoom;
  const x = ((lng + 180) / 360) * scale;
  const y =
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) *
    scale;
  return { x, y };
}

const map = L.map('map', {
  center: swissCities[0].center,
  zoom: swissCities[0].zoom,
  minZoom: 7,
  maxZoom: 16,
});

L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {
    attribution: 'Tiles © Esri',
    maxZoom: 18,
  }
).addTo(map);

const FloodLayer = L.GridLayer.extend({
  initialize(options = {}) {
    L.setOptions(this, options);
    this.waterLevel = options.waterLevel || 0;
    this.seedPoints = options.seedPoints || [];
  },

  setWaterLevel(level) {
    this.waterLevel = level;
    this.redraw();
  },

  setSeedPoints(seedPoints) {
    this.seedPoints = seedPoints || [];
    this.redraw();
  },

  getSeedPixelsForTile(coords, tileWidth, tileHeight) {
    const pixels = [];

    for (const [lat, lng] of this.seedPoints) {
      const tilePos = latLngToTileXY(lat, lng, coords.z);
      const tileX = Math.floor(tilePos.x);
      const tileY = Math.floor(tilePos.y);

      if (tileX === coords.x && tileY === coords.y) {
        const pixelX = Math.floor((tilePos.x - tileX) * tileWidth);
        const pixelY = Math.floor((tilePos.y - tileY) * tileHeight);
        if (
          pixelX >= 0 &&
          pixelX < tileWidth &&
          pixelY >= 0 &&
          pixelY < tileHeight
        ) {
          pixels.push([pixelX, pixelY]);
        }
      }
    }

    return pixels;
  },

  floodFillConnected(tileWidth, tileHeight, elevations, seedPixels) {
    const pixelCount = tileWidth * tileHeight;
    const flooded = new Uint8Array(pixelCount);
    const queue = [];
    let queueIndex = 0;

    for (const [x, y] of seedPixels) {
      const index = y * tileWidth + x;
      if (elevations[index] <= this.waterLevel && flooded[index] === 0) {
        flooded[index] = 1;
        queue.push(index);
      }
    }

    while (queueIndex < queue.length) {
      const currentIndex = queue[queueIndex++];
      const x = currentIndex % tileWidth;
      const y = Math.floor(currentIndex / tileWidth);

      const neighbors = [];
      if (x > 0) neighbors.push(currentIndex - 1);
      if (x < tileWidth - 1) neighbors.push(currentIndex + 1);
      if (y > 0) neighbors.push(currentIndex - tileWidth);
      if (y < tileHeight - 1) neighbors.push(currentIndex + tileWidth);

      for (const neighborIndex of neighbors) {
        if (
          flooded[neighborIndex] === 0 &&
          elevations[neighborIndex] <= this.waterLevel
        ) {
          flooded[neighborIndex] = 1;
          queue.push(neighborIndex);
        }
      }
    }

    return flooded;
  },

  createTile(coords, done) {
    const tile = document.createElement('canvas');
    const size = this.getTileSize();
    tile.width = size.x;
    tile.height = size.y;

    const ctx = tile.getContext('2d', { willReadFrequently: true });
    const image = new Image();
    image.crossOrigin = 'anonymous';

    const url = `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${coords.z}/${coords.x}/${coords.y}.png`;

    image.onload = () => {
      ctx.drawImage(image, 0, 0);
      const imageData = ctx.getImageData(0, 0, tile.width, tile.height);
      const pixels = imageData.data;
      const tilePixelCount = tile.width * tile.height;
      const elevations = new Float32Array(tilePixelCount);

      for (let pixelIndex = 0; pixelIndex < tilePixelCount; pixelIndex += 1) {
        const dataIndex = pixelIndex * 4;
        elevations[pixelIndex] = terrariumToElevation(
          pixels[dataIndex],
          pixels[dataIndex + 1],
          pixels[dataIndex + 2]
        );
      }

      const seedPixels = this.getSeedPixelsForTile(coords, tile.width, tile.height);
      const flooded = this.floodFillConnected(
        tile.width,
        tile.height,
        elevations,
        seedPixels
      );

      for (let pixelIndex = 0; pixelIndex < tilePixelCount; pixelIndex += 1) {
        const dataIndex = pixelIndex * 4;
        if (flooded[pixelIndex] === 1) {
          pixels[dataIndex] = 0;
          pixels[dataIndex + 1] = 114;
          pixels[dataIndex + 2] = 255;
          pixels[dataIndex + 3] = 145;
        } else {
          pixels[dataIndex + 3] = 0;
        }
      }

      ctx.putImageData(imageData, 0, 0);
      done(null, tile);
    };

    image.onerror = () => {
      done(null, tile);
    };

    image.src = url;
    return tile;
  },
});

const citySelect = document.getElementById('citySelect');
const waterRise = document.getElementById('waterRise');
const waterLevelInfo = document.getElementById('waterLevelInfo');

swissCities.forEach((city, index) => {
  const option = document.createElement('option');
  option.value = String(index);
  option.textContent = city.name;
  citySelect.appendChild(option);
});

let selectedCity = swissCities[0];
let currentWaterRise = Number(waterRise.value);

const floodLayer = new FloodLayer({
  tileSize: 256,
  opacity: 1,
  waterLevel: selectedCity.referenceWaterLevel + currentWaterRise,
  seedPoints: selectedCity.seedPoints,
});

floodLayer.addTo(map);

function updateSimulation() {
  const absoluteWaterLevel = selectedCity.referenceWaterLevel + currentWaterRise;
  floodLayer.setWaterLevel(absoluteWaterLevel);
  floodLayer.setSeedPoints(selectedCity.seedPoints);

  waterLevelInfo.textContent = `Wasserstand: ${absoluteWaterLevel.toFixed(
    1
  )} m ü. M. (Referenz ${selectedCity.referenceWaterLevel.toFixed(
    1
  )} m +${currentWaterRise.toFixed(1)} m)`;
}

citySelect.addEventListener('change', (event) => {
  selectedCity = swissCities[Number(event.target.value)];
  map.setView(selectedCity.center, selectedCity.zoom);
  updateSimulation();
});

waterRise.addEventListener('input', (event) => {
  currentWaterRise = Number(event.target.value);
  updateSimulation();
});

updateSimulation();
