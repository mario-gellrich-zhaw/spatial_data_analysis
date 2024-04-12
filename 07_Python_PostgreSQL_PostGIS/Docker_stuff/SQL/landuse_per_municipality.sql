-- landuse Tags for green spaces
landuse=forest 			- Areas with forestry or woodland vegetation.
landuse=grass 			- Areas covered in grass.
landuse=greenfield 		- Undeveloped land reserved for urban development.
landuse=garden 			- Private or community gardens.
landuse=meadow 			- Fields or meadows, often used for agriculture or left to nature.
landuse=orchard 		- Areas planted with fruit trees.
landuse=vineyard 		- Areas used for growing grapes.
landuse=cemetery 		- Land designated for burial.
landuse=recreation_ground 	- Open spaces for general recreation.
landuse=village_green 	  	- Common in British English for open space at a village’s heart.
landuse=allotments 		- Areas of land rented for growing food plants.
landuse=conservation 		- Land primarily used for conservation purposes.
landuse=greenhouse_horticulture - Areas with greenhouses for growing plants.

-- leisure Tags for parks and recreational areas
leisure=park 		- Urban or suburban areas dedicated to recreation, often green.
leisure=garden 		- Managed areas of planted flowers, trees, etc., possibly with paths and seating.
leisure=golf_course 	- Areas used for playing golf.
leisure=nature_reserve 	- Protected areas for conservation and limited recreation.
leisure=playground 	- Outdoor areas designed for children to play.
leisure=pitch 		- Areas for playing team sports.
leisure=green 		- Used for village greens and similar.
leisure=sports_centre 	- Large areas that include facilities for various sports, often including green spaces.

-- Query landuse and calculate area
SELECT
    p.osm_id,
    COALESCE(p.landuse, p.leisure) AS landuse_leisure,
    ST_Area(ST_Transform(p.way, 32632)) AS area_sqm,
    ST_Transform(p.way, 4326) AS way_wgs84
FROM
    public.planet_osm_polygon AS p
JOIN
    public.planet_osm_polygon AS z ON ST_Contains(z.way, p.way)
WHERE
    (p.landuse IN ('forest',
		  'grass',
		  'greenfield',
		  'garden',
		  'meadow',
		  'orchard',
		  'vineyard',
		  'cemetery',
		  'recreation_ground',
		  'village_green',
		  'allotments',
		  'conservation',
		  'greenhouse_horticulture')
    OR p.leisure IN ('park',
		      'garden',
		      'golf_course',
		      'nature_reserve',
		      'playground',
		      'pitch',
		      'green',
		      'sports_centre'))
    AND z.admin_level = '8'
    AND z.name = 'Zürich';

-- Aggregate area by landuse type
SELECT
    COALESCE(p.landuse, p.leisure) AS landuse_leisure,
    SUM(ST_Area(ST_Transform(p.way, 32632))) AS total_area_sqm
FROM
    public.planet_osm_polygon AS p
JOIN
    public.planet_osm_polygon AS z ON ST_Contains(z.way, p.way)
WHERE
    (p.landuse IN ('forest',
		  'grass',
		  'greenfield',
		  'garden',
		  'meadow',
		  'orchard',
		  'vineyard',
		  'cemetery',
		  'recreation_ground',
		  'village_green',
		  'allotments',
		  'conservation',
		  'greenhouse_horticulture')
    OR p.leisure IN ('park',
		      'garden',
		      'golf_course',
		      'nature_reserve',
		      'playground',
		      'pitch',
		      'green',
		      'sports_centre'))    
AND z.admin_level = '8'
AND z.name = 'Zürich'
GROUP BY landuse_leisure
ORDER BY total_area_sqm DESC;