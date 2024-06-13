#import relevant libraries
import networkx as nx
import pandas as pd
import numpy as np
import pickle
import time

#add graph pickel file   
graph_path = "SYDgraph.pkl"  
graph_metro_path = "SYDMetrograph.pkl" 
graph_ferry_path = "SYDFerrygraph.pkl"
graph_rapid_path = "SYDrapidgraph.pkl"
graph_bus_path = "SYDBusgraph.pkl"

with open(graph_path, "rb") as g:
    G = pickle.load(g)

with open(graph_metro_path, "rb") as g:
    Gm = pickle.load(g)
    
with open(graph_ferry_path, "rb") as g:
    Gf = pickle.load(g)
    
with open(graph_rapid_path, "rb") as g:
    Gr = pickle.load(g)
    
with open(graph_bus_path, "rb") as g:
    Gb = pickle.load(g)
    
edge_mode_dict = nx.get_edge_attributes(G, "mode")

# weights for rapid are updated to have lowest weight as 1 in the ratio
for edge in Gr.edges():
    if edge_mode_dict[edge] == "Metro":
        Gr.edges[edge]["weight"] = 0.07
    elif edge_mode_dict[edge] == "Train":
        Gr.edges[edge]["weight"] = 0.3
    elif edge_mode_dict[edge] == "Lrail":
        Gr.edges[edge]["weight"] = 0.25
    elif edge_mode_dict[edge] == "Ferry":
        Gr.edges[edge]["weight"] = 1

print("Graphs loaded....")
print(len(list(nx.connected_components(Gb))))

graph_metric_df = pd.DataFrame()

graph_metric_df["Graph"] = ["Multi", "Rapid", "Metro", "Ferry", "Bus"]

graph_metric_df["Nodes"] = [len(G.nodes()), len(Gr.nodes()), len(Gm.nodes()), len(Gf.nodes()), len(Gb.nodes())]
graph_metric_df["Edges"] = [len(G.edges()), len(Gr.nodes()), len(Gm.edges()), len(Gf.edges()), len(Gb.edges())]


print("Nodes, Edges added....")

def get_graph_degree(graph):
    dict_degree = dict(graph.degree())
    k = 0
    for key in dict_degree:
        k += dict_degree[key]
        
    return k/len(graph.nodes())

graph_metric_df["Degree"] = [get_graph_degree(G),get_graph_degree(Gr), get_graph_degree(Gm), get_graph_degree(Gf), get_graph_degree(Gb)]

print("Degree added....")

Cg = nx.average_clustering(G, weight= "weight")
Cgr = nx.average_clustering(Gr, weight= "weight")
Cgm = nx.average_clustering(Gm)
Cgf = nx.average_clustering(Gf)
Cgb = nx.average_clustering(Gb, weight = "weight")

print("Clustering added....")

#define fucntions to calculate the efficiency and path length to make it more efficient as the graph here is large
#calculate shortest path using networkx using floyd_warshall_numpy method
def calculate_efficiency_path_length(graph, weight):
    #get np array of shortest distance
    d_array = nx.floyd_warshall_numpy(graph, weight = weight)
    #sum of all shrtest path
    sum_d_array_paths = np.sum(d_array)
    # Diameter get max
    D = np.max(d_array)
    #handle zeros for same node pairs, replace with "inf" so that reciprocal will be 0
    d_array = np.where(d_array == 0, np.inf, d_array)
    #get distance resiprocal
    d_array_reciprocal = np.reciprocal(d_array)
    #sum of all reciprocals
    sum_d_reciprocal = np.sum(d_array_reciprocal)
    #number of nodes
    N = len(graph.nodes())
    #return efficiency metric
    return sum_d_reciprocal/(N*(N-1)), sum_d_array_paths/(N*(N-1)), D


#efficiency and path lengths
start_time = time.time()
print("calculating rapid graph efficiency, path length & diameter.........")
Efr, Lgr, Dgr = calculate_efficiency_path_length(Gr, "weight")
print("--- %s seconds ---" % (time.time() - start_time))

start_time = time.time()
print("calculating metro graph efficiency, path length & diameter.........")
Efm, Lgm, Dgm = calculate_efficiency_path_length(Gm, None)
print("--- %s seconds ---" % (time.time() - start_time))

start_time = time.time()
print("calculating ferry graph efficiency, path length & diameter.........")
Eff, Lgf, Dgf = calculate_efficiency_path_length(Gf, None)
print("--- %s seconds ---" % (time.time() - start_time))

start_time = time.time()
print("calculating main graph efficiency, path length & diameter.........")
Ef, Lg, Dg = calculate_efficiency_path_length(G, "weight")
print("--- %s seconds ---" % (time.time() - start_time))

start_time = time.time()
print("calculating bus graph efficiency, path length & diameter.........")
Efb, Lgb, Dgb = calculate_efficiency_path_length(Gb, "weight")
print("--- %s seconds ---" % (time.time() - start_time))


graph_metric_df["Path Length"] = [Lg, Lgr, Lgm, Lgf, Lgb]

print("Path length added....")

graph_metric_df["Diameter"] = [Dg, Dgr, Dgm, Dgf, Dgb]

print("Diameter added....")
#clustering added to df later to maintain sequence similar to AT
graph_metric_df["Clustering Coefficient"] = [Cg, Cgr, Cgm, Cgf, Cgb]

graph_metric_df["Efficiency"] = [Ef, Efr, Efm, Eff, Efb]

print("Efficiency added....")
    
graph_metric_df.to_excel("SYD_graphs Metrics.xlsx") 