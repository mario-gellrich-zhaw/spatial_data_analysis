SELECT
    p.osm_id,
    p."addr:street",
    p."addr:housenumber",
    p."addr:city",
    p."addr:postcode",
    p.shop,
    UPPER(p.name),
    ST_TRANSFORM(p.way, 4326)
FROM
    public.planet_osm_point AS p
WHERE 
    p.shop = 'supermarket'
    AND (UPPER(p.name) LIKE '%NETTO%' OR UPPER(p.name) LIKE '%EDEKA%')
    AND p."addr:street" IS NOT NULL
    AND p."addr:housenumber" IS NOT NULL
    AND p."addr:city" IS NOT NULL
    AND p."addr:postcode" IS NOT NULL;
