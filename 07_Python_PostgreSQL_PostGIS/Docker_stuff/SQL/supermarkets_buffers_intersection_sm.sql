WITH BufferedSupermarkets AS (
    SELECT
        p.osm_id,
        p."addr:street",
        p."addr:housenumber",
        p."addr:city",
        p."addr:postcode",
        p.shop,
        UPPER(p.name) AS brand,
        ST_TRANSFORM(p.way, 4326) AS geom,
        ST_TRANSFORM(ST_Buffer(p.way::geometry, 1000, 'quad_segs=8'), 4326) AS buffer_geom
    FROM
        public.planet_osm_point AS p
    WHERE
        p.shop = 'supermarket'
        AND p."addr:street" IS NOT NULL
        AND p."addr:housenumber" IS NOT NULL
        AND p."addr:city" IS NOT NULL
        AND p."addr:postcode" IS NOT NULL
)

SELECT
    a.osm_id AS osm_id_1,
    b.osm_id AS osm_id_2,
    a.brand AS brand_1,
    b.brand AS brand_2,
    ST_INTERSECTION(a.buffer_geom, b.buffer_geom) AS intersection_geom
FROM
    BufferedSupermarkets a
    INNER JOIN BufferedSupermarkets b ON a.osm_id < b.osm_id
        AND ST_INTERSECTS(a.buffer_geom, b.buffer_geom);
