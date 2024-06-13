#import relevant libraries
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import time
from haversine import haversine, Unit
from itertools import combinations
from tqdm import tqdm
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

print("Loading GTFS Data")
#convert GTFS data to dataframes
PATH = "/Users/chirantan/UoA MEnngSt/Research Project Z/Python/SYD_GTFS/"

stops_df = pd.read_csv(f"{PATH}stops.txt", low_memory= False)
trips_df = pd.read_csv(f"{PATH}trips.txt")
stop_times_df = pd.read_csv(f"{PATH}stop_times.txt", low_memory= False)
routes_df = pd.read_csv(f"{PATH}routes.txt")
calendar_df = pd.read_csv(f"{PATH}calendar.txt")
#consider only 1 trip for each shape for extraction of nodes and edges later
trips_filter_df = trips_df.groupby("shape_id").first().reset_index()


#exclude metro replacement bus and regional train service
routes_to_include = ["Sydney Buses Network", "Sydney Trains Network", "Sydney Metro Network", "Sydney Light Rail Network", "Sydney Ferries Network"]

routes_to_exclude = []

for i, route in routes_df.iterrows():
    if route["route_desc"] not in routes_to_include:
        if route["route_desc"] not in routes_to_exclude:
            routes_to_exclude.append(route["route_desc"])

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
routes_merged_df = routes_merged_df.drop(routes_merged_df[routes_merged_df["route_desc"].isin(routes_to_exclude)].index)

#calculate frequency for bus routes only 
#metro and ferry frequecy for all routes is comparable as per frequency analysis of whole network
#also express bus routes can be excluded and used as separate category for bus routes due to the infrastructure differences

#Bus route_type = 700 (for SYD GTFS, 3 is not present as route type), filter bus routes, 
bus_df = routes_merged_df.drop(routes_merged_df[routes_merged_df["route_type"]!= 700].index)


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
Level 1 = frequent #Frequency >=4 (not considering rapid transit routes)
Level 2 = non frequent  #Frequency <=3
####Due to the size of sydney bus network only frequent bus services i.e. bus level 1 will be considered for this study
above criterion list bus routes, trips and stops for all levels

Metro/trains = 8 cars, approx. peak capacity including seated and standing pax - 1200
Light Rail = 450
Ferry = Using same for Auckland, using avg capacity for common ferry vessels 400pax(source seacat)
Bus1 = 80pax
Bus2 = 80pax
assuming avg frequecies for these modes pax per hour capacity will 
Train = 2400pax (0.1)
Metro = 12000pax(0.02), high frequency route, metro running every 4-6 mins
Light Rail = 3150pax (0.08)
Ferry = 800pax  (0.3)
Bus1 = 480pax   (0.5)
Bus1 = 240pax   (1)
ratio (rounded) and inverse ratio for edge weights is given above """


print("Parsing GTFS Data")
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
    if stop_time["trip_id"] in bus1_trips and stop_time["stop_id"] not in bus1_stops:
        bus1_stops.append(stop_time["stop_id"])

print(bus1_routes, "\n", len(bus1_routes))
print(bus1_trips, "\n", len(bus1_trips))
print(bus1_stops, "\nBus LVL 1 Stop =", len(bus1_stops))


#Bus Level 2 Frequency routes, trips and stops 
bus2_routes = []
for i, route in bus_mean_frequency_df.iterrows():
    if 1< route["frequency"] < 4:
        bus2_routes.append(route["route_id"])

bus2_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in bus2_routes and trip["direction_id"] == 0:
        bus2_trips.append(trip["trip_id"])
        
bus2_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in bus2_trips and stop_time["stop_id"] not in bus2_stops:
        bus2_stops.append(stop_time["stop_id"])

print(bus2_routes, "\n", len(bus2_routes))
print(bus2_trips, "\n", len(bus2_trips))
print(bus2_stops, "\nBus LVL 2 Stop =", len(bus2_stops))


#Train route_type = 2, filter train routes, and then trips
train_routes = []

for i, route in routes_df.iterrows():
    if route["route_type"] == 2 and route["route_desc"] not in routes_to_exclude:
        train_routes.append(route["route_id"])

train_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in train_routes and trip["direction_id"] == 0:
        train_trips.append(trip["trip_id"])
        
train_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in train_trips and stop_time["stop_id"] not in train_stops:
        train_stops.append(stop_time["stop_id"])

print(train_routes, "\n", len(train_routes))
print(train_trips, "\n", len(train_trips))
print(train_stops, "\nTrain Stops =", len(train_stops))

#Metro route_type = 401, filter metro routes, and then trips
metro_routes = []

for i, route in routes_df.iterrows():
    if route["route_type"] == 401 and route["route_desc"] not in routes_to_exclude:
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

#Lrail route_type = 900, filter metro routes, and then trips
Lrail_routes = []

for i, route in routes_df.iterrows():
    if route["route_type"] == 900 and route["route_desc"] not in routes_to_exclude:
        Lrail_routes.append(route["route_id"])

Lrail_trips = []

for i, trip in trips_filter_df.iterrows():
    if trip["route_id"] in Lrail_routes and trip["direction_id"] == 0:
        Lrail_trips.append(trip["trip_id"])
        
Lrail_stops = []

for i, stop_time in stop_times_df.iterrows():
    if stop_time["trip_id"] in Lrail_trips and stop_time["stop_id"] not in Lrail_stops:
        Lrail_stops.append(stop_time["stop_id"])

print(Lrail_routes, "\n", len(Lrail_routes))
print(Lrail_trips, "\n", len(Lrail_trips))
print(Lrail_stops, "\nLight Rail Stops =", len(Lrail_stops))

#Ferry route_type = 4, filter ferry routes, and then trips
ferry_routes = []

for i, route in routes_df.iterrows():
    if route["route_type"] == 4 and route["route_desc"] not in routes_to_exclude:
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
        
## sort dataframes to keep only required trips & stops for faster processing with iterations
stops_to_keep = bus1_stops + bus2_stops + metro_stops + train_stops + Lrail_stops + ferry_stops
rapid_trips_to_keep = metro_trips + train_trips + Lrail_trips + ferry_trips 
bus_trips_to_keep = bus1_trips + bus2_trips
#stops filtered first to extract parents stops and then stops df filtered again for stops plus their parents stop 
stops_filter0_df = stops_df[stops_df["stop_id"].isin(stops_to_keep)]
# stop_times_train_df = stop_times_df[stop_times_df["trip_id"].isin(train_trips)]
# stop_times_train_df.to_excel("SYD_train_stop_times.xlsx") 
# Function to get parent node fot filtering
def parent_node_filter(args):
    stop, df = args
    for i, STOP in df.iterrows():
        if STOP["stop_id"] == stop:
            if not pd.isnull(STOP["parent_station"]):
                return STOP["parent_station"]

    
parent_stops = []

# Use ThreadPoolExecutor for parallel computation
with ThreadPoolExecutor() as ex:
    futures = [ex.submit(parent_node_filter, (stop, stops_filter0_df)) for stop in stops_to_keep]

    #Intialise progress bar
    progress_bar = tqdm(total = len(stops_to_keep), desc = "Adding Parent Nodes for filtering")
        
    for future in as_completed(futures):
        p_stop = future.result()
        parent_stops.append(p_stop)
        progress_bar.update(1)
    
    #close progress bar
    progress_bar.close()    
#initialise progress bar

stops_to_keep += parent_stops
#second round of filtering 
stops_filter_df = stops_df[stops_df["stop_id"].isin(stops_to_keep)]

rapid_stop_times_df = stop_times_df[stop_times_df["trip_id"].isin(rapid_trips_to_keep)]
bus_stop_times_df = stop_times_df[stop_times_df["trip_id"].isin(bus_trips_to_keep)]
stop_times_train_df = stop_times_df[stop_times_df["trip_id"].isin(train_trips)]
#upload memory that is not required
del stops_df
del stops_filter0_df
del stop_times_df
#define function to replace stop_id with parent station,
#INPUT - stop_id,
#OUTPUT - if parent station exist replaced with parent station stop_id or same stop_id returned

def get_stop_id(Stop_id):
    for i, stop in stops_filter_df.iterrows():
        if stop["stop_id"] == Stop_id:
            if not pd.isnull(stop["parent_station"]):
                return stop["parent_station"]
            else:
                return Stop_id

def get_stop_name_and_pos(Stop_id):
    for i, stop in stops_filter_df.iterrows():
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
#Metro Stops
#initialise progress bar
progress_bar = tqdm(total = len(stops_filter_df.index), desc = "Adding Metro Nodes")
#start iterations
for i, stop in stops_filter_df.iterrows():
    if stop["stop_id"] in metro_stops:
        check_and_add_node(G, stop["stop_id"], "Metro", 0.02)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#LRail stops
#initialise progress bar
progress_bar = tqdm(total = len(stops_filter_df.index), desc = "Adding Light Rail Nodes")
#start iterations
for i, stop in stops_filter_df.iterrows():
    if stop["stop_id"] in Lrail_stops:
        check_and_add_node(G, stop["stop_id"], "Lrail", 0.08)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#Train stops
#initialise progress bar
progress_bar = tqdm(total = len(stops_filter_df.index), desc = "Adding Train Nodes")
#start iterations
for i, stop in stops_filter_df.iterrows():
    if stop["stop_id"] in train_stops:
        check_and_add_node(G, stop["stop_id"], "Train", 0.1)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#Ferry stops
#initialise progress bar
progress_bar = tqdm(total = len(stops_filter_df.index), desc = "Adding Ferry Nodes")
#start iterations        
for i, stop in stops_filter_df.iterrows():
    if stop["stop_id"] in ferry_stops:
        check_and_add_node(G, stop["stop_id"], "Ferry", 0.3)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#Bus1 stops
#initialise progress bar
progress_bar = tqdm(total = len(stops_filter_df.index), desc = "Adding Bus1 Nodes")
#start iterations        
for i, stop in stops_filter_df.iterrows():        
    if stop["stop_id"] in bus1_stops:
        check_and_add_node(G, stop["stop_id"], "BusLVL1", 0.5)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#Bus2 stops
#initialise progress bar
progress_bar = tqdm(total = len(stops_filter_df.index), desc = "Adding Bus2 Nodes")
#start iterations        
for i, stop in stops_filter_df.iterrows():        
    if stop["stop_id"] in bus2_stops:
        check_and_add_node(G, stop["stop_id"], "BusLVL2", 1)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

        
#Add edges for metro trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(rapid_stop_times_df.index), desc = "Adding Metro Edges")
#start iterations
for i, stop_time in rapid_stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time["trip_id"]
    stop_id = stop_time["stop_id"]
    if stop_sequence > 1 and trip_id in metro_trips:
        prev_stop_id = rapid_stop_times_df.loc[(rapid_stop_times_df["trip_id"] == trip_id) & (rapid_stop_times_df["stop_sequence"] == stop_sequence - 1), "stop_id"].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id,"Metro", "black", 0.02)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#Add edges for Light rail trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(rapid_stop_times_df.index), desc = "Adding Light rail Edges")
#start iterations
for i, stop_time in rapid_stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time["trip_id"]
    stop_id = stop_time["stop_id"]
    if stop_sequence > 1 and trip_id in Lrail_trips:
        prev_stop_id = rapid_stop_times_df.loc[(rapid_stop_times_df["trip_id"] == trip_id) & (rapid_stop_times_df["stop_sequence"] == stop_sequence - 1), "stop_id"].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id,"Lrail", "magenta", 0.08)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

#Add edges for train trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(rapid_stop_times_df.index), desc = "Adding Train Edges")
#start iterations
for i, stop_time in rapid_stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time["trip_id"]
    stop_id = stop_time["stop_id"]
    if stop_sequence > 1 and trip_id in train_trips:
        prev_stop = rapid_stop_times_df.loc[(rapid_stop_times_df["trip_id"] == trip_id) & (rapid_stop_times_df["stop_sequence"] == stop_sequence - 1), "stop_id"]
        #to catch recurring index error in train edges
        if not prev_stop.empty: 
            prev_stop_id = prev_stop.values[0]
            check_and_add_edge(G, prev_stop_id, stop_id,"Train", "red", 0.1)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()        

#Add edges for ferry trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(rapid_stop_times_df.index), desc = "Adding Ferry Edges")
#start iterations
for i, stop_time in rapid_stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time["trip_id"]
    stop_id = stop_time["stop_id"]
    if stop_sequence > 1 and trip_id in ferry_trips:
        prev_stop_id = rapid_stop_times_df.loc[(rapid_stop_times_df["trip_id"] == trip_id) & (rapid_stop_times_df["stop_sequence"] == stop_sequence - 1), "stop_id"].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id,"Ferry", "blue", 0.3)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()

            
#Add edges for bus level 1 trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(bus_stop_times_df.index), desc = "Adding Bus 1 Edges")
#start iterations
for i, stop_time in bus_stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time["trip_id"]
    stop_id = stop_time["stop_id"]
    if stop_sequence > 1 and trip_id in bus1_trips:
        prev_stop_id = bus_stop_times_df.loc[(bus_stop_times_df["trip_id"] == trip_id) & (bus_stop_times_df["stop_sequence"] == stop_sequence - 1), "stop_id"].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id, "BusLVL2", "green", 0.5)
    
    progress_bar.update(1)
#close progress bar
progress_bar.close()


#Add edges for bus level 2 trips, using defined functions and lists
#initialise progress bar
progress_bar = tqdm(total = len(bus_stop_times_df.index), desc = "Adding Bus 2 Edges")
#start iterations
for i, stop_time in bus_stop_times_df.iterrows():
    stop_sequence = stop_time["stop_sequence"]
    trip_id = stop_time["trip_id"]
    stop_id = stop_time["stop_id"]
    if stop_sequence > 1 and trip_id in bus2_trips:
        prev_stop_id = bus_stop_times_df.loc[(bus_stop_times_df["trip_id"] == trip_id) & (bus_stop_times_df["stop_sequence"] == stop_sequence - 1), "stop_id"].values[0]
        check_and_add_edge(G, prev_stop_id, stop_id, "BusLVL2", "yellow", 1)
    
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

mode_1 = ["Metro", "Ferry", "Lrail", "Train"]
mode_2 = ["Metro", "Ferry", "Lrail", "Train", "BusLVL1", "BusLVL2"]

pos_dict = nx.get_node_attributes(G, "pos")
mode_dict = nx.get_node_attributes(G, "mode")
#start iterations
for s1, s2 in combinations(G.nodes(), 2):
    pos1 = pos_dict[s1]
    pos2 = pos_dict[s2]
    mode1 = mode_dict[s1]
    mode2 = mode_dict[s2]
    
    if mode1 in mode_1 and mode2 in mode_2 and mode1 != mode2:
        distance = haversine(pos1[::-1], pos2[::-1], unit = "m")
    
        if distance <= max_walk_distance:
            check_and_add_edge(G, s1, s2, "Walk", "yellow", 2)

    progress_bar.update(1)
#close progress bar
progress_bar.close()
            


#get lists for nodes as per modes
metro_train_nodes = []
ferry_nodes = []
bus_nodes = []

for node in G.nodes():
    if mode_dict[node] == "Metro":
        metro_train_nodes.append(node)
    elif mode_dict[node] == "Lrail":
        metro_train_nodes.append(node)
    elif mode_dict[node] == "Train":
        metro_train_nodes.append(node)
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
Gr = Gf.copy()
#remove metro nodes from bus and ferry graphs, noth graphs are done
Gb.remove_nodes_from(metro_train_nodes)
Gf.remove_nodes_from(metro_train_nodes)

#bus network has waiheke bus network which is not fully conneted in whole graph without ferry, so remove that 
#get connected components and remove smaller one
connected_bus_networks = list(nx.connected_components(Gb))
connected_networks = list(nx.connected_components(G))


print(len(connected_bus_networks))

graph_path = "New/SYDgraph.pkl"  
graph_metro_path = "New/SYDMetrograph.pkl" 
graph_ferry_path = "New/SYDFerrygraph.pkl"
graph_bus_path = "New/SYDBusgraph.pkl"
graph_rapid_path = "New/SYDrapidgraph.pkl"



with open(graph_path, "wb") as g:
    pickle.dump(G, g)      

with open(graph_metro_path, "wb") as g:
    pickle.dump(Gm, g)    
    
with open(graph_ferry_path, "wb") as g:
    pickle.dump(Gf, g)    
    
with open(graph_bus_path, "wb") as g:
    pickle.dump(Gb, g)    

with open(graph_rapid_path, "wb") as g:
    pickle.dump(Gr, g)  

with open(graph_path, "rb") as g:
    H = pickle.load(g)

print(len(G.nodes()))
print(len(H.nodes()))
print(len(G.edges()))
print(len(H.edges()))


labels = nx.get_node_attributes(G, "name")   
pos = nx.get_node_attributes(G, "pos")
color = nx.get_edge_attributes(G, "color")
color = color.values()
nx.draw_networkx(G, pos, labels = labels, node_size = 10, edge_color = color)
plt.show()
