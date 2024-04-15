-- This SQL-script uses hotel data (vector data) and traffic noise data (raster data) for spatial intersection

-- Prerequisites
planet_osm_point table available in PostgreSQL
public.strassenlaerm_tag available in PostgreSQL

-- To import table 'public.strassenlaerm_tag' to PostgreSQL:
Download the raster "StrassenLaerm_Tag.tif" from GeoAdmin
Create a smaller subset of this raster (QGIS: 'clip raster by extent') 
Make a reprojection of the raster to EPSG:3857 (QGIS: Warp (reproject))
Import the raster to PostgreSQL using 'raster2pgsql' (part of the QGIS installation), e.g.:

raster2pgsql -I -C -M U:\Lektionen\WPM\spatial_data_analysis\07_Python_PostgreSQL_PostGIS\postgis_raster\st_laerm_clipped.tif -F -t auto public.strassenlaerm_tag | psql -d osm_switzerland -U postgres


-- Verify the Spatial Reference System (SRS) of your raster data
SELECT
ST_SRID(rast) 
FROM public.strassenlaerm_tag LIMIT 1;


-- Query hotels in the city of Zurich
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
AND h."addr:city" = 'Zürich';


-- Intersect hotels with raster data
SELECT
    h.name AS hotel_name,
    h."addr:housenumber" AS house_number,
    h."addr:street" AS street,
    h."addr:postcode" AS postcode,
    h."addr:city" AS city,
    h."addr:country" AS country,
	ST_Value(r.rast, h.way) AS street_noise_db,
    ST_TRANSFORM(h.way, 4326) AS hotel_location
FROM
    planet_osm_point h
JOIN
    public.strassenlaerm_tag r
ON
    ST_Intersects(r.rast, h.way)
WHERE
    h.tourism = 'hotel'
AND h."addr:city" = 'Zürich';


-- Summarize raster values at hotel locations
SELECT
    MIN(street_noise_db) AS min_noise_db,
    MAX(street_noise_db) AS max_noise_db,
    AVG(street_noise_db) AS avg_noise_db,
    STDDEV(street_noise_db) AS stddev_noise_db,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY street_noise_db) AS Q25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY street_noise_db) AS Q50,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY street_noise_db) AS Q75
FROM (
    SELECT
        ST_Value(r.rast, h.way) AS street_noise_db
    FROM
        planet_osm_point h
    JOIN
        public.strassenlaerm_tag r
    ON
        ST_Intersects(r.rast, h.way)
    WHERE
        h.tourism = 'hotel'
    AND h."addr:city" = 'Zürich'
) AS noise_data;



