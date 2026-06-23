import os
import networkx as nx
import osmnx as ox

def create_city_graph(DATA_BASE_DIR, city_name="Bangalore", network_type="drive"):
    """
    Checks for a locally saved GraphML file. If it exists, loads it instantly.
    Otherwise, downloads from OSM, processes metrics, and caches it to disk.
    """
    # Sanitize name for file system storage (e.g., "bangalore_drive.graphml")
    file_name = f"{city_name.lower().replace(' ', '_')}_{network_type}.graphml"
    file_path = os.path.join(DATA_BASE_DIR, file_name)

    # 1. Direct Load Strategy: If the processed graph exists on disk, load it immediately
    if os.path.exists(file_path):
        print(f"📂 Found cached map network at: {file_path}")
        print(f"🚀 Loading {city_name} topological matrix directly from disk...")
        try:
            G_projected = ox.load_graphml(file_path)
            
            # Unproject once upon loading to avoid expensive runtime projection conversion
            from pyproj import CRS
            crs = G_projected.graph.get("crs")
            if crs and CRS.from_user_input(crs).is_projected:
                print("🔄 Unprojecting loaded graph to GPS decimal degrees (lat/lng)...")
                G_projected = ox.project_graph(G_projected, to_latlong=True)
                
            print(f"✅ Loaded successfully! Nodes: {len(G_projected.nodes)} | Edges: {len(G_projected.edges)}")
            return G_projected
        except Exception as e:
            print(f"⚠️ Error loading cached file, falling back to download: {e}")

    # 2. Download Strategy: Runs if cache doesn't exist
    print(f"🌐 Cache miss. Querying OpenStreetMap geospatial bounds for: {city_name}...")
    try:
        # Ensure target database directory directory exists
        os.makedirs(DATA_BASE_DIR, exist_ok=True)

        query = f"{city_name}, India" if "india" not in city_name.lower() else city_name
        
        # Download raw topology
        G = ox.graph_from_place(query, network_type=network_type, retain_all=False)
        
        # Project coordinates to local UTM meters for accurate tracking
        G_projected = ox.project_graph(G)
        
        # Hydrate vectors with traffic attributes
        G_projected = ox.add_edge_speeds(G_projected)
        G_projected = ox.add_edge_travel_times(G_projected)
        
        # 3. Store to Database Dir: Cache the fully built graph for next system startup
        print(f"💾 Caching processed graph to disk at: {file_path}")
        ox.save_graphml(G_projected, filepath=file_path)
        
        # Unproject to return standard GPS lat/lng decimal degree graph
        G_projected = ox.project_graph(G_projected, to_latlong=True)
        print(f"✅ Setup complete. Nodes: {len(G_projected.nodes)} | Edges: {len(G_projected.edges)}")
        return G_projected

    except Exception as e:
        print(f"❌ Failed to build or store network matrix for '{city_name}': {str(e)}")
        return None

def shortest_path(G, source, destination, active_incidents=None):
    # Unproject the graph if it is in UTM/meters projection to ensure decimal degree computations
    from pyproj import CRS
    crs = G.graph.get("crs")
    is_proj = CRS.from_user_input(crs).is_projected if crs else False

    if is_proj:
        G_gps = ox.project_graph(G, to_latlong=True)
    else:
        G_gps = G

    # Copy graph to apply temporary penalties
    G_temp = G_gps.copy() if active_incidents else G_gps
    
    if active_incidents:
        import math
        # Apply heavy penalties to edges near other active incidents/traffic jams
        for incident in active_incidents:
            lat = incident.get("lat") or incident.get("mean_lat")
            lng = incident.get("lng") or incident.get("mean_lng") or incident.get("long")
            if lat is None or lng is None:
                continue
            
            try:
                lat_val = float(lat)
                lng_val = float(lng)
            except (ValueError, TypeError):
                continue
                
            # Iterate through edges and penalize those within ~400 meters (approx 0.004 degrees lat/lng)
            for u, v, k, data in G_temp.edges(keys=True, data=True):
                node_u = G_temp.nodes[u]
                edge_lat = node_u.get('y')
                edge_lng = node_u.get('x')
                if edge_lat and edge_lng:
                    dist = math.sqrt((edge_lat - lat_val)**2 + (edge_lng - lng_val)**2)
                    if dist < 0.004:
                        # Apply a 20x weight penalty to force the routing search to divert away
                        data["length"] = data.get("length", 1.0) * 20.0

    # 2. Get nearest nodes (OSMnx expects longitude X first, then latitude Y)
    start_node = ox.distance.nearest_nodes(G_temp, source[1], source[0])
    end_node = ox.distance.nearest_nodes(G_temp, destination[1], destination[0])

    # 3. Calculate shortest path node IDs
    route = nx.shortest_path(G_temp, source=start_node, target=end_node, weight="length")

    # 4. Extract the actual [Lat, Lng] coordinates from the node IDs for Leaflet
    route_coords = []
    for node in route:
        node_data = G_temp.nodes[node]
        # OSMnx nodes store 'y' as Latitude and 'x' as Longitude
        route_coords.append([node_data['y'], node_data['x']])

    return route_coords



if __name__ == "__main__":
    # source and destination as (lat, lng)
    source = (12.9716, 77.5946)
    destination = (12.9900, 77.6000)
    
    coords = shortest_path("Bangalore, Karnataka, India", source, destination)
    print(f"Generated {len(coords)} coordinates for the path.")
    print("Sample:", coords[:3]) # Prints the first few coordinates