SELECT
    osm_id,
    name,
    boundary,
    admin_level,
    ST_Transform(way, 4326) AS geometry
FROM
    planet_osm_polygon
WHERE
    boundary = 'administrative'
    AND admin_level = '4';