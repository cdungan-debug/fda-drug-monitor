"""  
Physician Identity Mapping using Graph Algorithms

This script explores how Dijkstra's algorithm and other graph  
algorithms can be used to map relationships between physicians,  
drugs, specialties, and locations for the FDA drug approval  
notification system.

Algorithms explored:  
1. Dijkstra's Algorithm - Shortest path (closest relationship)  
2. BFS - All connections within N degrees  
3. PageRank - Most influential/important nodes  
4. Community Detection - Natural groupings  
"""

import json  
from collections import defaultdict  
import heapq


# ============================================================  
# PART 1: BUILD THE PHYSICIAN RELATIONSHIP GRAPH  
# ============================================================

class PhysicianGraph:  
    """  
    A graph representing relationships between doctors, drugs,  
    specialties, hospitals, and locations.

    This is an adjacency list implementation with weighted,  
    typed edges.  
    """

    def __init__(self):  
        # Adjacency list: node -> [(neighbor, weight, relationship_type)]  
        self.graph = defaultdict(list)  
        self.node_types = {}  # node_id -> type (doctor, drug, specialty, etc.)  
        self.node_data = {}   # node_id -> metadata dict

    def add_node(self, node_id, node_type, **metadata):  
        """Add a node to the graph."""  
        self.node_types[node_id] = node_type  
        self.node_data[node_id] = metadata

    def add_edge(self, node1, node2, weight=1, relationship="CONNECTED_TO"):  
        """Add a weighted, typed edge between two nodes."""  
        self.graph[node1].append((node2, weight, relationship))  
        self.graph[node2].append((node1, weight, relationship))

    def get_neighbors(self, node):  
        """Get all neighbors of a node."""  
        return self.graph.get(node, [])

    def get_nodes_by_type(self, node_type):  
        """Get all nodes of a specific type."""  
        return [  
            node_id for node_id, ntype in self.node_types.items()  
            if ntype == node_type  
        ]

    # ========================================================  
    # ALGORITHM 1: DIJKSTRA'S ALGORITHM  
    # ========================================================

    def dijkstra(self, source):  
        """  
        Dijkstra's Algorithm - Find shortest paths from source  
        to all other nodes.

        This answers: "How closely related is each doctor to  
        this drug/specialty/indication?"

        Time Complexity: O((V + E) log V)

        Returns:  
            distances: dict of node -> shortest distance  
            predecessors: dict of node -> previous node in path  
        """  
        distances = {node: float('infinity') for node in self.node_types}  
        distances[source] = 0  
        predecessors = {node: None for node in self.node_types}  
        visited = set()

        # Priority queue: (distance, node)  
        pq = [(0, source)]

        while pq:  
            current_dist, current_node = heapq.heappop(pq)

            if current_node in visited:  
                continue  
            visited.add(current_node)

            for neighbor, weight, rel_type in self.graph[current_node]:  
                if neighbor in visited:  
                    continue

                new_dist = current_dist + weight  
                if new_dist < distances[neighbor]:  
                    distances[neighbor] = new_dist  
                    predecessors[neighbor] = current_node  
                    heapq.heappush(pq, (new_dist, neighbor))

        return distances, predecessors

    def get_shortest_path(self, source, target):  
        """  
        Get the shortest path between two nodes using Dijkstra's.

        Returns:  
            path: list of nodes from source to target  
            distance: total weight of the path  
            relationships: list of relationship types along the path  
        """  
        distances, predecessors = self.dijkstra(source)

        if distances[target] == float('infinity'):  
            return None, float('infinity'), []

        # Reconstruct path  
        path = []  
        current = target  
        while current is not None:  
            path.append(current)  
            current = predecessors[current]  
        path.reverse()

        # Get relationship types along the path  
        relationships = []  
        for i in range(len(path) - 1):  
            for neighbor, weight, rel_type in self.graph[path[i]]:  
                if neighbor == path[i + 1]:  
                    relationships.append(rel_type)  
                    break

        return path, distances[target], relationships

    # ========================================================  
    # ALGORITHM 2: BFS - FIND ALL CONNECTIONS WITHIN N DEGREES  
    # ========================================================

    def bfs_within_degrees(self, source, max_degrees=3):  
        """  
        Breadth-First Search - Find all nodes within N degrees  
        of connection.

        This answers: "Who are ALL the doctors connected to this  
        drug within 3 relationship steps?"

        Time Complexity: O(V + E)

        Returns:  
            results: dict of degree -> list of (node, node_type)  
        """  
        visited = {source: 0}  
        queue = [(source, 0)]  
        results = defaultdict(list)

        while queue:  
            current_node, current_degree = queue.pop(0)

            if current_degree > max_degrees:  
                continue

            results[current_degree].append({  
                "node": current_node,  
                "type": self.node_types.get(current_node, "unknown"),  
                "data": self.node_data.get(current_node, {}),  
            })

            for neighbor, weight, rel_type in self.graph[current_node]:  
                if neighbor not in visited:  
                    visited[neighbor] = current_degree + 1  
                    queue.append((neighbor, current_degree + 1))

        return dict(results)

    # ========================================================  
    # ALGORITHM 3: PAGERANK - IMPORTANCE/INFLUENCE RANKING  
    # ========================================================

    def pagerank(self, damping=0.85, iterations=100, tolerance=1e-6):  
        """  
        PageRank Algorithm - Rank nodes by importance/influence.

        This answers: "Which doctors are most influential in  
        the network and should be contacted first?"

        The idea: A doctor is important if they are connected  
        to other important entities (hospitals, specialties,  
        other important doctors).

        Time Complexity: O(iterations * (V + E))

        Returns:  
            scores: dict of node -> PageRank score (sorted)  
        """  
        nodes = list(self.node_types.keys())  
        n = len(nodes)

        if n == 0:  
            return {}

        # Initialize all nodes with equal rank  
        scores = {node: 1.0 / n for node in nodes}

        for iteration in range(iterations):  
            new_scores = {}  
            max_diff = 0

            for node in nodes:  
                # Sum of (score / out_degree) for all incoming neighbors  
                rank_sum = 0  
                for other_node in nodes:  
                    for neighbor, weight, rel_type in self.graph[other_node]:  
                        if neighbor == node:  
                            out_degree = len(self.graph[other_node])  
                            if out_degree > 0:  
                                rank_sum += scores[other_node] / out_degree

                new_scores[node] = (1 - damping) / n + damping * rank_sum  
                max_diff = max(max_diff, abs(new_scores[node] - scores[node]))

            scores = new_scores

            # Check convergence  
            if max_diff < tolerance:  
                print(f"  PageRank converged after {iteration + 1} iterations")  
                break

        # Sort by score descending  
        sorted_scores = dict(  
            sorted(scores.items(), key=lambda x: x[1], reverse=True)  
        )  
        return sorted_scores

    # ========================================================  
    # ALGORITHM 4: FIND DOCTORS FOR A DRUG APPROVAL  
    # ========================================================

    def find_doctors_for_drug(self, drug_node, max_distance=5):  
        """  
        Combined approach: Use Dijkstra's to find all doctors  
        connected to a drug, then rank by distance (closeness  
        of relationship).

        This is the main function that would be used in the  
        FDA automation pipeline.

        Returns:  
            ranked_doctors: list of dicts with doctor info and  
                           relationship details  
        """  
        distances, predecessors = self.dijkstra(drug_node)

        doctors = []  
        for node, dist in distances.items():  
            if (self.node_types.get(node) == "doctor"  
                    and dist <= max_distance  
                    and dist < float('infinity')):

                # Get the path to understand the relationship  
                path, total_dist, relationships = self.get_shortest_path(  
                    drug_node, node  
                )

                doctors.append({  
                    "doctor_id": node,  
                    "doctor_data": self.node_data.get(node, {}),  
                    "relationship_distance": dist,  
                    "connection_path": path,  
                    "relationship_types": relationships,  
                })

        # Sort by distance (closest relationship first)  
        doctors.sort(key=lambda x: x["relationship_distance"])  
        return doctors


# ============================================================  
# PART 2: BUILD A SAMPLE GRAPH WITH NORTHWELL-LIKE DATA  
# ============================================================

def build_sample_graph():  
    """  
    Build a sample physician relationship graph that mimics  
    the Northwell Health ecosystem.

    This demonstrates how the graph structure works with  
    realistic healthcare data.  
    """  
    g = PhysicianGraph()

    # --- ADD SPECIALTIES ---  
    specialties = [  
        "Cardiology", "Oncology", "Neurology", "Dermatology",  
        "Pulmonology", "Rheumatology", "Ophthalmology",  
        "Gastroenterology", "Nephrology", "Endocrinology",  
    ]  
    for spec in specialties:  
        g.add_node(f"spec_{spec}", "specialty", name=spec)

    # --- ADD LOCATIONS ---  
    locations = [  
        ("loc_manhattan", "Manhattan, NY"),  
        ("loc_brooklyn", "Brooklyn, NY"),  
        ("loc_queens", "Queens, NY"),  
        ("loc_longisland", "Long Island, NY"),  
        ("loc_westchester", "Westchester, NY"),  
    ]  
    for loc_id, loc_name in locations:  
        g.add_node(loc_id, "location", name=loc_name)

    # --- ADD HOSPITALS ---  
    hospitals = [  
        ("hosp_lenox", "Lenox Hill Hospital", "loc_manhattan"),  
        ("hosp_lij", "Long Island Jewish Medical Center", "loc_longisland"),  
        ("hosp_nshore", "North Shore University Hospital", "loc_longisland"),  
        ("hosp_southside", "South Shore University Hospital", "loc_longisland"),  
        ("hosp_plainview", "Plainview Hospital", "loc_longisland"),  
    ]  
    for hosp_id, hosp_name, loc_id in hospitals:  
        g.add_node(hosp_id, "hospital", name=hosp_name)  
        g.add_edge(hosp_id, loc_id, weight=1, relationship="LOCATED_IN")

    # --- ADD DOCTORS ---  
    doctors = [  
        ("dr_smith", "Dr. Sarah Smith", "Cardiology", "hosp_lenox"),  
        ("dr_jones", "Dr. Michael Jones", "Cardiology", "hosp_lij"),  
        ("dr_patel", "Dr. Priya Patel", "Oncology", "hosp_nshore"),  
        ("dr_chen", "Dr. Wei Chen", "Oncology", "hosp_lenox"),  
        ("dr_williams", "Dr. James Williams", "Neurology", "hosp_lij"),  
        ("dr_garcia", "Dr. Maria Garcia", "Dermatology", "hosp_lenox"),  
        ("dr_kim", "Dr. Soo Kim", "Pulmonology", "hosp_nshore"),  
        ("dr_brown", "Dr. David Brown", "Rheumatology", "hosp_lij"),  
        ("dr_taylor", "Dr. Emily Taylor", "Ophthalmology", "hosp_lenox"),  
        ("dr_anderson", "Dr. Robert Anderson", "Nephrology", "hosp_nshore"),  
        ("dr_wilson", "Dr. Lisa Wilson", "Cardiology", "hosp_nshore"),  
        ("dr_martinez", "Dr. Carlos Martinez", "Gastroenterology", "hosp_lij"),  
        ("dr_lee", "Dr. Jennifer Lee", "Endocrinology", "hosp_lenox"),  
    ]  
    for doc_id, doc_name, spec, hosp in doctors:  
        g.add_node(doc_id, "doctor", name=doc_name,  
                   specialty=spec, hospital=hosp)  
        g.add_edge(doc_id, f"spec_{spec}", weight=1,  
                   relationship="SPECIALIZES_IN")  
        g.add_edge(doc_id, hosp, weight=1,  
                   relationship="WORKS_AT")

    # --- ADD DRUG INDICATIONS (What conditions drugs treat) ---  
    indications = [  
        ("ind_hypertension", "Hypertension", ["Cardiology", "Nephrology"]),  
        ("ind_cancer", "Cancer / Tumors", ["Oncology"]),  
        ("ind_seizures", "Seizures / Epilepsy", ["Neurology"]),  
        ("ind_acne", "Acne Vulgaris", ["Dermatology"]),  
        ("ind_asthma", "Severe Asthma", ["Pulmonology"]),  
        ("ind_arthritis", "Rheumatoid Arthritis", ["Rheumatology"]),  
        ("ind_glaucoma", "Glaucoma", ["Ophthalmology"]),  
        ("ind_malaria", "Malaria Prevention", ["Gastroenterology"]),  
        ("ind_osteoporosis", "Osteoporosis", ["Endocrinology", "Rheumatology"]),  
        ("ind_melanoma", "Melanoma", ["Oncology", "Dermatology"]),  
        ("ind_pah", "Pulmonary Arterial Hypertension",  
         ["Pulmonology", "Cardiology"]),  
        ("ind_hrs", "Hepatorenal Syndrome", ["Nephrology", "Gastroenterology"]),  
    ]  
    for ind_id, ind_name, related_specs in indications:  
        g.add_node(ind_id, "indication", name=ind_name)  
        for spec in related_specs:  
            g.add_edge(ind_id, f"spec_{spec}", weight=1,  
                       relationship="TREATED_BY_SPECIALTY")

    # --- ADD SAMPLE DRUG APPROVALS (From our FDA scraper) ---  
    drugs = [  
        ("drug_losartan", "LOSARTAN POTASSIUM", "ind_hypertension"),  
        ("drug_exdensur", "EXDENSUR (Depemokimab)", "ind_asthma"),  
        ("drug_opdualag", "OPDUALAG", "ind_melanoma"),  
        ("drug_terlivaz", "TERLIVAZ (Terlipressin)", "ind_hrs"),  
        ("drug_macitentan", "MACITENTAN", "ind_pah"),  
        ("drug_voranigo", "VORANIGO (Vorasidenib)", "ind_cancer"),  
        ("drug_oxcarbazepine", "OXCARBAZEPINE", "ind_seizures"),  
        ("drug_clindamycin", "CLINDAMYCIN PHOSPHATE", "ind_acne"),  
        ("drug_risedronate", "RISEDRONATE SODIUM", "ind_osteoporosis"),  
        ("drug_dorzolamide", "DORZOLAMIDE HYDROCHLORIDE", "ind_glaucoma"),  
        ("drug_risperidone", "RISPERIDONE", "ind_seizures"),  
        ("drug_malarone", "MALARONE PEDIATRIC", "ind_malaria"),  
    ]  
    for drug_id, drug_name, indication in drugs:  
        g.add_node(drug_id, "drug", name=drug_name)  
        g.add_edge(drug_id, indication, weight=1,  
                   relationship="INDICATED_FOR")

    # --- ADD DOCTOR-TO-DOCTOR RELATIONSHIPS ---  
    # (Referral networks, co-authors, same practice group)  
    doctor_connections = [  
        ("dr_smith", "dr_jones", 2, "SAME_SPECIALTY"),  
        ("dr_smith", "dr_wilson", 2, "SAME_SPECIALTY"),  
        ("dr_jones", "dr_wilson", 2, "SAME_SPECIALTY"),  
        ("dr_patel", "dr_chen", 2, "SAME_SPECIALTY"),  
        ("dr_smith", "dr_anderson", 3, "REFERRAL_NETWORK"),  
        ("dr_kim", "dr_smith", 3, "REFERRAL_NETWORK"),  
        ("dr_brown", "dr_lee", 3, "REFERRAL_NETWORK"),  
        ("dr_patel", "dr_garcia", 3, "CO_AUTHOR"),  
    ]  
    for doc1, doc2, weight, rel in doctor_connections:  
        g.add_edge(doc1, doc2, weight=weight, relationship=rel)

    return g


# ============================================================  
# PART 3: DEMONSTRATE EACH ALGORITHM  
# ============================================================

def main():  
    """Run all algorithm demonstrations."""  
    print("=" * 70)  
    print("PHYSICIAN IDENTITY MAPPING — GRAPH ALGORITHM EXPLORATION")  
    print("=" * 70)  
    print()

    # Build the graph  
    g = build_sample_graph()  
    print(f"Graph built with:")  
    print(f"  {len(g.node_types)} nodes")  
    edge_count = sum(len(edges) for edges in g.graph.values()) // 2  
    print(f"  {edge_count} edges")  
    print(f"  Node types: {set(g.node_types.values())}")  
    print()

    # ----------------------------------------------------------  
    # DEMO 1: DIJKSTRA'S ALGORITHM  
    # "Which doctors are most closely connected to LOSARTAN?"  
    # ----------------------------------------------------------  
    print("=" * 70)  
    print("ALGORITHM 1: DIJKSTRA'S SHORTEST PATH")  
    print("Question: Which doctors are most closely connected")  
    print("          to the new LOSARTAN POTASSIUM approval?")  
    print("=" * 70)  
    print()

    doctors = g.find_doctors_for_drug("drug_losartan")  
    for i, doc in enumerate(doctors, 1):  
        data = doc["doctor_data"]  
        path_str = " → ".join(doc["connection_path"])  
        rels_str = " → ".join(doc["relationship_types"])  
        print(f"  #{i} {data.get('name', 'Unknown')}")  
        print(f"     Specialty: {data.get('specialty', 'Unknown')}")  
        print(f"     Hospital:  {data.get('hospital', 'Unknown')}")  
        print(f"     Distance:  {doc['relationship_distance']}")  
        print(f"     Path:      {path_str}")  
        print(f"     Via:       {rels_str}")  
        print()

    # ----------------------------------------------------------  
    # DEMO 2: DIJKSTRA'S FOR OPDUALAG (Melanoma — crosses specialties)  
    # ----------------------------------------------------------  
    print("=" * 70)  
    print("ALGORITHM 1b: DIJKSTRA'S — CROSS-SPECIALTY EXAMPLE")  
    print("Question: Which doctors should know about OPDUALAG")  
    print("          (melanoma drug — involves Oncology AND Dermatology)?")  
    print("=" * 70)  
    print()

    doctors = g.find_doctors_for_drug("drug_opdualag")  
    for i, doc in enumerate(doctors, 1):  
        data = doc["doctor_data"]  
        path_str = " → ".join(doc["connection_path"])  
        rels_str = " → ".join(doc["relationship_types"])  
        print(f"  #{i} {data.get('name', 'Unknown')}")  
        print(f"     Specialty: {data.get('specialty', 'Unknown')}")  
        print(f"     Distance:  {doc['relationship_distance']}")  
        print(f"     Path:      {path_str}")  
        print(f"     Via:       {rels_str}")  
        print()

    # ----------------------------------------------------------  
    # DEMO 3: BFS — ALL CONNECTIONS WITHIN 3 DEGREES  
    # ----------------------------------------------------------  
    print("=" * 70)  
    print("ALGORITHM 2: BREADTH-FIRST SEARCH (BFS)")  
    print("Question: What entities are within 3 relationship")  
    print("          steps of EXDENSUR (severe asthma drug)?")  
    print("=" * 70)  
    print()

    connections = g.bfs_within_degrees("drug_exdensur", max_degrees=3)  
    for degree, nodes in sorted(connections.items()):  
        print(f"  Degree {degree}:")  
        for node_info in nodes:  
            node_type = node_info["type"]  
            node_name = node_info["data"].get("name", node_info["node"])  
            print(f"    [{node_type.upper()}] {node_name}")  
        print()

    # ----------------------------------------------------------  
    # DEMO 4: PAGERANK — MOST INFLUENTIAL NODES  
    # ----------------------------------------------------------  
    print("=" * 70)  
    print("ALGORITHM 3: PAGERANK")  
    print("Question: Which entities are most influential/central")  
    print("          in the physician network?")  
    print("=" * 70)  
    print()

    scores = g.pagerank()  
    print("  Top 15 most influential nodes:")  
    print()  
    for i, (node, score) in enumerate(list(scores.items())[:15], 1):  
        node_type = g.node_types.get(node, "unknown")  
        node_name = g.node_data.get(node, {}).get("name", node)  
        print(f"  #{i:2d} [{node_type.upper():10s}] {node_name:40s} "  
              f"Score: {score:.6f}")

    print()

    # ----------------------------------------------------------  
    # DEMO 5: SPECIFIC PATH ANALYSIS  
    # ----------------------------------------------------------  
    print("=" * 70)  
    print("ALGORITHM 4: PATH ANALYSIS")  
    print("Question: What is the exact relationship path between")  
    print("          VORANIGO (cancer drug) and Dr. Garcia (Dermatologist)?")  
    print("=" * 70)  
    print()

    path, distance, relationships = g.get_shortest_path(  
        "drug_voranigo", "dr_garcia"  
    )

    if path:  
        print(f"  Total distance: {distance}")  
        print(f"  Path:")  
        for i, node in enumerate(path):  
            node_type = g.node_types.get(node, "unknown")  
            node_name = g.node_data.get(node, {}).get("name", node)  
            prefix = "  START → " if i == 0 else "       → "  
            if i == len(path) - 1:  
                prefix = "    END → "  
            print(f"  {prefix}[{node_type}] {node_name}")  
            if i < len(relationships):  
                print(f"            ↓  ({relationships[i]})")  
    print()

    # ----------------------------------------------------------  
    # COMPARISON: DIJKSTRA'S vs ALTERNATIVES  
    # ----------------------------------------------------------  
    print("=" * 70)  
    print("ALGORITHM COMPARISON FOR PHYSICIAN IDENTITY MAPPING")  
    print("=" * 70)  
    print()  
    print("  Algorithm          | Best For                    | Limitation")  
    print("  " + "-" * 66)  
    print("  Dijkstra's         | Single shortest path        | "  
          "One source at a time")  
    print("  BFS                | All connections within N    | "  
          "Ignores edge weights")  
    print("  PageRank           | Ranking by importance       | "  
          "Doesn't find paths")  
    print("  Community Detection| Finding doctor clusters     | "  
          "Doesn't rank individuals")  
    print("  Knowledge Graph    | Typed relationships         | "  
          "More complex to build")  
    print()  
    print("  RECOMMENDATION: Hybrid approach using Knowledge Graph")  
    print("  structure (what we built above) with Dijkstra's for")  
    print("  path-finding and PageRank for priority ranking.")  
    print()

    # Save results  
    results = {  
        "graph_stats": {  
            "total_nodes": len(g.node_types),  
            "total_edges": edge_count,  
            "node_types": list(set(g.node_types.values())),  
        },  
        "losartan_doctors": [  
            {  
                "name": d["doctor_data"].get("name"),  
                "specialty": d["doctor_data"].get("specialty"),  
                "distance": d["relationship_distance"],  
                "path": d["connection_path"],  
            }  
            for d in g.find_doctors_for_drug("drug_losartan")  
        ],  
        "algorithm_comparison": {  
            "dijkstra": "Best for finding closest doctor to a drug",  
            "bfs": "Best for finding all related doctors",  
            "pagerank": "Best for ranking doctors by importance",  
            "recommendation": "Hybrid approach combining all three",  
        },  
    }

    with open("graph_analysis_results.json", "w") as f:  
        json.dump(results, f, indent=2)  
    print("Results saved to graph_analysis_results.json")


if __name__ == "__main__":  
    main()  
