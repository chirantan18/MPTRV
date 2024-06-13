#import relevant libraries
import networkx as nx
import pandas as pd
from tqdm import tqdm
import numpy as np
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        
        
print(len(nodes_for_vulnerability_check), len(bus_1_and_2_nodes))

Gr = G.copy()
Gr.remove_nodes_from(bus_1_and_2_nodes)

#for bus graphs, express routes as well as nodes with degree more than 4 used
bus_nodes_for_vulnerability_check = []
for node in Gb.nodes():
    if node_mode_dict[node] in modes_for_vunerability:
        bus_nodes_for_vulnerability_check.append(node)
    elif Gb.degree(node) > 4:
        bus_nodes_for_vulnerability_check.append(node)
        
print(len(bus_nodes_for_vulnerability_check))

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

#efficiency for ferry network
start_time = time.time()
Eff = calculate_efficiency(Gf, 1)
print(f"Ferry = {Eff}")
print("--- %s seconds ---" % (time.time() - start_time))

#efficiency for bus network
start_time = time.time()
Efb = calculate_efficiency(Gb, "weight")
print(f"Bus = {Efb}")
print("--- %s seconds ---" % (time.time() - start_time))

EF_dict = {G: Ef, Gr: Efr, Gm: Efm, Gf: Eff, Gb: Efb}



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
Ferry_node_vulnerability_df = calculate_node_vunerability(Gf, list(Gf.nodes()), 1)
Bus_node_vulnerability_df = calculate_node_vunerability(Gb, bus_nodes_for_vulnerability_check, "weight")

with pd.ExcelWriter("AT_Vulnerability & Robustness.xlsx") as writer:
    AT_node_vulnerability_df.to_excel(writer, sheet_name = "Multimodal")
    AT_rapid_node_vulnerability_df.to_excel(writer, sheet_name = "Rapid")
    Metro_node_vulnerability_df.to_excel(writer, sheet_name = "Metro")
    Ferry_node_vulnerability_df.to_excel(writer, sheet_name = "Ferry")
    Bus_node_vulnerability_df.to_excel(writer, sheet_name = "Bus")

print(f"Multi = {Ef} \nRapid = {Efr} \nMetro = {Efm} \nFerry = {Eff} \nBus = {Efb}")


