#import relevant libraries
import networkx as nx
import pandas as pd
import numpy as np
import pickle
from itertools import combinations
from tqdm import tqdm
from haversine import haversine, Unit

#add graph pickel file   
graph_path = "ATgraph.pkl"  
graph_metro_path = "ATMetrograph.pkl" 
graph_ferry_path = "ATFerrygraph.pkl"
graph_bus_path = "ATBusgraph.pkl"


with open(graph_path, "rb") as g:
    G = pickle.load(g)

with open(graph_metro_path, "rb") as g:
    Gm = pickle.load(g)
    
with open(graph_ferry_path, "rb") as g:
    Gf = pickle.load(g)
    
with open(graph_bus_path, "rb") as g:
    Gb = pickle.load(g)
    

node_mode_dict = nx.get_node_attributes(G, "mode")

#only metro, ferry and busEx nodes are analysed for vulnarabilty, as these edges have least weight
rapid_modes = ["Metro", "Ferry", "Bus Express"]

non_rapid_nodes = []


for node in G.nodes():
    if not node_mode_dict[node] in rapid_modes:
        non_rapid_nodes.append(node)

Gr = G.copy()
Gr.remove_nodes_from(non_rapid_nodes)

edge_mode_dict = nx.get_edge_attributes(G, "mode")

for edge in Gr.edges():
    if edge_mode_dict[edge] == "Metro":
        Gr.edges[edge]["weight"] = 0.2
    elif edge_mode_dict[edge] == "Ferry":
        Gr.edges[edge]["weight"] = 1
    elif edge_mode_dict[edge] == "BusEx":
        Gr.edges[edge]["weight"] = 0.6
        
print("Graphs loaded....")

#Add CRL nodes, remove edge between kingland and grafto to add Mt Eden in between
#(-36.850625, 174.762764) Te Waihorotiu Station
#(-36.858519, 174.758777) K Road Station
#(-36.867721, 174.758437) Maungawhau Station
#Grafton_Kingland_edge = ('277-dfb27cf9', '122-34ecc043')
Gn = G.copy()
Gn.remove_edge('277-dfb27cf9', '122-34ecc043')

Gn.add_node("Te Waihorotiu Station", name = "Te Waihorotiu Station", pos = (174.762764, -36.850625), mode = "Metro", weight = 0.1)
Gn.add_node("K Road Station", name = "K Road Station", pos = (174.758777, -36.858519), mode = "Metro", weight = 0.1)
Gn.add_node("Maungawhau Station", name = "Maungawhau Station", pos = (174.758437, -36.867721), mode = "Metro", weight = 0.1)
#add edges for mt eden and grafton/kingland
Gn.add_edge('277-dfb27cf9', "Maungawhau Station", mode = "Metro", color = "red", weight = 0.1)
Gn.add_edge("Maungawhau Station", '122-34ecc043', mode = "Metro", color = "red", weight = 0.1)
#add CRL edges
Gn.add_edge('133-b84b56d3', "Te Waihorotiu Station", mode = "Metro", color = "red", weight = 0.1)
Gn.add_edge("Te Waihorotiu Station", "K Road Station", mode = "Metro", color = "red", weight = 0.1)
Gn.add_edge("K Road Station", "Maungawhau Station", mode = "Metro", color = "red", weight = 0.1)

#add walikng edges for new stations
#networkx has pos as (lon, lat), haversine needs (lat, lon), useing tuple[::-1]
#check and add walking transfer
max_walk_distance = 500
#initialise progress bar
progress_bar = tqdm(total = len(Gn.nodes()), desc = "Adding Walking Transsfers")

mode_1 = ["Metro"]
mode_2 = ["Metro", "Ferry", "Bus Express", "Bus LVL1", "Bus LVL2"]

pos_dict = nx.get_node_attributes(Gn, "pos")
mode_dict = nx.get_node_attributes(Gn, "mode")
#start iterations
for s1 in Gn.nodes():
    for s2 in Gn.nodes():
        if s1 != s2:
            pos1 = pos_dict[s1]
            pos2 = pos_dict[s2]
            mode1 = mode_dict[s1]
            mode2 = mode_dict[s2]
    
            distance = haversine(pos1[::-1], pos2[::-1], unit = "m")
    
            if distance <= max_walk_distance and mode1 in mode_1 and mode2 in mode_2 and mode1 != mode2:
                if not Gn.has_edge(s1, s2):
                    Gn.add_edge(s1, s2, mode = "Walk", color = "yellow", weight = 2)

    progress_bar.update(1)
#close progress bar
progress_bar.close()


    
print(len(Gn.nodes()))
print(len(Gn.edges()))

Gnm = Gn.copy()
Gnr = Gn.copy()
Gnr.remove_nodes_from(non_rapid_nodes)
for node in G.nodes():
    if node_mode_dict[node] != "Metro":
        Gnm.remove_node(node)
edge_mode_dict = nx.get_edge_attributes(G, "mode")

for edge in Gr.edges():
    if edge_mode_dict[edge] == "Metro":
        Gr.edges[edge]["weight"] = 0.2
    elif edge_mode_dict[edge] == "Ferry":
        Gr.edges[edge]["weight"] = 1
    elif edge_mode_dict[edge] == "BusEx":
        Gr.edges[edge]["weight"] = 0.6
        
print("CRL Graphs loaded....")

graph_metric_df = pd.DataFrame()

graph_metric_df["Graph"] = ["Multi", "Rapid", "Metro", "Ferry", "Bus", "Multi - CRL", "Rapid - CRL", "Metro - CRL"]

graph_metric_df["Nodes"] = [len(G.nodes()), len(Gr.nodes()), len(Gm.nodes()), len(Gf.nodes()), 
                            len(Gb.nodes()), len(Gn.nodes()), len(Gnr.nodes()), len(Gnm.nodes())]
graph_metric_df["Edges"] = [len(G.edges()), len(Gr.edges()), len(Gm.edges()), len(Gf.edges()), 
                            len(Gb.edges()), len(Gn.edges()), len(Gnr.edges()), len(Gnm.edges())]


print("Nodes, Edges added....")

def get_graph_degree(graph):
    dict_degree = dict(graph.degree())
    k = 0
    for key in dict_degree:
        k += dict_degree[key]
        
    return k/len(graph.nodes())

graph_metric_df["Degree"] = [get_graph_degree(G), get_graph_degree(Gr), get_graph_degree(Gm), get_graph_degree(Gf), 
                             get_graph_degree(Gb), get_graph_degree(Gn), get_graph_degree(Gnr), get_graph_degree(Gnm)]

print("Degree added....")
    
Lg = nx.average_shortest_path_length(G, weight= "weight", method= "floyd-warshall-numpy")
Lgr = nx.average_shortest_path_length(Gr, weight= "weight", method= "floyd-warshall-numpy")
Lgm = nx.average_shortest_path_length(Gm, method= "floyd-warshall-numpy")
Lgf = nx.average_shortest_path_length(Gf, method= "floyd-warshall-numpy")
Lgb = nx.average_shortest_path_length(Gb, weight= "weight", method= "floyd-warshall-numpy")
Lgn = nx.average_shortest_path_length(Gn, weight= "weight", method= "floyd-warshall-numpy")
Lgnr = nx.average_shortest_path_length(Gnr, weight= "weight", method= "floyd-warshall-numpy")
Lgnm = nx.average_shortest_path_length(Gnm, method= "floyd-warshall-numpy")

graph_metric_df["Path Length"] = [Lg, Lgr, Lgm, Lgf, Lgb, Lgn, Lgnr, Lgnm]

print("Path length added....")

Dg = nx.diameter(G, weight = "weight")
Dgr = nx.diameter(Gr, weight = "weight")
Dgm = nx.diameter(Gm)
Dgf = nx.diameter(Gf)
Dgb = nx.diameter(Gb, weight = "weight")
Dgn = nx.diameter(Gn, weight = "weight")
Dgnr = nx.diameter(Gnr, weight = "weight")
Dgnm = nx.diameter(Gnm)

graph_metric_df["Diameter"] = [Dg, Dgr, Dgm, Dgf, Dgb, Dgn, Dgnr, Dgnm]

print("Diameter added....")

Cg = nx.average_clustering(G, weight= "weight")
Cgr = nx.average_clustering(Gr, weight= "weight")
Cgm = nx.average_clustering(Gm)
Cgf = nx.average_clustering(Gf)
Cgb = nx.average_clustering(Gb, weight= "weight")
Cgn = nx.average_clustering(Gn, weight= "weight")
Cgnr = nx.average_clustering(Gnr, weight= "weight")
Cgnm = nx.average_clustering(Gnm)

graph_metric_df["Clustering Coefficient"] = [Cg, Cgr, Cgm, Cgf, Cgb, Cgn, Cgnr, Cgnm]

print("Clustering added....")

#define fucntions to calculate the efficiency
#calculate shortest path using networkx using floyd_warshall_numpy method
def calculate_efficiency(graph, weight):
    #get np array of shortest distance
    d_array = nx.floyd_warshall_numpy(graph, weight = weight)
    #handle zeros for same node pairs, replace with "inf" so that reciprocal will be 0
    d_array = np.where(d_array == 0, np.inf, d_array)
    #get distance resiprocal
    d_array_reciprocal = np.reciprocal(d_array)
    #sum of all reciprocals
    sum_d_reciprocal = np.sum(d_array_reciprocal)
    #numbe of nodes
    N = len(graph.nodes())
    #return efficiency metric
    return sum_d_reciprocal/(N*(N-1))


#efficiency for whole network
Ef = calculate_efficiency(G, "weight")
Efr = calculate_efficiency(Gr, "weight")
Efm = calculate_efficiency(Gm, None)
Eff = calculate_efficiency(Gf, None)
Efb = calculate_efficiency(Gb, "weight")
Efn = calculate_efficiency(Gn, "weight")
Efnr = calculate_efficiency(Gnr, "weight")
Efnm = calculate_efficiency(Gnm, None)

graph_metric_df["Efficiency"] = [Ef,Efr, Efm, Eff, Efb, Efn, Efnr, Efnm]

print("Efficiency added....")
    
graph_metric_df.to_excel("AT_graphs Metrics with CRL2.xlsx") 