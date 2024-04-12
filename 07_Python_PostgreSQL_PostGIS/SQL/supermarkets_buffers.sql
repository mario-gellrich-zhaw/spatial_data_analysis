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
