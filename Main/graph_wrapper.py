import psycopg2
import json
import shapely.geometry as geo
from geopy.distance import vincenty
from itertools import tee
import networkx as nx
import re

def connect_to_psql(dbname='gis', user='zhou', password='', hostaddr='', port='5432', remote=False):
    try:
        if remote:
            token = "dbname=%s user=%s host=%s port=%s password=%s"%(dbname, user, hostaddr, port, password)
            conn =  psycopg2.connect(token)
        else:
            conn = psycopg2.connect("dbname=%s user=%s"%(dbname, user))
        print('Connection established. DNS info: %s' % conn.dsn)
    except:
        print('Fail to connect to Postgres Server')
    return conn

def get_area(conn, reg_osm_id):
    cur=conn.cursor()
    cur.execute("SELECT ST_AsGeoJSON(ST_FlipCoordinates(ST_Transform(ST_Centroid(way), 4326))), "
                "ST_AsGeoJSON(ST_FlipCoordinates(ST_Transform(way, 4326))) "
                "FROM planet_osm_polygon WHERE osm_id = %d; "%reg_osm_id)
    data = cur.fetchall()
    cur.close()

    centJson = json.loads(data[0][0])
    polyJson = json.loads(data[0][1])
    return centJson['coordinates'], polyJson['coordinates']

# Currently using data in student transformers 
def get_transformers(conn): 
    cur=conn.cursor()
    cur.execute("SELECT ST_AsGeoJSON(ST_Collect(ST_FlipCoordinates(ST_Transform(way, 4326)))) FROM student_transformers;")
    #cur.execute("SELECT ST_AsGeoJSON(ST_Collect(ST_FlipCoordinates(ST_Transform(way, 4326)))) FROM transformer;")
    transformers = cur.fetchall()
    cur.close()
    return json.loads(transformers[0][0])['coordinates']

def get_roads(conn, reg_osm_id, road_types):
    # Select roads within specified area using osm data
    cur = conn.cursor()

    if not road_types:
        cur.execute("SELECT ST_AsGeoJSON(ST_Collect((ST_FlipCoordinates(ST_Transform(way, 4326))))) FROM planet_osm_line "
                    "WHERE ST_Within(way,(SELECT way FROM planet_osm_polygon WHERE osm_id = %d )) = true "
                    "AND highway != '';"%(reg_osm_id))
    else:
        road_types = str(road_types).replace("[", "(").replace("]",")")
        cur.execute("SELECT ST_AsGeoJSON(ST_Collect((ST_FlipCoordinates(ST_Transform(way, 4326))))) FROM planet_osm_line "
                    "WHERE ST_Within(way,(SELECT way FROM planet_osm_polygon WHERE osm_id = %d )) = true "
                    "AND highway IN %s;"%(reg_osm_id, road_types))        

    roads = cur.fetchall()
    cur.close()
    if roads[0][0] is None:
        return None
    return json.loads(roads[0][0])['coordinates']


def get_apprx_roads(conn):
    # Select approximated roads with only start and end point
    cur=conn.cursor()
    cur.execute("SELECT DISTINCT ST_AsGeoJSON(ST_FlipCoordinates(ST_Transform(way, 4326))) "
                "FROM node WHERE node_type IN ('road_start', 'road_end');")
    rdNodes = cur.fetchall()
    cur.close()
    return [json.loads(nd[0])['coordinates'] for nd in rdNodes]

def get_proj_houses(conn):
    # Select houses and its projection to the nearest roads
    cur=conn.cursor()
    cur.execute("SELECT DISTINCT ST_AsGeoJSON(ST_FlipCoordinates(ST_Transform(way, 4326))), "
                "ST_AsGeoJSON(ST_FlipCoordinates(ST_Transform(origin_house_way, 4326))) "
                "FROM node WHERE node_type IN ('house');")
    hsPairs = cur.fetchall()
    cur.close()
    return [(json.loads(pr[0])['coordinates'], json.loads(pr[1])['coordinates'] ) for pr in hsPairs]

def get_edge_data(conn):
    cur = conn.cursor()
    cur.execute("SELECT t1.id, t2.id, "
                "ST_Distance(ST_Transform(t1.way,26986), ST_Transform(t2.way,26986)) "
                "FROM (SELECT id, way FROM node) AS t1, "
                "(SELECT id, way FROM node ) AS t2 "
                "WHERE t1.id != t2.id;")
    edgeData = cur.fetchall()
    cur.close()
    return edgeData


def split_by_difference(lines):
    # Split given lines by intersection between every pair
    total = len(lines)
    split_lines = []
    split_lines_coords = []

    for i in range(total):
        l1 = geo.LineString(lines[i])
        #print list(l1.coords)
        crossed = []
        for j in range(total):
            if i == j:
                continue
            l2 = geo.LineString(lines[j])
            if l1.crosses(l2):
                crossed.append(l2)
        if not crossed:
            # l1 has no intersection with other roads
            split_lines.append(l1)
            split_lines_coords.append(list(l1.coords))
        else:
            # Split l2 by its intersection with l1
            for l2 in crossed:
                split = l1.difference(l2)
                if split.geom_type == "MultiLineString":
                    for line in split.geoms:
                        split_lines.append(line)
                        split_lines_coords.append(list(line.coords))
                elif split.geom_type == "LineString":
                    split_lines.append(split)
                    split_lines_coords.append(list(split.coords))
    return split_lines_coords

def store_split_roads(conn, split_roads_coords):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS split_roads (way geometry(LineString, 4326));")
    cur.execute("DELETE FROM split_roads;")
    for road in split_roads_coords:
        lineStr = re.sub('\d{1},\s{1}', ' ', str(road))
        lineStr = re.sub("(\[|\(|\)|\])", "", lineStr)
        cur.execute("INSERT INTO split_roads VALUES(ST_GeomFromText('LINESTRING(%s)',4326));"%lineStr)
    conn.commit()
    cur.close()

def fetch_split_roads(conn):
    cur = conn.cursor()
    cur.execute("SELECT ST_AsGeoJSON(ST_Collect(way)) FROM split_roads;")
    roads = cur.fetchall()
    cur.close()
    return json.loads(roads[0][0])['coordinates']
    

def generate_connected_subgraph(roads):
    # Generate subgraphs by connecting along roads
    graph = nx.Graph()
    for road in roads:
        sid, eid = tee(road) # Initial index of edge start and end node
        next(eid) # Move end node next to start
        for n1, n2 in zip(sid, eid):
            graph.add_edge(tuple(n1), tuple(n2))        
    subgraph = list(nx.connected_component_subgraphs(graph))[0]
    
    # Assign edge length
    for e1, e2 in subgraph.edges_iter():
        subgraph[e1][e2]["length"] = vincenty(e1, e2).kilometers  
    return subgraph

def find_shortest_path(source, target, subgraph):
    nearest_source = nearest_target = [None, None]
    min_dist_src = min_dist_tar = [float("inf"), float("inf")]

    for node in subgraph.nodes():
        dist_src = vincenty(source, node).kilometers
        dist_tar = vincenty(target, node).kilometers
        if dist_src < min_dist_src:
            nearest_source = node
            min_dist_src = dist_src
        if dist_tar < min_dist_tar:
            nearest_target = node
            min_dist_tar = dist_tar
    path = nx.shortest_path(subgraph, source = nearest_source, target = nearest_target, weight = "length")

    # Calculate total length
    total_len = 0
    sid, eid = tee(path) # Initial index of edge start and end node
    next(eid) # Move end node next to start
    for n1, n2 in zip(sid, eid):
        total_len += subgraph[n1][n2]['length']
    return path, total_len, subgraph

def merge_roads(roads, meters):
    merged_roads = []

    for road in roads:
        merged_roads.append(road)

    for i in merged_roads:
        for j in merged_roads:
            if i == j:
                continue
            if vincenty(i[-1], j[0]).kilometers != 0.0 and vincenty(i[-1], j[0]).kilometers <= meters/1000:
                j[0] = i[-1]
    return merged_roads
