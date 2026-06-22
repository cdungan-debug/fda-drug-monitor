"""  
Generate a visual graph diagram of the physician  
relationship network as an HTML file that can be  
opened in any browser.

No external libraries needed - generates pure HTML/JS  
using vis.js from CDN.  
"""

import json


def generate_graph_html():  
    """Build an interactive graph visualization."""

    # Define all nodes with colors by type  
    nodes = []  
    edges = []

    # Color scheme by node type  
    colors = {  
        "doctor": "#4CAF50",  
        "specialty": "#2196F3",  
        "hospital": "#FF9800",  
        "location": "#9C27B0",  
        "drug": "#F44336",  
        "indication": "#FFC107",  
    }

    shapes = {  
        "doctor": "dot",  
        "specialty": "diamond",  
        "hospital": "square",  
        "location": "triangle",  
        "drug": "star",  
        "indication": "hexagon",  
    }

    # --- SPECIALTIES ---  
    specialties = [  
        "Cardiology", "Oncology", "Neurology",  
        "Dermatology", "Pulmonology", "Rheumatology",  
        "Ophthalmology", "Gastroenterology",  
        "Nephrology", "Endocrinology",  
    ]  
    for spec in specialties:  
        nodes.append({  
            "id": "spec_" + spec,  
            "label": spec,  
            "group": "specialty",  
            "color": colors["specialty"],  
            "shape": shapes["specialty"],  
            "size": 25,  
            "font": {"size": 14, "color": "#333"},  
        })

    # --- HOSPITALS ---  
    hospitals = [  
        ("hosp_lenox", "Lenox Hill\nHospital", "loc_manhattan"),  
        ("hosp_lij", "LIJ Medical\nCenter", "loc_longisland"),  
        ("hosp_nshore", "North Shore\nUniversity", "loc_longisland"),  
    ]  
    for hid, hname, lid in hospitals:  
        nodes.append({  
            "id": hid,  
            "label": hname,  
            "group": "hospital",  
            "color": colors["hospital"],  
            "shape": shapes["hospital"],  
            "size": 22,  
            "font": {"size": 12, "color": "#333"},  
        })

    # --- LOCATIONS ---  
    locations = [  
        ("loc_manhattan", "Manhattan"),  
        ("loc_longisland", "Long Island"),  
    ]  
    for lid, lname in locations:  
        nodes.append({  
            "id": lid,  
            "label": lname,  
            "group": "location",  
            "color": colors["location"],  
            "shape": shapes["location"],  
            "size": 20,  
            "font": {"size": 12, "color": "#333"},  
        })

    # Hospital to location edges  
    for hid, hname, lid in hospitals:  
        edges.append({  
            "from": hid, "to": lid,  
            "label": "LOCATED_IN",  
            "color": {"color": "#999"},  
            "font": {"size": 9, "color": "#999"},  
        })

    # --- DOCTORS ---  
    doctors = [  
        ("dr_smith", "Dr. Smith\n(Cardiology)", "Cardiology",  
         "hosp_lenox"),  
        ("dr_jones", "Dr. Jones\n(Cardiology)", "Cardiology",  
         "hosp_lij"),  
        ("dr_patel", "Dr. Patel\n(Oncology)", "Oncology",  
         "hosp_nshore"),  
        ("dr_chen", "Dr. Chen\n(Oncology)", "Oncology",  
         "hosp_lenox"),  
        ("dr_williams", "Dr. Williams\n(Neurology)", "Neurology",  
         "hosp_lij"),  
        ("dr_garcia", "Dr. Garcia\n(Dermatology)", "Dermatology",  
         "hosp_lenox"),  
        ("dr_kim", "Dr. Kim\n(Pulmonology)", "Pulmonology",  
         "hosp_nshore"),  
        ("dr_brown", "Dr. Brown\n(Rheumatology)", "Rheumatology",  
         "hosp_lij"),  
        ("dr_taylor", "Dr. Taylor\n(Ophthalmology)",  
         "Ophthalmology", "hosp_lenox"),  
        ("dr_anderson", "Dr. Anderson\n(Nephrology)", "Nephrology",  
         "hosp_nshore"),  
        ("dr_wilson", "Dr. Wilson\n(Cardiology)", "Cardiology",  
         "hosp_nshore"),  
        ("dr_martinez", "Dr. Martinez\n(Gastro)", "Gastroenterology",  
         "hosp_lij"),  
        ("dr_lee", "Dr. Lee\n(Endocrinology)", "Endocrinology",  
         "hosp_lenox"),  
    ]  
    for did, dname, spec, hosp in doctors:  
        nodes.append({  
            "id": did,  
            "label": dname,  
            "group": "doctor",  
            "color": colors["doctor"],  
            "shape": shapes["doctor"],  
            "size": 18,  
            "font": {"size": 11, "color": "#333"},  
        })  
        edges.append({  
            "from": did, "to": "spec_" + spec,  
            "label": "SPECIALIZES_IN",  
            "color": {"color": "#4CAF50"},  
            "font": {"size": 8, "color": "#4CAF50"},  
            "dashes": False,  
        })  
        edges.append({  
            "from": did, "to": hosp,  
            "label": "WORKS_AT",  
            "color": {"color": "#FF9800"},  
            "font": {"size": 8, "color": "#FF9800"},  
            "dashes": True,  
        })

    # --- INDICATIONS ---  
    indications = [  
        ("ind_hypertension", "Hypertension",  
         ["Cardiology", "Nephrology"]),  
        ("ind_cancer", "Cancer",  
         ["Oncology"]),  
        ("ind_seizures", "Seizures",  
         ["Neurology"]),  
        ("ind_acne", "Acne",  
         ["Dermatology"]),  
        ("ind_asthma", "Severe Asthma",  
         ["Pulmonology"]),  
        ("ind_melanoma", "Melanoma",  
         ["Oncology", "Dermatology"]),  
        ("ind_pah", "Pulmonary Arterial\nHypertension",  
         ["Pulmonology", "Cardiology"]),  
        ("ind_hrs", "Hepatorenal\nSyndrome",  
         ["Nephrology", "Gastroenterology"]),  
        ("ind_osteoporosis", "Osteoporosis",  
         ["Endocrinology", "Rheumatology"]),  
        ("ind_glaucoma", "Glaucoma",  
         ["Ophthalmology"]),  
    ]  
    for iid, iname, related_specs in indications:  
        nodes.append({  
            "id": iid,  
            "label": iname,  
            "group": "indication",  
            "color": colors["indication"],  
            "shape": shapes["indication"],  
            "size": 20,  
            "font": {"size": 11, "color": "#333"},  
        })  
        for spec in related_specs:  
            edges.append({  
                "from": iid, "to": "spec_" + spec,  
                "label": "TREATED_BY",  
                "color": {"color": "#FFC107"},  
                "font": {"size": 8, "color": "#997700"},  
            })

    # --- DRUGS ---  
    drugs = [  
        ("drug_losartan", "LOSARTAN", "ind_hypertension"),  
        ("drug_exdensur", "EXDENSUR", "ind_asthma"),  
        ("drug_opdualag", "OPDUALAG", "ind_melanoma"),  
        ("drug_terlivaz", "TERLIVAZ", "ind_hrs"),  
        ("drug_macitentan", "MACITENTAN", "ind_pah"),  
        ("drug_voranigo", "VORANIGO", "ind_cancer"),  
        ("drug_oxcarbazepine", "OXCARBAZEPINE", "ind_seizures"),  
        ("drug_clindamycin", "CLINDAMYCIN", "ind_acne"),  
        ("drug_risedronate", "RISEDRONATE", "ind_osteoporosis"),  
        ("drug_dorzolamide", "DORZOLAMIDE", "ind_glaucoma"),  
    ]  
    for drid, drname, indication in drugs:  
        nodes.append({  
            "id": drid,  
            "label": drname,  
            "group": "drug",  
            "color": colors["drug"],  
            "shape": shapes["drug"],  
            "size": 22,  
            "font": {"size": 12, "color": "#333",  
                     "bold": True},  
        })  
        edges.append({  
            "from": drid, "to": indication,  
            "label": "INDICATED_FOR",  
            "color": {"color": "#F44336"},  
            "font": {"size": 8, "color": "#F44336"},  
            "width": 2,  
        })

    # --- DOCTOR-DOCTOR CONNECTIONS ---  
    doc_edges = [  
        ("dr_smith", "dr_jones", "SAME_SPECIALTY"),  
        ("dr_smith", "dr_wilson", "SAME_SPECIALTY"),  
        ("dr_patel", "dr_chen", "SAME_SPECIALTY"),  
        ("dr_smith", "dr_anderson", "REFERRAL"),  
        ("dr_patel", "dr_garcia", "CO_AUTHOR"),  
    ]  
    for d1, d2, rel in doc_edges:  
        edges.append({  
            "from": d1, "to": d2,  
            "label": rel,  
            "color": {"color": "#aaa"},  
            "font": {"size": 8, "color": "#aaa"},  
            "dashes": [5, 5],  
        })

    # Build HTML  
    nodes_json = json.dumps(nodes)  
    edges_json = json.dumps(edges)

    html = """<!DOCTYPE html>  
<html>  
<head>  
    <title>Physician Identity Mapping - Graph Visualization</title>  
    <script type="text/javascript"  
        src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js">  
    </script>  
    <style>  
        body {  
            margin: 0; padding: 0;  
            font-family: Arial, sans-serif;  
        }  
        #header {  
            background: linear-gradient(135deg, #0078d4, #00a4ef);  
            color: white; padding: 15px 25px;  
        }  
        #header h1 { margin: 0; font-size: 20px; }  
        #header p { margin: 5px 0 0 0; opacity: 0.9;  
                    font-size: 13px; }  
        #legend {  
            padding: 10px 25px;  
            background: #f8f9fa;  
            border-bottom: 1px solid #ddd;  
            display: flex; gap: 20px;  
            flex-wrap: wrap;  
            font-size: 13px;  
        }  
        .legend-item {  
            display: flex; align-items: center; gap: 6px;  
        }  
        .legend-dot {  
            width: 14px; height: 14px;  
            border-radius: 50%;  
            display: inline-block;  
        }  
        #graph {  
            width: 100%; height: calc(100vh - 120px);  
            border: none;  
        }  
        #info {  
            position: fixed; bottom: 10px; right: 10px;  
            background: white; border: 1px solid #ddd;  
            border-radius: 8px; padding: 12px 16px;  
            font-size: 12px; color: #666;  
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);  
            max-width: 300px;  
        }  
    </style>  
</head>  
<body>  
    <div id="header">  
        <h1>Physician Identity Mapping Graph</h1>  
        <p>Knowledge Graph showing relationships between  
           Drugs, Indications, Specialties, Doctors,  
           Hospitals, and Locations</p>  
    </div>  
    <div id="legend">  
        <div class="legend-item">  
            <span class="legend-dot"  
                  style="background:#F44336"></span>  
            Drugs  
        </div>  
        <div class="legend-item">  
            <span class="legend-dot"  
                  style="background:#FFC107"></span>  
            Indications  
        </div>  
        <div class="legend-item">  
            <span class="legend-dot"  
                  style="background:#2196F3"></span>  
            Specialties  
        </div>  
        <div class="legend-item">  
            <span class="legend-dot"  
                  style="background:#4CAF50"></span>  
            Doctors  
        </div>  
        <div class="legend-item">  
            <span class="legend-dot"  
                  style="background:#FF9800"></span>  
            Hospitals  
        </div>  
        <div class="legend-item">  
            <span class="legend-dot"  
                  style="background:#9C27B0"></span>  
            Locations  
        </div>  
    </div>  
    <div id="graph"></div>  
    <div id="info">  
        <strong>How to use:</strong><br>  
        - Drag nodes to rearrange<br>  
        - Scroll to zoom in/out<br>  
        - Click a node to highlight connections<br>  
        - Colored paths show relationship types<br>  
        <br>  
        <strong>Path example:</strong><br>  
        LOSARTAN (red star) → Hypertension (yellow)  
        → Cardiology (blue) → Dr. Smith (green)  
    </div>

    <script type="text/javascript">  
        var nodes = new vis.DataSet(NODES_DATA);  
        var edges = new vis.DataSet(EDGES_DATA);

        var container = document.getElementById("graph");  
        var data = { nodes: nodes, edges: edges };

        var options = {  
            physics: {  
                enabled: true,  
                solver: "forceAtlas2Based",  
                forceAtlas2Based: {  
                    gravitationalConstant: -40,  
                    centralGravity: 0.008,  
                    springLength: 120,  
                    springConstant: 0.02,  
                    damping: 0.4,  
                },  
                stabilization: {  
                    iterations: 200,  
                },  
            },  
            edges: {  
                smooth: {  
                    type: "continuous",  
                },  
                arrows: {  
                    to: { enabled: true, scaleFactor: 0.5 },  
                },  
                font: { align: "middle" },  
            },  
            nodes: {  
                borderWidth: 2,  
                shadow: true,  
            },  
            interaction: {  
                hover: true,  
                tooltipDelay: 200,  
                navigationButtons: true,  
            },  
        };

        var network = new vis.Network(  
            container, data, options  
        );

        network.on("click", function(params) {  
            if (params.nodes.length > 0) {  
                var nodeId = params.nodes[0];  
                var connected = network.getConnectedNodes(  
                    nodeId  
                );  
                var allNodes = nodes.get();  
                var updateArray = [];

                allNodes.forEach(function(node) {  
                    if (node.id === nodeId ||  
                        connected.indexOf(node.id) !== -1) {  
                        updateArray.push({  
                            id: node.id,  
                            opacity: 1.0,  
                        });  
                    } else {  
                        updateArray.push({  
                            id: node.id,  
                            opacity: 0.15,  
                        });  
                    }  
                });  
            }  
        });  
    </script>  
</body>  
</html>"""

    html = html.replace("NODES_DATA", nodes_json)  
    html = html.replace("EDGES_DATA", edges_json)

    with open("physician_graph.html", "w") as f:  
        f.write(html)

    print("Graph visualization saved to physician_graph.html")  
    print()  
    print("Graph contains:")  
    print("  " + str(len(nodes)) + " nodes")  
    print("  " + str(len(edges)) + " edges")  
    print()  
    print("Node types:")  
    print("  Red stars    = Drugs (FDA approvals)")  
    print("  Yellow hex   = Indications (what drugs treat)")  
    print("  Blue diamond = Specialties")  
    print("  Green dots   = Doctors")  
    print("  Orange sq    = Hospitals")  
    print("  Purple tri   = Locations")  
    print()  
    print("Download the artifact and open")  
    print("physician_graph.html in your browser to")  
    print("view the interactive graph.")


if __name__ == "__main__":  
    generate_graph_html()  
