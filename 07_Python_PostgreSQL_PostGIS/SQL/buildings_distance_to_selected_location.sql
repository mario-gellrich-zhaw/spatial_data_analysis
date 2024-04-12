SELECT 
  p.osm_id,
  p."addr:street",
  p."addr:housenumber",
  p."addr:city",
  p."addr:postcode",
  p.building,
  ST_Transform(p.way, 4326) AS way_transformed,
  ST_Distance(
    ST_Transform(p.way, 4326)::geography,
	-- Zürich, Grossmünster
    ST_SetSRID(ST_MakePoint(8.54394, 47.37011), 4326)::geography
  ) AS distance
FROM 
  public.planet_osm_polygon AS p
WHERE 
  p."addr:street" IS NOT NULL
  AND p."addr:city" = 'Zürich'
  AND p."addr:postcode" IN ('8055')
