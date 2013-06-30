The sample data was generated from an osmosis snapshot database
containing Utah data downloaded from Geofabrik on 6/30/13.

The query used was 

    COPY (SELECT id, st_astext(geom), tags->'name' FROM nodes WHERE tags->'amenity' IN ('restaurant', 'bar', 'cafe') AND tags?'name' AND NOT (tags?'website' OR tags?'url')) TO '/osm/out/sampledata.csv' CSV;
