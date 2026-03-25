# 09 Flood Simulator

Einfache 2D-Web-App zur Simulation potenzieller Hochwassergefährdungsflächen in 5 Schweizer Städten.

## Eigenschaften

- Hintergrundkarte: **ESRI World Imagery**
- Frei verfügbares Höhenmodell: **Terrarium Elevation Tiles** (Mapzen/AWS)
- Stadtwahl: Zürich, Genf, Basel, Bern, Lausanne
- Steuerung über Slider für Wasseranstieg in Metern

## Modellannahme

Die Darstellung verwendet eine **vereinfachte Badewannenlogik**:

- Ein Pixel wird als potenziell überflutet dargestellt, wenn seine Geländehöhe unterhalb des gewählten Wasserstands liegt.
- Es wird **keine** hydrodynamische Fließsimulation (Abfluss, Dämme, Kanalnetz, Zeitverlauf) durchgeführt.

## Lokal starten

Aus dem Ordner `09_Flood_Simulator` z. B. mit Python:

```bash
python3 -m http.server 8080
```

Dann im Browser öffnen:

- `http://localhost:8080`

## Quellen

- ESRI World Imagery Tile Service
- Elevation Tiles: `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
