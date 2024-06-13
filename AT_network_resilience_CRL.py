#import relevant libraries
import networkx as nx
import pandas as pd
from tqdm import tqdm
import numpy as np
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from haversine import haversine, Unit
from itertools import combinations

#add graph pickel file     
graph_path = "ATgraph.pkl"  
graph_metro_path = "ATMetrograph.pkl" 
graph_ferry_path = "ATFerrygraph.pkl"
graph_bus_path = "ATBusgraph.pkl"

with open(graph_path, "rb") as g:
    G = pickle.load(g)

print(len(G.nodes()))
print(len(G.edges()))

#Add CRL nodes, remove edge between kingland and grafto to add Mt Eden in between
#(-36.850625, 174.762764) Te Waihorotiu Station
#(-36.858519, 174.758777) K Road Station
#(-36.867721, 174.758437) Maungawhau Station
#Grafton_Kingland_edge = ('277-dfb27cf9', '122-34ecc043')

G.remove_edge('277-dfb27cf9', '122-34ecc043')

G.add_node("Te Waihorotiu Station", name = "Te Waihorotiu Station", pos = (174.762764, -36.850625), mode = "Metro", weight = 0.1)
G.add_node("K Road Station", name = "K Road Station", pos = (174.758777, -36.858519), mode = "Metro", weight = 0.1)
G.add_node("Maungawhau Station", name = "Maungawhau Station", pos = (174.758437, -36.867721), mode = "Metro", weight = 0.1)
#add edges for mt eden and grafton/kingland
G.add_edge('277-dfb27cf9', "Maungawhau Station", mode = "Metro", color = "red", weight = 0.1)
G.add_edge("Maungawhau Station", '122-34ecc043', mode = "Metro", color = "red", weight = 0.1)
#add CRL edges
G.add_edge('133-b84b56d3', "Te Waihorotiu Station", mode = "Metro", color = "red", weight = 0.1)
G.add_edge("Te Waihorotiu Station", "K Road Station", mode = "Metro", color = "red", weight = 0.1)
G.add_edge("K Road Station", "Maungawhau Station", mode = "Metro", color = "red", weight = 0.1)

#add walikng edges for new stations
#networkx has pos as (lon, lat), haversine needs (lat, lon), useing tuple[::-1]
#check and add walking transfer
max_walk_distance = 500
#initialise progress bar
progress_bar = tqdm(total = len(G.nodes()), desc = "Adding Walking Transsfers")

mode_1 = ["Metro"]
mode_2 = ["Metro", "Ferry", "Bus Express", "Bus LVL1", "Bus LVL2"]

pos_dict = nx.get_node_attributes(G, "pos")
mode_dict = nx.get_node_attributes(G, "mode")
#start iterations
for s1 in G.nodes():
    for s2 in G.nodes():
        if s1 != s2:
            pos1 = pos_dict[s1]
            pos2 = pos_dict[s2]
            mode1 = mode_dict[s1]
            mode2 = mode_dict[s2]
    
            distance = haversine(pos1[::-1], pos2[::-1], unit = "m")
    
            if distance <= max_walk_distance and mode1 in mode_1 and mode2 in mode_2 and mode1 != mode2:
                if not G.has_edge(s1, s2):
                    G.add_edge(s1, s2, mode = "Walk", color = "yellow", weight = 2)

    progress_bar.update(1)
#close progress bar
progress_bar.close()
    
print(len(G.nodes()))
print(len(G.edges()))

node_name_dict = nx.get_node_attributes(G, "name")
node_mode_dict = nx.get_node_attributes(G, "mode")

#only metro, ferry and busEx nodes are analysed for vulnarabilty, as these edges have least weight
modes_for_vunerability = ["Metro", "Ferry", "Bus Express"]

nodes_for_vulnerability_check = []
bus_1_and_2_nodes = []

for node in G.nodes():
    if node_mode_dict[node] in modes_for_vunerability:
        nodes_for_vulnerability_check.append(node)
    else:
        bus_1_and_2_nodes.append(node)


        
        
print(len(nodes_for_vulnerability_check))

#new rapid network graph
Gr = G.copy()
Gr.remove_nodes_from(bus_1_and_2_nodes)

#new metro network graph
Gm = Gr.copy()

remove_for_metro_graph = []
        
for node in nodes_for_vulnerability_check:
    if node_mode_dict[node] != "Metro":
        remove_for_metro_graph.append(node)
        
Gm.remove_nodes_from(remove_for_metro_graph)


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
start_time = time.time()
Ef = calculate_efficiency(G, "weight")
print(f"Multimodal = {Ef}")
print("--- %s seconds ---" % (time.time() - start_time))

#efficiency for rapid network
start_time = time.time()
Efr = calculate_efficiency(Gr, "weight")
print(f"Rapid = {Efr}")
print("--- %s seconds ---" % (time.time() - start_time))

#efficiency for metro network
start_time = time.time()
Efm = calculate_efficiency(Gm, 1)
print(f"Metro = {Efm}")
print("--- %s seconds ---" % (time.time() - start_time))


EF_dict = {G: Ef, Gr: Efr, Gm: Efm}



# Function to compute efficiency when removing a node
def compute_efficiency(args):
    node, graph, weight = args
    H = graph.copy()
    H.remove_node(node)
    return node, calculate_efficiency(H, weight)


def calculate_node_vunerability(graph, nodes, weight):
    
    # Create an empty dictionary for node and efficiency when it's removed
    efficiency_when_node_removed = {}

    # Use ThreadPoolExecutor for parallel computation
    with ThreadPoolExecutor() as ex:
        futures = [ex.submit(compute_efficiency, (node, graph, weight)) for node in nodes]

        #Intialise progress bar
        progress_bar = tqdm(total=len(nodes), desc="Calculating Efficiency")
        
        for future in as_completed(futures):
            node, efficiency = future.result()
            efficiency_when_node_removed[node] = efficiency
            progress_bar.update(1)
            
    Ef = EF_dict[graph]   
    #calculate node vulnerabilty, V = delta(E) = Ef - Ef1
    #create copy for dict for efficiency
    node_vulnerabilty = efficiency_when_node_removed.copy()
    #iterate over keys and edit values, new value is Ef1 - Ef = -V, then multiply by -1 
    for key in node_vulnerabilty:
        node_vulnerabilty[key] = Ef - node_vulnerabilty[key]
        
    node_vulnerabilty_df = pd.DataFrame(node_vulnerabilty.items(), columns = ["Node id", "Vunerabilty"])



    node_vulnerabilty_df["Robustness"] = node_vulnerabilty_df["Node id"].map(efficiency_when_node_removed)    
    node_vulnerabilty_df["Node Name"] = node_vulnerabilty_df["Node id"].map(node_name_dict)
    node_vulnerabilty_df["Mode"] = node_vulnerabilty_df["Node id"].map(node_mode_dict)

    node_vulnerabilty_df = node_vulnerabilty_df.sort_values("Vunerabilty", ascending = False)
    
    return node_vulnerabilty_df

AT_node_vulnerability_df = calculate_node_vunerability(G, nodes_for_vulnerability_check, "weight")
AT_rapid_node_vulnerability_df = calculate_node_vunerability(Gr, list(Gr.nodes()), "weight")
Metro_node_vulnerability_df = calculate_node_vunerability(Gm, list(Gm.nodes()), 1)


with pd.ExcelWriter("AT_CRL_Vulnerability & Robustness2.xlsx") as writer:
    AT_node_vulnerability_df.to_excel(writer, sheet_name = "Multimodal_CRL")
    AT_rapid_node_vulnerability_df.to_excel(writer, sheet_name = "Rapid_CRL")
    Metro_node_vulnerability_df.to_excel(writer, sheet_name = "Metro_CRL")


print(f"Multi = {Ef} \nRapid = {Efr} \nMetro = {Efm}")


