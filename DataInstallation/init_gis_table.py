import psycopg2
import json
import networkx as nx

def connect_to_psql(dbname='gis', user='zhou', password='', hostaddr='', port='5432', remote=False):
    try:
        if remote:  
            conn =  psycopg2.connect("dbname=%s user=%s hostaddress=%s port=%s password=%s"%(dbname, user, hostaddr, port, password))
        else:
            conn = psycopg2.connect("dbname=%s user=%s"%(dbname, user))
    except:
        print 'Fail to connect to Postgres Server'
    return conn

def init_transformer(conn, reg_osm_id): 
    """Transformer data only from OpenStreetMap"""
    cur = conn.cursor()
    # Select all locations within GARCHING and its power='transformer'
    cur.execute("INSERT INTO transformer(osm_id, power, way) SELECT t1.osm_id, t1.power, t1.way FROM planet_osm_point AS t1 , "
                "(SELECT way FROM planet_osm_polygon WHERE osm_id = %d) AS t2 "
                "WHERE t1.power = 'transformer' and ST_Within(t1.way, t2.way);"%reg_osm_id)
    conn.commit()
    cur.close()


def init_apprx_road(conn, reg_osm_id, road_type=['residential']):
    road_type = str(road_type).replace("[", "(").replace("]",")")
    cur = conn.cursor()
    # Select roads within GARCHING and store its start and end point
    cur.execute("INSERT INTO apprx_road(osm_id, start_way, end_way) "
                "SELECT t2.osm_id, ST_StartPoint(t2.way), ST_EndPoint(t2.way) "
                "FROM (SELECT way FROM planet_osm_polygon WHERE osm_id = %d) AS t1, "
                "(SELECT osm_id, way FROM planet_osm_line WHERE highway in %s) AS t2 "
                "WHERE ST_Within(t2.way, t1.way) = true;"
                %(reg_osm_id, road_type))
    conn.commit()
    cur.close()


def init_node(conn, reg_osm_id, road_type, radius):
    road_type = str(road_type).replace("[", "(").replace("]",")")    
    cur = conn.cursor()
    # Create intermediate table to store houses projected to nearest roads of specified types and within a specific radius
    cur.execute("CREATE TABLE IF NOT EXISTS temp_road_house (hid  bigint, hway geometry(Point,900913), rway geometry(LineString,900913), distance float);")
    
    # clean entries
    cur.execute("DELETE FROM temphsrd;")
    
    cur.execute("INSERT INTO temp_road_house "
                "(SELECT t1.osm_id, t1.ct_way, t2.way, " 
                "ST_Distance(ST_Transform(t1.ct_way,26986), ST_Transform(t2.way,26986)) "
                "FROM "
                "(SELECT osm_id, ST_Centroid(way) AS ct_way FROM planet_osm_polygon "
                "WHERE ST_Within(way,(SELECT way FROM planet_osm_polygon WHERE osm_id = %d)) "
                "AND building != '') AS t1 "
                "LEFT JOIN "
                "(SELECT way FROM planet_osm_line WHERE highway in %s"
                "AND ST_DWithin(way,(SELECT way FROM planet_osm_polygon WHERE osm_id = %d), 1) = true) AS t2 "            
                "ON ST_DWithin(t1.ct_way, t2.way, %d) = true);"
                %(reg_osm_id, road_type, reg_osm_id, radius))

    # Store house nodes, selecting the projected house with the shortest distance to original location
    cur.execute("INSERT INTO node(osm_id, node_type,  max_capacity, max_load, way, origin_house_way) "
                "(SELECT hid, \'house\', 0, 0, ST_ClosestPoint(rway, hway), hway "
                "FROM temp_road_house "
                "WHERE (hway, distance) IN "
                "(SELECT hway, MIN(distance) FROM temp_road_house "
                "GROUP BY hway));")
    
    # Drop temporary table
    cur.execute("DROP TABLE temp_road_house;")
    
    # Store transformer nodes without projection onto road
    cur.execute("INSERT INTO node(osm_id, node_type,  max_capacity, max_load, way) "
                "(SELECT transformer_id, \'transformer\', 0, 0, way "
                "FROM student_transformers);")

    # Store road start nodes
    cur.execute("INSERT INTO node(osm_id, node_type,  max_capacity, max_load, way) "
                "(SELECT osm_id, \'road_start\', 0, 0, start_way FROM apprx_road);")

    # Store road end nodes
    cur.execute("INSERT INTO node(osm_id, node_type,  max_capacity, max_load, way) "
                "(SELECT osm_id, \'road_end\', 0, 0, end_way FROM apprx_road);")
    conn.commit() 
    cur.close()


    
# Initial database
GARCHING = -30971
road_type=['motorway', 'trunk', 'primary', 'secondary', 'unclassified',
           'tertiary', 'residential', 'service', 'motorway_link', 
           'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link', 
           'living_street', 'pedestrian', 'road', 'footway']
conn = connect_to_psql(dbname='gis', user='zhou')
# init_transformer(conn, reg_osm_id=GARCHING) 
init_apprx_road(conn, reg_osm_id=GARCHING, road_type=road_type)
init_node(conn, reg_osm_id=GARCHING, road_type=road_type, radius=60)
conn.close()


