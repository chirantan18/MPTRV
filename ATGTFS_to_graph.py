#import relevant libraries
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import time
from haversine import haversine, Unit
from itertools import combinations
from tqdm import tqdm
import pickle
import random

#convert GTFS data to dataframes
#GTFS from AT last updated 11 April
PATH = "/Users/chirantan/UoA MEnngSt/Research Project Z/Python/AT_GTFS/"

stops_df = pd.read_csv(f"{PATH}stops.txt")
trips_df = pd.read_csv(f"{PATH}trips.txt")
stop_times_df = pd.read_csv(f"{PATH}stop_times.txt")
routes_df = pd.read_csv(f"{PATH}routes.txt")
agency_df = pd.read_csv(f"{PATH}agency.txt")
calendar_df = pd.read_csv(f"{PATH}calendar.txt")
#consider only 1 trip for each shape for extraction of nodes and edges later
trips_filter_df = trips_df.groupby("shape_id").first().reset_index()


#exclude metro replacement bus and regional train service
agency_to_exclude = ["ATMB", "WRC"]

#consider trips/services that run on weekdays atleast 4 days a week
service_id_exclude = []

for i, day in calendar_df.iterrows():
    x = day["monday"] + day["tuesday"] + day["wednesday"] + day["thursday"] + day ["friday"]
    if x < 4:
        service_id_exclude.append(day["service_id"])
        
#merge dataframes for trips and stoptimes
merged_df = pd.merge(trips_df, stop_times_df, how = "outer", on = "trip_id")
#filter sevices ids from the exclusion list
merged_df = merged_df.drop(merged_df[merged_df["service_id"].isin(service_id_exclude)].index)
#only consider first stop sequence for frequency
merged_df = merged_df.drop(merged_df[merged_df["stop_sequence"] > 1].index)
#filter for 6am to 8pm trips
merged_df = merged_df.drop(merged_df[merged_df["arrival_time"].str[:2].astype(int) >= 20].index)
merged_df = merged_df.drop(merged_df[merged_df["arrival_time"].str[:2].astype(int) < 6].index)

#add a column for each hour 
merged_df["hour"] = merged_df["arrival_time"].apply(lambda x: time.strptime(x, "%H:%M:%S").tm_hour)

#merge dataframe with routes to calculate frequecy per route
routes_merged_df = pd.merge(merged_df, routes_df, how = "outer", on = "route_id")


#calculate frequency for bus routes only 
#metro and ferry frequecy for all routes is comparable as per frequency analysis of whole network
#also express bus routes can be excluded and used as separate category for bus routes due to the infrastructure differences

#Bus route_type = 3, filter bus routes, 
bus_df = routes_merged_df.drop(routes_merged_df[routes_merged_df["route_type"]!= 3].index)
#remove agencies to exclude
bus_df = bus_df.drop(bus_df[bus_df["agency_id"].isin(agency_to_exclude)].index)

#group dataframe in following order and size the hour subgroup is no. of trips that hour for that route
#sort the data dataframe
bus_frequency_df = bus_df.groupby(["route_id", "service_id", "direction_id", "hour" ]).size().reset_index(name="no_of_trips")
bus_frequency_df = bus_frequency_df.sort_values(["route_id", "direction_id", "service_id"])    

#calculate mean/average of frequencies,
#note: median was same as avaerage for 90% of routes, 
#given peak hour frequency mean was considered as most accurate way to find center in this dataframe
bus_mean_frequency_df = bus_frequency_df.groupby(["route_id"])["no_of_trips"].mean().reset_index(name = "frequency")
bus_mean_frequency_df["frequency"] = bus_mean_frequency_df["frequency"].round(decimals=0)

""" filter bus routes in frequency levels 
Level 1 = frequent #Frequency >=5 (not considering rapid transit routes)
Level 2 = non frequent  #Frequency <=4
above criterion list bus routes, trips and stops for all levels
also express bus routes can be used as separate category for bus routes due to the infrastructure differences
considering capacity of modes and frequency weight will be assigned to the edges
Metro = 6 cars (760pax) and 3 cars (380pax), as per kiwirail, for this study assume  avg 4.5cars capacity i.e.570
Ferry = 400pax(source seacat),
BusEx = 72pax (48pax seated) for regular bus, 106pax (90pax seated) for double decker, most express route use double decker so assume capacity 90pax
Bus1 = 72pax
Bus2 = 72pax
assuming avg frequecies for these modes pax per houe capacity will 
Metro = 2280pax (0.1)
Ferry = 400pax  (0.5)
BusEx = 720pax  (0.3)
Bus1 = 432pax   (0.5)
Bus2 = 216pax   (1)
ratio (rounded) of these modes is 10:2:3:2:1, inverse ratio for edge weights is given above """



#express bus routes, trips and stops
busex_routes = ["NX1-203", "NX2-207", "WX1-206", "AIR-221"]

busex_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in busex_routes and trip["direction_id"] == 0 and trip["trip_id"] not in busex_trips:
        busex_trips.append(trip["trip_id"])
        
busex_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in busex_trips and stop_time["stop_id"] not in busex_stops:
        busex_stops.append(stop_time["stop_id"])
        
print(busex_routes, "\n", len(busex_routes))
print(busex_trips, "\n", len(busex_trips))
print(busex_stops, "\nBus Express Stop =", len(busex_stops))

#Bus Level 1 Frequency routes, trips and stops 
bus1_routes = []

for i, route in bus_mean_frequency_df.iterrows():
    if route["frequency"] >= 4:
        bus1_routes.append(route["route_id"])

bus1_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in bus1_routes and trip["direction_id"] == 0:
        bus1_trips.append(trip["trip_id"])
        
bus1_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in bus1_trips and stop_time["stop_id"] not in (busex_stops, bus1_stops):
        bus1_stops.append(stop_time["stop_id"])

print(bus1_routes, "\n", len(bus1_routes))
print(bus1_trips, "\n", len(bus1_trips))
print(bus1_stops, "\nBus LVL 1 Stop =", len(bus1_stops))

#Bus Level 2 Frequency routes, trips and stops
bus2_routes = []

for i, route in bus_mean_frequency_df.iterrows():
    if route["frequency"] <= 3:
        bus2_routes.append(route["route_id"])

bus2_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in bus2_routes and trip["direction_id"] == 0:
        bus2_trips.append(trip["trip_id"])
        
bus2_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in bus2_trips and stop_time["stop_id"] not in (busex_stops, bus1_stops, bus2_stops):
        bus2_stops.append(stop_time["stop_id"])

print(bus2_routes, "\n", len(bus2_routes))
print(bus2_trips, "\n", len(bus2_trips))
print(bus2_stops, "\nBus LVL 2 Stop =", len(bus2_stops))

#Metro route_type = 2, filter metro routes, and then trips
metro_routes = []

for i, route in routes_df.iterrows():
    if route["route_type"] == 2 and route["agency_id"] not in agency_to_exclude:
        metro_routes.append(route["route_id"])

metro_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in metro_routes and trip["direction_id"] == 0:
        metro_trips.append(trip["trip_id"])
        
metro_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in metro_trips and stop_time["stop_id"] not in metro_stops:
        metro_stops.append(stop_time["stop_id"])

print(metro_routes, "\n", len(metro_routes))
print(metro_trips, "\n", len(metro_trips))
print(metro_stops, "\nMetro Stops =", len(metro_stops))

#Ferry route_type = 4, filter ferry routes, and then trips
ferry_routes = []

for i, route in routes_df.iterrows():
    if route["route_type"] == 4 and route["agency_id"] not in agency_to_exclude:
        ferry_routes.append(route["route_id"])

ferry_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in ferry_routes and trip["direction_id"] == 0:
        ferry_trips.append(trip["trip_id"])
        
ferry_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in ferry_trips and stop_time["stop_id"] not in ferry_stops:
        ferry_stops.append(stop_time["stop_id"])


print(ferry_routes, "\n", len(ferry_routes))
print(ferry_trips, "\n", len(ferry_trips))
print(ferry_stops, "\nFerry Stop =", len(ferry_stops))

#define function to replace stop_id with parent station,
#INPUT - stop_id,
#OUTPUT - if parent station exist replaced with parent station stop_id or same stop_id returned

def get_stop_id(Stop_id):
    for i, stop in stops_df.iterrows():
        if stop["stop_id"] == Stop_id:
            if not pd.isnull(stop["parent_station"]):
                return stop["parent_station"]
            else:
                return Stop_id

def get_stop_name_and_pos(Stop_id):
    for i, stop in stops_df.iterrows():
        if stop["stop_id"] == Stop_id:
            return stop["stop_name"], (stop["stop_lon"], stop["stop_lat"])

#define function to check if nodes are in graph and if not add, while replacing stop_id with parent station
#INPUT - Graph, stop to be added, stop name, stop coordinates
#OUTPUT - node added if not in graph

def check_and_add_node(graph, STOP, mode, weight):
    STOP = get_stop_id(STOP)
    name, pos = get_stop_name_and_pos(STOP)
    if not G.has_node(STOP):
        G.add_node(STOP, name = name, pos = pos, mode = mode, weight = weight)
        #print(f"{STOP} added to graph")
    #else:
        #print(f"{STOP} already in graph")

#define function to check if edges are in graph and if not add, while replacing stop_id with parent station
#INPUT - Graph, stop1, stop2, edge color
#OUTPUT - edge added if not in graph

def check_and_add_edge(graph, S1, S2, mode, color, weight):
    S1 = get_stop_id(S1)
    S2 = get_stop_id(S2)
    if not graph.has_edge(S1, S2) and S1 != S2:
        graph.add_edge(S1, S2, mode = mode, color = color, weight = weight)
        #print(f"Edge {S1, S2} added to graph with color {color} and mode {mode}")
    #else:
        #print(f"Edge {S1, S2} is already in graph")           


#create empty graph G
G = nx.Graph()


# Add nodes for metro, ferry and bus (all levels) stops, using get_stop_id() function
#initialise progress bar
progress_bar = tqdm(total = len(stops_df.index), desc = "Adding Metro Nodes")
#start iterations
for i, stop in stops_df.iterrows():
    if stop["stop_id"] in metro_stops:
        check_and_add_node(G, stop["stop_id"], "Metro", 0.1)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#initialise progress bar
progress_bar = tqdm(total = len(stops_df.index), desc = "Adding Ferry Nodes")
#start iterations        
for i, stop in stops_df.iterrows():
    if stop["stop_id"] in ferry_stops:
        check_and_add_node(G, stop["stop_id"], "Ferry", 0.5)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#initialise progress bar
progress_bar = tqdm(total = len(stops_df.index), desc = "Adding BusEx Nodes")
#start iterations        
for i, stop in stops_df.iterrows():
    if stop["stop_id"] in busex_stops:
        check_and_add_node(G, stop["stop_id"], "Bus Express", 0.3)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#initialise progress bar
progress_bar = tqdm(total = len(stops_df.index), desc = "Adding Bus1 Nodes")
#start iterations        
for i, stop in stops_df.iterrows():        
    if stop["stop_id"] in bus1_stops:
        check_and_add_node(G, stop["stop_id"], "Bus LVL1", 0.5)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#initialise progress bar
progress_bar = tqdm(total = len(stops_df.index), desc = "Adding Bus2 Nodes")
#start iterations        
for i, stop in stops_df.iterrows():        
    if stop["stop_id"] in bus2_stops:
        check_and_add_node(G, stop["stop_id"], "Bus LVL2", 1)
        
    progress_bar.update(1)
#close progress bar
progress_bar.close()
        
#Add edges for metro trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(stop_times_df.index), desc = "Adding Metro Edges")
#start iterations
for i, stop_time in stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time['trip_id']
    stop_id = stop_time['stop_id']
    if stop_sequence > 1 and trip_id in metro_trips:
        prev_stop_id = stop_times_df.loc[(stop_times_df['trip_id'] == trip_id) & (stop_times_df['stop_sequence'] == stop_sequence - 1), 'stop_id'].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id,"Metro", "red", 0.1)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()
        

#Add edges for ferry trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(stop_times_df.index), desc = "Adding Ferry Edges")
#start iterations
for i, stop_time in stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time['trip_id']
    stop_id = stop_time['stop_id']
    if stop_sequence > 1 and trip_id in ferry_trips:
        prev_stop_id = stop_times_df.loc[(stop_times_df['trip_id'] == trip_id) & (stop_times_df['stop_sequence'] == stop_sequence - 1), 'stop_id'].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id,"Ferry", "blue", 0.5)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()


#Add edges for bus express trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(stop_times_df.index), desc = "Adding BusEx Edges")
#start iterations
for i, stop_time in stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time['trip_id']
    stop_id = stop_time['stop_id']
    if stop_sequence > 1 and trip_id in busex_trips:
        prev_stop_id = stop_times_df.loc[(stop_times_df['trip_id'] == trip_id) & (stop_times_df['stop_sequence'] == stop_sequence - 1), 'stop_id'].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id, "Bus Express", "black", 0.3)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()
            
#Add edges for bus level 1 trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(stop_times_df.index), desc = "Adding Bus1 Edges")
#start iterations
for i, stop_time in stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time['trip_id']
    stop_id = stop_time['stop_id']
    if stop_sequence > 1 and trip_id in bus1_trips:
        prev_stop_id = stop_times_df.loc[(stop_times_df['trip_id'] == trip_id) & (stop_times_df['stop_sequence'] == stop_sequence - 1), 'stop_id'].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id, "Bus LVL1", "green", 0.5)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#Add edges for bus level 2 trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(stop_times_df.index), desc = "Adding Bus2 Edges")
#start iterations
for i, stop_time in stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time['trip_id']
    stop_id = stop_time['stop_id']
    if stop_sequence > 1 and trip_id in bus2_trips:
        prev_stop_id = stop_times_df.loc[(stop_times_df['trip_id'] == trip_id) & (stop_times_df['stop_sequence'] == stop_sequence - 1), 'stop_id'].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id, "Bus LVL2", "orange", 1)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#remove nodes with no edges 
def remove_nodes_with_no_edges(graph):
    nodes_to_remove = [node for node in graph.nodes if graph.degree(node) == 0]
    graph.remove_nodes_from(nodes_to_remove)

print(f"Nodes - {G.number_of_nodes()}")    

remove_nodes_with_no_edges(G)   

print(f"Nodes - {G.number_of_nodes()}")   

#networkx has pos as (lon, lat), haversine needs (lat, lon), useing tuple[::-1]
#check and add walking transfer
max_walk_distance = 500
#initialise progress bar
progress_bar = tqdm(total = len(list(combinations(G.nodes(), 2))), desc = "Adding Walking Transsfers")

mode_1 = ["Metro", "Ferry"]
mode_2 = ["Metro", "Ferry", "Bus Express", "Bus LVL1", "Bus LVL2"]

pos_dict = nx.get_node_attributes(G, "pos")
mode_dict = nx.get_node_attributes(G, "mode")
#start iterations
for s1, s2 in combinations(G.nodes(), 2):
    pos1 = pos_dict[s1]
    pos2 = pos_dict[s2]
    mode1 = mode_dict[s1]
    mode2 = mode_dict[s2]
    
    distance = haversine(pos1[::-1], pos2[::-1], unit = "m")
    
    if distance <= max_walk_distance and mode1 in mode_1 and mode2 in mode_2 and mode1 != mode2:
        check_and_add_edge(G, s1, s2, "Walk", "yellow", 2)

    progress_bar.update(1)
#close progress bar
progress_bar.close()
            


#get lists for nodes as per modes
metro_nodes = []
ferry_nodes = []
bus_nodes = []

for node in G.nodes():
    if mode_dict[node] == "Metro":
        metro_nodes.append(node)
    elif mode_dict[node] == "Ferry":
        ferry_nodes.append(node)
    else:
        bus_nodes.append(node)    

#copy graph for creating metro, ferry and bus individual graphs
Gm = G.copy()
Gf = G.copy()
#remove ferry nodes from metro graph
Gm.remove_nodes_from(ferry_nodes)
#copy graph for bus from metro as ferry is already removed
Gb = Gm.copy()
#remove bus nodes from metro and ferry graphs, metro graph is done
Gm.remove_nodes_from(bus_nodes)
Gf.remove_nodes_from(bus_nodes)
#remove metro nodes from bus and ferry graphs, noth graphs are done
Gb.remove_nodes_from(metro_nodes)
Gf.remove_nodes_from(metro_nodes)

#bus network has waiheke bus network which is not fully conneted in whole graph without ferry, so remove that 
#get connected components and remove smaller one
connected_bus_networks = list(nx.connected_components(Gb))

Gb.remove_nodes_from(min(connected_bus_networks, key = len))

graph_path = "ATgraph.pkl"  
graph_metro_path = "ATMetrograph.pkl" 
graph_ferry_path = "ATFerrygraph.pkl"
graph_bus_path = "ATBusgraph.pkl"



with open(graph_path, "wb") as g:
    pickle.dump(G, g)      

with open(graph_metro_path, "wb") as g:
    pickle.dump(Gm, g)    
    
with open(graph_ferry_path, "wb") as g:
    pickle.dump(Gf, g)    
    
with open(graph_bus_path, "wb") as g:
    pickle.dump(Gb, g)    

with open(graph_path, "rb") as g:
    H = pickle.load(g)

print(len(G.nodes()))
print(len(H.nodes()))
print(len(G.edges()))
print(len(H.edges()))

G_node_attr_dict = nx.get_node_attributes(G, "name")
H_node_attr_dict = nx.get_node_attributes(H, "name")

rand_node = random.choice(list(G.nodes()))

print(G_node_attr_dict[rand_node], H_node_attr_dict[rand_node])



labels = nx.get_node_attributes(G, "name")   
pos = nx.get_node_attributes(G, "pos")
color = nx.get_edge_attributes(G, "color")
color = color.values()
nx.draw_networkx(G, pos, labels = labels, node_size = 10, edge_color = color)
plt.show()