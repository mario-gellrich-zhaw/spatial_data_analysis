-- Canton of Zurich
SELECT 
    osm_id,
    name,
    ST_Area(ST_Transform(way, 32632)) / 1000000 AS area_km2,
	ST_Transform(way, 4326) AS geom
FROM planet_osm_polygon
WHERE 
    boundary = 'administrative' 
    AND admin_level = '4'
    AND name IN ('Zürich');

-- All municipalities in the Canton of Zurich
SELECT 
    osm_id,
    name,
    ST_Area(ST_Transform(way, 32632)) / 1000000 AS area_km2,
    ST_Transform(way, 4326) AS geom
FROM planet_osm_polygon AS municipalities
WHERE 
    municipalities.boundary = 'administrative' 
    AND municipalities.admin_level = '8'
    AND ST_Contains(
        (SELECT way FROM planet_osm_polygon WHERE name = 'Zürich' AND boundary = 'administrative' AND admin_level = '4'),
        municipalities.way
    );