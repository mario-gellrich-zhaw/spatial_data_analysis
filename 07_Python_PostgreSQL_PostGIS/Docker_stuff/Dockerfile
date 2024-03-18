FROM postgis/postgis

RUN apt-get update && apt-get install -y wget osm2pgsql

COPY default.style /usr/bin/

RUN wget -O /tmp/switzerland-latest.osm.pbf http://download.geofabrik.de/europe/switzerland-latest.osm.pbf
