-- Create supermarket buffers (1000 m) for all supermarkets in selected postcode areas
WITH supermarket_buffers AS (
    SELECT
        p.osm_id AS supermarket_osm_id,
        ST_TRANSFORM(ST_Buffer(p.way::geometry, 1000, 'quad_segs=8'), 4326) AS buffer_geom
    FROM
        public.planet_osm_point AS p
    WHERE
        p.shop = 'supermarket'
        AND p."addr:postcode" IN ('8001', '8055')
),
-- Preselection of buildings (to reduce data size)
buildings AS (
    SELECT
        p.osm_id AS building_osm_id,
        p."addr:street",
        p."addr:housenumber",
        p."addr:city",
        p."addr:postcode",
        ST_TRANSFORM(p.way, 4326) AS geom
    FROM
        public.planet_osm_polygon AS p
    WHERE
        p."addr:street" IS NOT NULL
        AND p."addr:city" = 'Zürich'
)
-- Select buildings inside supermarket buffers
SELECT
    b.building_osm_id,
    b."addr:street",
    b."addr:housenumber",
    b."addr:city",
    b."addr:postcode",
    b.geom AS building_geom,
    s.supermarket_osm_id,
    s.buffer_geom AS buffer_geom
FROM
    buildings AS b
JOIN
    supermarket_buffers AS s ON ST_Intersects(b.geom, s.buffer_geom::geometry);
