--
-- Create transformer table, resources are directly from osm
--
CREATE TABLE transformer (
	id bigint NOT NULL,
	osm_id bigint NOT NULL,
	power text,
	way geometry(Point,900913)
);

CREATE SEQUENCE transformer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE transformer_id_seq OWNED BY transformer.id;
ALTER TABLE ONLY transformer ALTER COLUMN id SET DEFAULT nextval('transformer_id_seq'::regclass);


--
-- Create appr_road table, a road is approximated by its starting point and end point
--

CREATE TABLE apprx_road (
	id bigint NOT NULL,
	osm_id bigint NOT NULL,
	start_way geometry(Point,900913),
	end_way geometry(Point,900913)
);

CREATE SEQUENCE apprx_road_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE apprx_road_id_seq OWNED BY apprx_road.id;
ALTER TABLE ONLY apprx_road ALTER COLUMN id SET DEFAULT nextval('apprx_road_id_seq'::regclass);


--
-- Create node table, a node type can be either transformer or house
--

CREATE TABLE node (
	id bigint NOT NULL,
	osm_id bigint NOT NULL,
	node_type text, 
	max_capacity int,
	max_load int,
	way geometry(Point,900913),	
	projected_way geometry(Point,900913)
);

CREATE SEQUENCE node_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE node_id_seq OWNED BY node.id;
ALTER TABLE ONLY node ALTER COLUMN id SET DEFAULT nextval('node_id_seq'::regclass);

--
-- Create edge table, every node pair and its distance along the long
--







