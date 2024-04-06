-- The following SQL script is used to create a road network topology and calculate the shortest path between two nodes using pgRouting.

-- Prerequisites: 
    -- PostgreSQL with extensions PostGIS, pgRouting
    -- OSM data loaded into the database
    -- OSM data is loaded into the table public.planet_osm_roads
    -- The table public.planet_osm_roads contains at least the following columns: osm_id, highway, way

-- Adding source and target columns to public.planet_osm_roads
ALTER TABLE public.planet_osm_roads ADD COLUMN source INTEGER;
ALTER TABLE public.planet_osm_roads ADD COLUMN target INTEGER;

-- Creating a topology for the road network
SELECT pgr_createTopology(
    'public.planet_osm_roads', -- Road network table
     0.0001,                   -- Tolerance: determines how close two line endpoints must be to be considered the same node
    'way',                     -- The geometry column in your road network table
    'osm_id',                  -- The unique identifier column of your road network table
    'source',                  -- The column that will be created/updated to store the source node of each line
    'target',                  -- The column that will be created/updated to store the target node of each line
    rows_where:='true',        -- Optional: condition to select a subset of rows. Default is 'true', meaning all rows
    clean:='true'              -- Optional: cleans the topology by removing isolated nodes and edges
);

-- Check new topology table which includes of the road network
SELECT * FROM public.planet_osm_roads_vertices_pgr;

-- Adding and calculating the length of each road segment
ALTER TABLE public.planet_osm_roads ADD COLUMN length FLOAT8;
UPDATE public.planet_osm_roads
SET length = ST_Length(ST_Transform(way, 4326)::geography);

-- Take a look at the updated public.planet_osm_roads table
SELECT 
osm_id,
highway,
source,
target,
length
FROM public.planet_osm_roads
WHERE highway IN ('motorway');

-- Calculate shortest path between specified source_node and target_node
DROP TABLE IF EXISTS route;
CREATE TABLE route AS
SELECT 
    seq,
    route.node,
    route.edge, 
    route.cost,
    route.agg_cost,
    planet_osm_roads.osm_id,
    planet_osm_roads.source,
    planet_osm_roads.target,
    ST_Transform(planet_osm_roads.way, 4326)::geometry AS geom
FROM pgr_dijkstra(
    'SELECT osm_id AS id, source, target, length AS cost FROM planet_osm_roads',
    403, -- Source node ID 
    141938, -- Target node ID
    FALSE
) AS route
JOIN public.planet_osm_roads ON route.edge = public.planet_osm_roads.osm_id;

-- Query table route
SELECT * FROM route;

-- Extract all the nodes that have length less than or equal to the <<value distance>>
DROP TABLE IF EXISTS driving_distance;
CREATE TABLE driving_distance AS
SELECT dd.*,
       ST_Y(ST_Transform(pt.the_geom, 4326)) AS lat,
       ST_X(ST_Transform(pt.the_geom, 4326)) AS lon,
       ST_Transform(pt.the_geom, 4326) AS geom
FROM pgr_drivingDistance(
    'SELECT 
         osm_id AS id, 
         source, target, 
         length AS cost 
     FROM public.planet_osm_roads',
    403, 25000, true -- source_node and value distance (in meters)
) AS dd
JOIN public.planet_osm_roads_vertices_pgr AS pt
ON dd.node = pt.id;

-- Query table driving_distance
SELECT * FROM public.driving_distance
