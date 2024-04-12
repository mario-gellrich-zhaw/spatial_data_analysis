-- Create buffers around major roads
SELECT 
osm_id,
ST_TRANSFORM(ST_Buffer(p.way::geometry, 1000), 4326) AS buffer_geom
FROM public.planet_osm_roads AS p
WHERE
-- highway IN ('motorway', 'trunk', 'primary')
highway IN ('motorway');

-- Create buffers around major roads and combine these buffers to one single buffer
SELECT 
1 as group_id,
ST_TRANSFORM(ST_UNION(ST_Buffer(p.way::geometry, 1000)), 4326) AS combined_buffer_geom
FROM public.planet_osm_roads AS p
WHERE
--highway IN ('motorway', 'trunk', 'primary')
highway IN ('motorway');