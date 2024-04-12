-- The following SQL script is used to create a road network topology and calculate the shortest paths between nodes using pgRouting.

-- Prerequisites: 
    -- PostgreSQL with extensions PostGIS and pgRouting
    -- OSM data loaded into the database
    -- table planet_osm_line with the road network is available

-- Infos:
    -- pgRouting: https://pgrouting.org
    -- pgRouting Workshop: https://workshop.pgrouting.org
    -- Dijkstra's Algorithm: https://www.youtube.com/watch?v=bZkzH5x0SKU

-- Creating a subset of roads in the city of Zuerich
DROP TABLE IF EXISTS roads_zuerich;
CREATE TABLE roads_zuerich AS 
SELECT *
FROM 
    public.planet_osm_line
WHERE 
    highway IN ('motorway', 'trunk', 'primary', 'secondary', 
                'tertiary', 'unclassified', 'residential',
                'service')
    AND ST_Within(
        ST_TRANSFORM(way, 4326), 
        (SELECT geom 
         FROM public.municipalities_ch
         WHERE bfs_nummer = 261)
    );

-- Querying roads
SELECT 
    osm_id,
    highway,
    ST_TRANSFORM(way, 4326) AS way_transformed
FROM 
    public.roads_zuerich;

-- Counting distinct road types
SELECT 
    highway,
    COUNT(*) AS highway_num
FROM 
    public.roads_zuerich
GROUP BY 
    highway
ORDER BY 
    highway_num DESC;

-- Adding source and target columns to public.planet_osm_roads
ALTER TABLE public.roads_zuerich ADD COLUMN source INTEGER;
ALTER TABLE public.roads_zuerich ADD COLUMN target INTEGER;

-- Creating a topology for the road network
SELECT pgr_createTopology(
    'public.roads_zuerich',    -- Road network table
     0.0001,                   -- Tolerance: determines how close two line endpoints must be to be considered the same node
    'way',                     -- The geometry column in your road network table
    'osm_id',                  -- The unique identifier column of your road network table
    'source',                  -- The column that will be created/updated to store the source node of each line
    'target',                  -- The column that will be created/updated to store the target node of each line
    rows_where:='true',        -- Optional: condition to select a subset of rows. Default is 'true', meaning all rows
    clean:='true'              -- Optional: cleans the topology by removing isolated nodes and edges
);

-- Checking topology table which includes the road network
SELECT
id,
ST_TRANSFORM(the_geom, 4326) as geom
FROM public.roads_zuerich_vertices_pgr;

-- Adding the length of road segments
ALTER TABLE public.roads_zuerich ADD COLUMN length FLOAT8;
UPDATE public.roads_zuerich
SET length = ST_Length(ST_Transform(way, 4326)::geography);

-- Calculating length per road category
SELECT 
    highway,
    SUM(length) AS total_length
FROM 
    public.roads_zuerich
GROUP BY 
    highway
ORDER BY 
    total_length DESC;


-- Conducting connectivity analysis
CREATE TEMP TABLE temp_components AS
SELECT * FROM pgr_connectedComponents(
    'SELECT osm_id AS id, source, target, length AS cost FROM roads_zuerich'
);

ALTER TABLE roads_zuerich ADD COLUMN component INTEGER;

UPDATE roads_zuerich r
SET component = (
    SELECT component
    FROM temp_components
    WHERE r.source = node
    LIMIT 1
);

-- Querying roads (consider connecting components)
SELECT 
    osm_id,
    highway,
    source,
    target,
    length,
    component,
    ST_TRANSFORM(way, 4326) AS way_transformed
FROM 
    public.roads_zuerich;


-- Counting distinct connected elements
SELECT 
    component,
    COUNT(*) AS num_roads
FROM 
    public.roads_zuerich
GROUP BY 
    component
ORDER BY 
    num_roads DESC;

-- Selecting connected roads
SELECT
osm_id,
highway,
source,
target,
length,
component,
ST_TRANSFORM(way, 4326)
FROM public.roads_zuerich
WHERE component = 3
ORDER BY length DESC;


-- Calculating the shortest path between single source_node and target_node
DROP TABLE IF EXISTS route;
CREATE TABLE route AS
SELECT 
    seq,
    route.node,
    route.edge, 
    route.cost,
    route.agg_cost,
    public.roads_zuerich.osm_id,
    public.roads_zuerich.source,
    public.roads_zuerich.target,
    ST_Transform(roads_zuerich.way, 4326)::geometry AS geom
FROM pgr_dijkstra(
    'SELECT osm_id AS id, source, target, length AS cost FROM roads_zuerich',
    3170, -- Source node ID 
    14040, -- Target node ID
    FALSE
) AS route
JOIN public.roads_zuerich ON route.edge = public.roads_zuerich.osm_id;

SELECT * FROM route;

-- Calculating the shortest path between single source_node and multiple target_nodes
DROP TABLE IF EXISTS one_to_many;
CREATE TABLE one_to_many AS
SELECT dijkstra.*, 
       ST_TRANSFORM(roads.way, 4326)
FROM pgr_bdDijkstra(
    'SELECT osm_id AS id, source, target, length AS cost FROM roads_zuerich',
    386, -- Source node ID 
    ARRAY[14426, 16746], -- Array of target node IDs
    FALSE
) AS dijkstra
JOIN public.roads_zuerich AS roads ON dijkstra.edge = roads.osm_id;

SELECT * FROM one_to_many;


-- Extracting all the nodes that have length less than or equal to distance
DROP TABLE IF EXISTS driving_distance;
CREATE TABLE driving_distance AS
SELECT dd.*,
       ST_Y(ST_Transform(pt.the_geom, 4326)) AS lat,
       ST_X(ST_Transform(pt.the_geom, 4326)) AS lon,
       ST_Transform(pt.the_geom, 4326) AS geom
FROM pgr_drivingDistance(
    'SELECT 
         osm_id AS id, 
         source, 
         target, 
         length AS cost 
     FROM  public.roads_zuerich',
    6359, 5000, true -- source_node and distance in meters
) AS dd
JOIN  public.roads_zuerich_vertices_pgr AS pt
ON dd.node = pt.id;

SELECT * FROM public.driving_distance;


-- Calculate k-shortest path (multiple alternative paths)
SELECT
    ksp.seq,
    ksp.path_id,
    ksp.path_seq,
    ksp.start_vid AS start_node,
    ksp.end_vid AS end_node,
    ksp.node,
    ksp.edge,
    ksp.cost,
    ksp.agg_cost,
    ST_Transform(roads.way, 4326) AS geom
FROM pgr_ksp(
    'SELECT osm_id AS id, source, target, length AS cost FROM public.roads_zuerich',
    18388, -- source node ID 
    8649, -- target node ID
    4,  -- k (number of shortest paths to find)
    false -- directed graph (true for directed, false for undirected)
) AS ksp
JOIN public.planet_osm_roads AS roads ON ksp.edge = roads.osm_id;


-- Aggregate agg_costs of k-shortest path (multiple alternative paths)
WITH KShortestPaths AS (
    SELECT
        ksp.seq,
        ksp.path_id,
        ksp.path_seq,
        ksp.start_vid AS start_node,
        ksp.end_vid AS end_node,
        ksp.node,
        ksp.edge,
        ksp.cost,
        ksp.agg_cost,
        ST_Transform(roads.way, 4326) AS geom
    FROM pgr_ksp(
        'SELECT osm_id AS id, source, target, length AS cost FROM public.roads_zuerich',
        16022, -- source node ID 
        2481, -- target node ID
        4,  -- k (number of shortest paths to find)
        false -- directed graph (true for directed, false for undirected)
    ) AS ksp
    JOIN public.roads_zuerich AS roads ON ksp.edge = roads.osm_id
)
SELECT
    path_id,
    ROUND(MAX(agg_cost)::numeric, 2) AS max_agg_cost 
FROM KShortestPaths
GROUP BY path_id
ORDER BY path_id;



