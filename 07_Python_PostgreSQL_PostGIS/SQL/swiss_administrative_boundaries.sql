SELECT 
    osm_id,
    name,
    ST_Area(ST_Transform(way, 32632)) / 1000000 AS area_km2,
	ST_Transform(way, 4326) AS geom
FROM planet_osm_polygon
WHERE 
    boundary = 'administrative' 
    AND admin_level = '8'
    -- AND name IN ('Zürich');
