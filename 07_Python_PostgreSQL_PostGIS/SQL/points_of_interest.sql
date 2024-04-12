-- Hotels
WITH zurich_boundary AS (
    SELECT way
    FROM planet_osm_polygon
    WHERE boundary = 'administrative'
    AND admin_level = '8'
    AND name = 'Zürich'
)
SELECT
    h.name AS hotel_name,
    h."addr:housenumber" AS house_number,
    h."addr:street" AS street,
    h."addr:postcode" AS postcode,
    h."addr:city" AS city,
    h."addr:country" AS country,
    ST_Transform(h.way, 4326) AS hotel_location
FROM planet_osm_point h
WHERE h.tourism = 'hotel'
AND ST_Within(ST_Transform(h.way, 4326), (SELECT ST_Transform(way, 4326) FROM zurich_boundary));


-- Points-of-Interest
WITH zurich_boundary AS (
    SELECT way
    FROM planet_osm_polygon
    WHERE boundary = 'administrative'
    AND admin_level = '8'
    AND name = 'Zürich'
)
SELECT
    poi.name AS poi_name,
    poi."addr:housenumber" AS house_number,
    poi."addr:street" AS street,
    poi."addr:postcode" AS postcode,
    poi."addr:city" AS city,
    ST_Transform(poi.way, 4326) AS poi_location
FROM planet_osm_point poi
WHERE poi.amenity IN ('bar', 
					  'restaurant', 
					  'cafe', 
					  'pub', 
					  'cinema', 
					  'theatre')
AND ST_Within(ST_Transform(poi.way, 4326), (SELECT ST_Transform(way, 4326) FROM zurich_boundary));


-- Points-of-Interest in Buffer-Distance around hotels
WITH zurich_boundary AS (
  SELECT way
  FROM planet_osm_polygon
  WHERE boundary = 'administrative'
  AND admin_level = '8'
  AND name = 'Zürich'
),
hotels AS (
  SELECT
    name AS hotel_name,
    way AS hotel_geom,
	ST_TRANSFORM(way, 4326) AS hotel_geom_st
  FROM planet_osm_point
  WHERE tourism = 'hotel'
  AND ST_Within(way, (SELECT way FROM zurich_boundary))
),
buffered_hotels AS (
  SELECT 
    hotel_name,
    hotel_geom,
    ST_Buffer(hotel_geom, 250) AS hotel_buffer
  FROM hotels
)
SELECT DISTINCT
  bh.hotel_name,
  poi.amenity,
  poi.name AS poi_name
FROM planet_osm_point poi
JOIN buffered_hotels bh ON ST_Within(poi.way, bh.hotel_buffer)
WHERE poi.amenity IS NOT NULL 
AND poi.amenity IN ('bar', 
                    'restaurant', 
                    'cafe', 
                    'pub', 
                    'cinema', 
                    'theatre')


-- Count POI per hotel
WITH zurich_boundary AS (
  SELECT way
  FROM planet_osm_polygon
  WHERE boundary = 'administrative'
  AND admin_level = '8'
  AND name = 'Zürich'
),
hotels AS (
  SELECT
    name AS hotel_name,
    way AS hotel_geom,
	ST_TRANSFORM(way, 4326) AS hotel_geom_st
  FROM planet_osm_point
  WHERE tourism = 'hotel'
  AND ST_Within(way, (SELECT way FROM zurich_boundary))
),
buffered_hotels AS (
  SELECT 
    hotel_name,
    hotel_geom,
    ST_Buffer(hotel_geom, 250) AS hotel_buffer
  FROM hotels
)
SELECT DISTINCT
  bh.hotel_name,
  COUNT(poi.name) AS poi_count
FROM planet_osm_point poi
JOIN buffered_hotels bh ON ST_Within(poi.way, bh.hotel_buffer)
WHERE poi.amenity IS NOT NULL 
AND poi.amenity IN ('bar', 
                    'restaurant', 
                    'cafe', 
                    'pub', 
                    'cinema', 
                    'theatre')
GROUP BY bh.hotel_name
ORDER BY poi_count DESC;



