SELECT ROUND(
    CAST(ST_Distance(
        -- Berlin (longitude, latitude)
        ST_GeographyFromText('SRID=4326;POINT(13.4050 52.5200)'),
        -- München (longitude, latitude)
        ST_GeographyFromText('SRID=4326;POINT(11.5819 48.1351)')
    ) / 1000 AS NUMERIC), -- Convert meters to kilometers
    1 -- Round to two decimal places
) AS distance_in_kilometers;