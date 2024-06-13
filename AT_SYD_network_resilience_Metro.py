#import relevant libraries
import networkx as nx
from tqdm import tqdm
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from haversine import haversine, Unit
from itertools import combinations
import numpy as np
import matplotlib.pyplot as plt

#add graph pickel file     
graph_path = "ATgraph.pkl"  
graph_metro_path = "ATMetrograph.pkl"  
syd_metro_graph_path = "../Sydney/New/SYDMetrograph.pkl"

with open(graph_path, "rb") as g:
    G = pickle.load(g)
    
with open(graph_metro_path, "rb") as g:
    Gm = pickle.load(g)

with open(syd_metro_graph_path, "rb") as g:
    Gsm = pickle.load(g)
    
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
progress_bar = tqdm(total = len(list(combinations(G.nodes(), 2))), desc = "Adding Walking Transsfers")

mode_1 = ["Metro"]
mode_2 = ["Metro", "Ferry", "Bus Express", "Bus LVL1", "Bus LVL2"]

pos_dict = nx.get_node_attributes(Gn, "pos")
mode_dict = nx.get_node_attributes(Gn, "mode")
#start iterations
for s1, s2 in combinations(Gn.nodes(), 2):
    pos1 = pos_dict[s1]
    pos2 = pos_dict[s2]
    mode1 = mode_dict[s1]
    mode2 = mode_dict[s2]
    if mode1 in mode_1 and mode2 in mode_2 and mode1 != mode2:
        distance = haversine(pos1[::-1], pos2[::-1], unit = "m")
    
        if distance <= max_walk_distance:
            if not Gn.has_edge(s1, s2):
                Gn.add_edge(s1, s2, mode = "Walk", color = "yellow", weight = 2)

    progress_bar.update(1)
#close progress bar
progress_bar.close()

    
print(len(Gn.nodes()))
print(len(Gn.edges()))

Gnm = Gn.copy()

for node in Gn.nodes():
    if mode_dict[node] != "Metro":
        Gnm.remove_node(node)

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

#function for attacks
def random_attack(Graph, num_nodes):
    nodes_to_remove = random.sample(list(Graph.nodes()), num_nodes)
    Graph.remove_nodes_from(nodes_to_remove)
    
#function for trageted degree based attack
def target_degree_attack(Graph, num_nodes):
    degree_based_nodes = sorted(Graph.degree(), key = lambda x : x[1], reverse = True)
    nodes_to_remove = [node for node, _ in degree_based_nodes[:num_nodes]]
    Graph.remove_nodes_from(nodes_to_remove)
    
#function for trageted betweenness centrality based attack
def target_centrality_attack(Graph, num_nodes):
    centrality_based_nodes = sorted(nx.betweenness_centrality(Graph, weight= "weight").items(), key = lambda x : x[1], reverse = True)
    nodes_to_remove = [node for node,_ in centrality_based_nodes[:num_nodes]]
    Graph.remove_nodes_from(nodes_to_remove)

#define largest connected network size     
def get_LCC_size(Graph):
    if len(Graph) == 0: 
        return 0 
    LCC = max(list(nx.connected_components(Graph)), key = len)
    return len(LCC)
#random attack
def run_random_attack_simulations(graph, num_nodes):
    graph_copy = graph.copy()
    
    lcc_list = [100]
    eff_list = [100]
    
    steps = 20
    progress_bar = tqdm(total = steps, desc = f"{graph} random attack in Progress")
    for step in range(steps):
        if step == 19:
            lcc_list.append(0)
            eff_list.append(0)
        else:
            random_attack(graph_copy, num_nodes)
            lcc = (get_LCC_size(graph_copy)/len(graph.nodes()))*100
            eff = (calculate_efficiency(graph_copy, "weight")/EF_dict[graph])*100
            print(f"{step + 1} lcc = {lcc}%, eff = {eff}%")
            lcc_list.append(lcc)
            eff_list.append(eff)
        progress_bar.update(1)
        
    progress_bar.close()
    return lcc_list, eff_list

#target degree attack 
def run_target_degree_attack_simulations(graph, num_nodes):
    graph_copy = graph.copy()
    
    lcc_list = [100]
    eff_list = [100]
    
    steps = 20
    progress_bar = tqdm(total = steps, desc = f"{graph} target degree attacks in Progress")
    for step in range(steps):
        if step == 19:
            lcc_list.append(0)
            eff_list.append(0)
        else:
            target_degree_attack(graph_copy, num_nodes)
            lcc = (get_LCC_size(graph_copy)/len(graph.nodes()))*100
            eff = (calculate_efficiency(graph_copy, "weight")/EF_dict[graph])*100
            print(f"{step + 1} lcc = {lcc}%, eff = {eff}%")
            lcc_list.append(lcc)
            eff_list.append(eff)
        progress_bar.update(1)
        
    progress_bar.close()
    return lcc_list, eff_list

#target centrality attack 
def run_target_centrality_attack_simulations(graph, num_nodes):
    graph_copy = graph.copy()
    
    lcc_list = [100]
    eff_list = [100]
    
    steps = 20
    progress_bar = tqdm(total = steps, desc = f"{graph} target centrality attacks in Progress")
    for step in range(steps):
        if step == 19:
            lcc_list.append(0)
            eff_list.append(0)
        else:
            target_centrality_attack(graph_copy, num_nodes)
            lcc = (get_LCC_size(graph_copy)/len(graph.nodes()))*100
            eff = (calculate_efficiency(graph_copy, "weight")/EF_dict[graph])*100
            print(f"{step + 1} lcc = {lcc}%, eff = {eff}%")
            lcc_list.append(lcc)
            eff_list.append(eff)
        progress_bar.update(1)
        
    progress_bar.close()
    return lcc_list, eff_list



#efficiency for metro network
Efm = calculate_efficiency(Gm, "weight")
print(f"Multimodal = {Efm}")

#efficiency for whole metro with CRL
Efnm = calculate_efficiency(Gnm, "weight")
print(f"Multimodal CRL = {Efnm}")

#efficiency for mrteo sydney
Efsm = calculate_efficiency(Gsm, "weight")
print(f"Multimodal Sydney = {Efsm}")

graph_size_dict = {Gm: len(Gm.nodes()), Gnm: len(Gnm.nodes()), Gsm: len(Gsm.nodes())}
EF_dict = {Gm: Efm, Gnm: Efnm, Gsm: Efsm}

num_nodes_remove_Gm = int(len(Gm.nodes()) * 5/100)
num_nodes_remove_Gnm = int(len(Gnm.nodes()) * 5/100)
num_nodes_remove_Gsm = int(len(Gsm.nodes()) * 5/100)





Gm_random_lcc, Gm_random_eff = run_random_attack_simulations(Gm, num_nodes_remove_Gm)
Gnm_random_lcc, Gnm_random_eff = run_random_attack_simulations(Gnm, num_nodes_remove_Gnm)
Gsm_random_lcc, Gsm_random_eff = run_random_attack_simulations(Gsm, num_nodes_remove_Gsm)

Gm_target_degree_lcc, Gm_target_degree_eff = run_target_degree_attack_simulations(Gm, num_nodes_remove_Gm)
Gnm_target_degree_lcc, Gnm_target_degree_eff = run_target_degree_attack_simulations(Gnm, num_nodes_remove_Gnm)
Gsm_target_degree_lcc, Gsm_target_degree_eff = run_target_degree_attack_simulations(Gsm, num_nodes_remove_Gsm)

percentages = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50 ,55, 60, 65, 70, 75, 80, 85, 90, 95, 100]


#plot results
fig = plt.figure(figsize = (15, 10))
axes1 = fig.add_subplot(1, 2, 1)
axes2 = fig.add_subplot(1, 2, 2)





axes1.set_ylabel("Largest Connected Network (%)")
axes1.set_xlabel("Percentage of network removed (%)")
axes1.plot(percentages, Gm_random_lcc, "o--r", label= "Random Attack - AKL")
axes1.plot(percentages, Gm_target_degree_lcc, "v--c", label= "Target Degree based attack - AKL")
axes1.plot(percentages, Gnm_random_lcc, "o:g", label= "Random Attack - AKL with CRL")
axes1.plot(percentages, Gnm_target_degree_lcc, "v:m", label= "Target Degree based attack - AKL with CRL")
axes1.plot(percentages, Gsm_random_lcc, "o-b", label= "Random Attack - SYD")
axes1.plot(percentages, Gsm_target_degree_lcc, "v-y", label= "Target Degree based attack - SYD")
axes1.legend()

axes2.set_ylabel("Network Efficiency (%)")
axes2.set_xlabel("Percentage of network removed (%)")
axes2.plot(percentages, Gm_random_eff, "o--r", label= "Random Attack - AKL")
axes2.plot(percentages, Gm_target_degree_eff, "v--c", label= "Target Degree based attack - AKL")
axes2.plot(percentages, Gnm_random_eff, "o:g", label= "Random Attack - AKL with CRL")
axes2.plot(percentages, Gnm_target_degree_eff, "v:m", label= "Target Degree based attack - AKL with CRL")
axes2.plot(percentages, Gsm_random_eff, "o-b", label= "Random Attack - SYD")
axes2.plot(percentages, Gsm_target_degree_eff, "v-y", label= "Target Degree based attack - SYD")
axes2.legend()

plt.show()