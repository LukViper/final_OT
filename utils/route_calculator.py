import networkx as nx
import json
from math import radians, sin, cos, sqrt, atan2
import random
import time
import math
import os
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib
from utils.vessel_physics import vessel_physics
from utils.hull_fouling import hull_fouling
from utils.lunar_tides import lunar_tides
from utils.ocean_currents import ocean_currents

class ShippingRouteOptimizer:
    def __init__(self, seed=None):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.SEA_LANES_GEOJSON_PATH = os.path.join(current_dir, "../Shipping_Lanes_v1.geojson")
        
        print(f" Looking for GeoJSON at: {self.SEA_LANES_GEOJSON_PATH}")
        
        self.PORT_LOCATIONS = {
            "Jebel_Ali": (25.0108, 55.0610),
            "Mumbai": (18.948, 72.835),
            "Colombo": (6.9271, 79.8612),
            "Singapore": (1.3521, 103.8198),
            "Jakarta": (-6.2088, 106.8456),
            "Port Moresby": (-9.4790, 147.1494),
            "Kudat": (6.8831, 116.8466),
            "Bangkok": (13.7563, 100.5018),
            "Manila": (14.5995, 120.9842),
            "Hong_Kong": (22.3193, 114.1694),
            "Busan": (35.1796, 129.0756),
            "Shanghai": (31.2304, 121.4737),
            "Shenzhen": (22.5431, 114.0579),
            "Yokohama": (35.4437, 139.6380),
            "Palu": (0.9003, 119.8780),
            "Tokyo": (35.6762, 139.6503),
            "Melbourne": (-37.8136, 144.9631),
            "Perth": (-31.9514, 115.8617),
            "Suez_Canal": (30.5852, 32.2654),
            "Salalah": (16.9472, 54.0104),
        }
        
        # Vessel Profiles (Digital Twins)
        self.VESSEL_PROFILES = {
            "ULCC_Tanker": {
                "name": "Ultra Large Crude Carrier",
                "avg_speed_kmh": 26.0,  # ~14 knots
                "base_fuel_rate": 0.08,  # tonnes/km at avg speed
                "deadweight_tonnage": 320000,
                "admiralty_coefficient": 450,
                "weather_sensitivity": 1.4,  # High sensitivity due to mass/drag
            },
            "Container_Ship": {
                "name": "Panamax Container Ship",
                "avg_speed_kmh": 39.0,  # ~21 knots
                "base_fuel_rate": 0.05,
                "deadweight_tonnage": 65000,
                "admiralty_coefficient": 550,
                "weather_sensitivity": 1.1,
            },
            "Bulker": {
                "name": "Handysize Bulk Carrier",
                "avg_speed_kmh": 22.0,  # ~12 knots
                "base_fuel_rate": 0.03,
                "deadweight_tonnage": 35000,
                "admiralty_coefficient": 400,
                "weather_sensitivity": 1.2,
            }
        }
        
        # Default vessel settings
        self.current_vessel = self.VESSEL_PROFILES["Container_Ship"]
        self.AVERAGE_SPEED_KMH = self.current_vessel["avg_speed_kmh"]
        self.FUEL_CONSUMPTION_PER_KM = self.current_vessel["base_fuel_rate"]
        self.hull_days = 90  # Default days since cleaning
        self.departure_time = None
        # Emission Control Areas (ECA) — Simple bounding boxes for demo
        self.ECA_ZONES = [
            {"name": "North Sea/Baltic", "lat_range": (50, 65), "lon_range": (-5, 30), "cost_multiplier": 1.4},
            {"name": "US/Canada East Coast", "lat_range": (25, 55), "lon_range": (-85, -50), "cost_multiplier": 1.35},
            {"name": "US/Canada West Coast", "lat_range": (30, 60), "lon_range": (-130, -115), "cost_multiplier": 1.35}
        ]
        
        self.WEATHER_FACTOR = 1
        self.GA_POPULATION_SIZE = 40
        self.GA_GENERATIONS = 100
        self.PORT_CONNECTION_THRESHOLD_KM = 500
        
        # Seed for deterministic behavior
        self.seed = seed
        if self.seed is not None:
            random.seed(self.seed)
            self.deterministic_random = random.Random(self.seed)
        else:
            self.deterministic_random = random.Random(42)  # Default seed
        
        print(" Initializing Shipping Route Optimizer...")
        
        # Initialize graph and data structures once
        self.sea_graph = self._build_sea_graph()
        self._connect_ports_to_sea_nodes()
        self.port_paths = self._precompute_all_port_paths()
        
        # Initialize weather service as None (lazy loading)
        self.weather_service = None
        
        print(" Shipping Route Optimizer initialized successfully!")

    # ========== HELPER METHODS ==========
    def _get_deterministic_seed(self, start_port, destination_port, hub_ports, goal):
        """Generate a deterministic seed based on input parameters"""
        input_str = f"{start_port}_{destination_port}_{sorted(hub_ports)}_{goal}"
        return int(hashlib.md5(input_str.encode()).hexdigest()[:8], 16) % (2**31)

    # ========== 4D ROUTE OPTIMIZATION ==========
    def calculate_route_4d(self, start_port, destination_port, hub_ports=None, 
                          departure_time=None, speed_knots=20):
        """
        Calculate route with full 4D weather forecasting
        This is the journal-level method that considers weather at arrival times
        """
        if hub_ports is None:
            hub_ports = []
        
        if departure_time is None:
            departure_time = datetime.now()
        
        print("\n" + "="*70)
        print(" 4D ROUTE OPTIMIZATION (Time-Dependent)")
        print("="*70)
        print(f" Departure: {departure_time}")
        print(f" Speed: {speed_knots} knots")
        
        # Get route (use genetic algorithm for hub ports, direct if none)
        if hub_ports:
            route, distance = self._run_genetic_algorithm(
                start_port, destination_port, hub_ports, "fuel"
            )
        else:
            route = [start_port, destination_port]
            distance = self._total_distance(route)
        
        # Get coordinates
        coords = self._build_full_route_coordinates(route)
        
        # Try to import 4D forecast
        try:
            from utils.forecast_4d import forecast_4d
        except ImportError:
            print(" 4D forecast module not found. Install with: pip install requests numpy")
            # Fallback to simple forecast
            return self._calculate_route_fallback(start_port, destination_port, route, distance, coords, departure_time)
        
        # Get 4D timeline
        timeline = forecast_4d.route_timeline_4d(coords, departure_time, speed_knots)
        
        # Calculate fuel with time-dependent weather
        total_fuel_4d = 0
        total_fuel_static = 0
        
        for i, segment in enumerate(timeline['timeline']):
            seg_dist = segment['distance_km']
            forecast = segment['forecast']
            
            # Clean-hull Holtrop fuel. Fouling is applied once, to both columns.
            base_fuel = vessel_physics.fuel_consumption(seg_dist, speed_knots, 15.0)
            
            # Piecewise sea-state multiplier. Units follow the forecast module:
            # wind_speed is km/h in the climatological fallback.
            wind = forecast.get('wind_speed', 0) or 0
            wave = forecast.get('wave_height', 0) or 0
            
            if wind > 60 or wave > 5:
                weather_mult = 1.4  # Severe
            elif wind > 40 or wave > 3:
                weather_mult = 1.2  # Rough
            elif wind > 20 or wave > 1.5:
                weather_mult = 1.1  # Moderate
            else:
                weather_mult = 1.0  # Calm
            
            segment_fuel_4d = base_fuel * weather_mult
            total_fuel_4d += segment_fuel_4d
            
            # Calm-water baseline. A previous version compared against a
            # hardcoded 1.15 factor and reported the ratio as a saving,
            # including a fixed 15% when the forecast module was missing.
            total_fuel_static += base_fuel
        
        # Weather delta before fouling, so the two effects are not confounded.
        weather_delta = (total_fuel_static - total_fuel_4d) / total_fuel_static * 100 if total_fuel_static > 0 else 0
        water_temps = [28.0] * max(len(coords), 1)
        fouling = hull_fouling.calculate_fouling_penalty(
            self.hull_days, water_temps, [35.0] * max(len(coords), 1)
        )
        total_fuel_4d *= fouling["fuel_multiplier"]
        total_fuel_static *= fouling["fuel_multiplier"]
        fouling_penalty = fouling["total_penalty_percent"]
        
        print(f"\n 4D Results:")
        print(f"   Calm-water fuel:     {total_fuel_static:.1f} tonnes")
        print(f"   Weather-adjusted:    {total_fuel_4d:.1f} tonnes")
        print(f"   Calm-water delta:    {weather_delta:.1f}%")
        print(f"   Optimal departure:   {timeline.get('optimal_departure', departure_time.isoformat())}")
        print(f"   Confidence:          {timeline.get('ensemble_confidence', 0.5)*100:.0f}%")
        
        return {
            'route': route,
            'distance_km': distance,
            'timeline': timeline,
            'fuel_4d': round(total_fuel_4d, 1),
            'fuel_static': round(total_fuel_static, 1),
            'savings_percent': round(weather_delta, 1),
            'fouling_impact': fouling_penalty,
            'optimal_departure': timeline.get('optimal_departure', departure_time.isoformat()),
            'confidence': timeline.get('ensemble_confidence', 0.5)
        }

    def _calculate_route_fallback(self, start_port, destination_port, route, distance, coords, departure_time):
        """Fallback method if 4D forecast isn't available"""
        print(" Using simplified 4D calculation")
        
        calm = distance * self.FUEL_CONSUMPTION_PER_KM
        return {
            'route': route,
            'distance_km': distance,
            'fuel_4d': round(calm, 1),
            'fuel_static': round(calm, 1),
            'savings_percent': 0.0,
            'fouling_impact': 0,
            'optimal_departure': departure_time.isoformat(),
            'confidence': 0.0,
            'note': 'Forecast unavailable; calm-water rate only. No weather saving is implied.'
        }

    # ========== GRAPH BUILDING ==========
    def _build_sea_graph(self):
        """Build the sea graph from GeoJSON data"""
        sea_graph = nx.Graph()
        
        if not os.path.exists(self.SEA_LANES_GEOJSON_PATH):
            raise FileNotFoundError(f"GeoJSON file not found: {self.SEA_LANES_GEOJSON_PATH}")
        
        print(f" Loading GeoJSON from: {self.SEA_LANES_GEOJSON_PATH}")
        
        with open(self.SEA_LANES_GEOJSON_PATH, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        def make_sea_node_id(lat, lon):
            return f"sea_{lat:.6f}_{lon:.6f}"

        for feature in geojson_data.get("features", []):
            geometry = feature.get("geometry", {})
            typ = geometry.get("type")
            coords = geometry.get("coordinates", [])
            lines = []
            if typ == "LineString":
                lines.append(coords)
            elif typ == "MultiLineString":
                for line in coords:
                    lines.append(line)
            else:
                continue

            for line in lines:
                prev_node = None
                for lon, lat in line:
                    node_id = make_sea_node_id(lat, lon)
                    if node_id not in sea_graph:
                        sea_graph.add_node(node_id, coord=(lat, lon))
                    if prev_node is not None and not sea_graph.has_edge(prev_node, node_id):
                        coord_a = sea_graph.nodes[prev_node]["coord"]
                        coord_b = sea_graph.nodes[node_id]["coord"]
                        w = self._calculate_distance_km(coord_a, coord_b)
                        sea_graph.add_edge(prev_node, node_id, weight=w)
                    prev_node = node_id

        sea_nodes = len([n for n in sea_graph.nodes if str(n).startswith('sea_')])
        print(f" Built sea-graph with {sea_nodes} sea nodes and {len(list(sea_graph.edges))} edges")
        return sea_graph

    def _connect_ports_to_sea_nodes(self):
        """Connect ports to nearby sea nodes"""
        for pname, pcoord in self.PORT_LOCATIONS.items():
            self.sea_graph.add_node(pname, coord=pcoord)
            connected = []
            for node, data in list(self.sea_graph.nodes(data=True)):
                if not str(node).startswith("sea_"):
                    continue
                d = self._calculate_distance_km(pcoord, data["coord"])
                if d <= self.PORT_CONNECTION_THRESHOLD_KM:
                    self.sea_graph.add_edge(pname, node, weight=d)
                    connected.append(node)
            print(f" Port {pname} connected to {len(connected)} sea nodes.")

    def _precompute_all_port_paths(self):
        """Precompute paths between all ports for web use"""
        print(" Precomputing all port-to-port paths...")
        port_paths = {}
        ports = list(self.PORT_LOCATIONS.keys())
        
        total_combinations = len(ports) * (len(ports) - 1)
        current = 0
        
        for i in range(len(ports)):
            for j in range(len(ports)):
                if i == j:
                    continue
                port_paths[(ports[i], ports[j])] = self._astar_between(ports[i], ports[j])
                current += 1
                if current % 50 == 0:
                    print(f"  Progress: {current}/{total_combinations} paths computed")
        
        print(" Precompute done.")
        return port_paths

    def _calculate_distance_km(self, coord1, coord2):
        """Haversine distance in km between two (lat, lon) coordinates."""
        R = 6371.0
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        return 2 * R * atan2(sqrt(a), sqrt(1 - a))

    def _heuristic_distance(self, u, v):
        cu = self.sea_graph.nodes[u].get("coord")
        cv = self.sea_graph.nodes[v].get("coord")
        if cu is None or cv is None:
            return 0.0
        return self._calculate_distance_km(cu, cv)

    @lru_cache(maxsize=None)
    def _astar_between(self, u, v):
        """Run A* between two nodes in the sea graph and return (path_tuple, length)."""
        try:
            path = nx.astar_path(self.sea_graph, u, v, heuristic=self._heuristic_distance, weight="weight")
            length = nx.path_weight(self.sea_graph, path, weight="weight")
            return tuple(path), length
        except Exception as e:
            return None, float("inf")

    def _total_distance(self, port_sequence):
        """Sum of distances along a port sequence using precomputed port-to-port paths."""
        dist = 0.0
        for i in range(len(port_sequence) - 1):
            _, d = self.port_paths.get((port_sequence[i], port_sequence[i + 1]), (None, float("inf")))
            dist += d
        return dist

    def _estimate_travel_time_hours(self, distance_km):
        return (distance_km / self.AVERAGE_SPEED_KMH) * self.WEATHER_FACTOR

    def _estimate_fuel_tonnes(self, distance_km):
        return distance_km * self.FUEL_CONSUMPTION_PER_KM * self.WEATHER_FACTOR

    # ========== GENETIC ALGORITHM ==========
    def _fitness(self, route_seq, goal):
        """Compute fitness for GA - routes with ALL intermediate ports get priority."""
        if hasattr(self, 'current_hub_ports'):
            required_ports = set(self.current_hub_ports)
            actual_ports = set(route_seq[1:-1])  
            
            if not required_ports.issubset(actual_ports):
                return 0.0
        
        d = self._total_distance(route_seq)
        if d == float("inf"):
            return 0.0

        stops = len(route_seq) - 2  
        if goal == "fastest":
            time_hours = self._estimate_travel_time_hours(d) + stops * 8
            return 1.0 / (time_hours + 1e-6)
        else:
            fuel_tonnes = self._estimate_fuel_tonnes(d) * (1 + 0.025 * stops)
            return 1.0 / (fuel_tonnes + 1e-6)

    def _deterministic_shuffle(self, lst, seed):
        """Deterministic shuffle using Fisher-Yates algorithm"""
        rng = random.Random(seed)
        result = lst[:]
        for i in range(len(result) - 1, 0, -1):
            j = rng.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def _crossover(self, parent1, parent2, hub_ports, seed):
        """Order crossover on the hub permutation (Davis, 1985).

        The previous operator concatenated both parents and therefore did not
        search the permutation space. Start and end ports are fixed. Every
        required hub appears once.
        """
        rng = random.Random(seed)
        hubs1 = list(parent1[1:-1])
        hubs2 = list(parent2[1:-1])
        # Drop accidental duplicates from older call sites before crossing.
        hubs1 = list(dict.fromkeys(hubs1))
        hubs2 = list(dict.fromkeys(hubs2))
        for hub in hub_ports:
            if hub not in hubs1:
                hubs1.append(hub)
            if hub not in hubs2:
                hubs2.append(hub)
        n = len(hubs1)
        if n < 2:
            child_hubs = hubs1
        else:
            i, j = sorted(rng.sample(range(n), 2))
            child_hubs = [None] * n
            child_hubs[i : j + 1] = hubs1[i : j + 1]
            taken = set(child_hubs[i : j + 1])
            fill = [h for h in hubs2 if h not in taken]
            # Remaining required hubs, in parent-2 order, if a parent was short.
            for hub in hub_ports:
                if hub not in taken and hub not in fill:
                    fill.append(hub)
            cursor = 0
            for idx in list(range(j + 1, n)) + list(range(0, i)):
                child_hubs[idx] = fill[cursor]
                cursor += 1
        return [parent1[0]] + child_hubs + [parent1[-1]]

    def _mutate(self, route, hub_ports, seed):
        """Deterministic mutation that maintains all hub ports."""
        rng = random.Random(seed)
        
        if len(route) <= 3:
            return route
        
        intermediate_indices = list(range(1, len(route) - 1))
        
        if len(intermediate_indices) >= 2:
            i, j = rng.sample(intermediate_indices, 2)
            route[i], route[j] = route[j], route[i]
        
        return route

    def _run_genetic_algorithm(self, start_port, destination_port, hub_ports, goal):
        """Deterministic genetic algorithm to optimize route."""
        if not hub_ports:
            direct_route = [start_port, destination_port]
            direct_distance = self._total_distance(direct_route)
            return direct_route, direct_distance

        print(f" GA optimizing route with ALL hubs: {hub_ports}")
        
        # Generate deterministic seed for this specific optimization
        ga_seed = self._get_deterministic_seed(start_port, destination_port, hub_ports, goal)
        rng = random.Random(ga_seed)
        
        # Generate initial population deterministically
        population = []
        base_route = [start_port] + hub_ports + [destination_port]
        
        # Create variations by rotating the hub sequence
        for i in range(self.GA_POPULATION_SIZE):
            if i == 0:
                # First individual is the natural order
                route = base_route.copy()
            else:
                # Create variations by rotating and shuffling deterministically
                variation_seed = ga_seed + i * 1000
                variation_rng = random.Random(variation_seed)
                
                shuffled_hubs = hub_ports.copy()
                variation_rng.shuffle(shuffled_hubs)
                
                route = [start_port] + shuffled_hubs + [destination_port]
            population.append(route)

        best_route = None
        best_fitness = -float('inf')
        best_distance = float('inf')

        for generation in range(self.GA_GENERATIONS):
            # Evaluate fitness
            fitness_scores = []
            for route in population:
                route_hubs = set(route[1:-1]) 
                required_hubs = set(hub_ports)
                correct_start_end = route[0] == start_port and route[-1] == destination_port
                
                if required_hubs.issubset(route_hubs) and correct_start_end:
                    distance = self._total_distance(route)
                    fitness = self._fitness(route, goal)
                    fitness_scores.append((route, fitness, distance))
                    
                    if fitness > best_fitness:
                        best_route = route.copy()
                        best_fitness = fitness
                        best_distance = distance
                else:
                    fitness_scores.append((route, 0.0, float('inf')))

            fitness_scores.sort(key=lambda x: x[1], reverse=True)

            # Create new population (elitism + deterministic selection)
            new_population = []
            
            # Keep top individuals (elitism)
            elite_count = max(2, self.GA_POPULATION_SIZE // 10)
            for i in range(min(elite_count, len(fitness_scores))):
                if fitness_scores[i][1] > 0:
                    new_population.append(fitness_scores[i][0])

            # Fill rest with offspring
            while len(new_population) < self.GA_POPULATION_SIZE:
                # Deterministic tournament selection
                tourn_seed = ga_seed + generation * 10000 + len(new_population)
                tourn_rng = random.Random(tourn_seed)
                
                valid_routes = [route for route, fitness, _ in fitness_scores if fitness > 0]
                
                if len(valid_routes) >= 2:
                    # Tournament of size 3 (deterministic)
                    candidates1 = [valid_routes[tourn_rng.randint(0, len(valid_routes)-1)] for _ in range(3)]
                    candidates2 = [valid_routes[tourn_rng.randint(0, len(valid_routes)-1)] for _ in range(3)]
                    
                    parent1 = max(candidates1, key=lambda r: self._fitness(r, goal))
                    parent2 = max(candidates2, key=lambda r: self._fitness(r, goal))
                    
                    # Crossover with deterministic seed
                    cross_seed = ga_seed + generation * 1000 + len(new_population)
                    child = self._crossover(parent1, parent2, hub_ports, cross_seed)
                    
                    # Mutation with deterministic probability
                    if tourn_rng.random() < 0.3:
                        mutate_seed = ga_seed + generation * 10000 + len(new_population) + 1
                        child = self._mutate(child, hub_ports, mutate_seed)
                    
                    new_population.append(child)
                else:
                    # Fallback: use rotated base route
                    idx = len(new_population) % len(hub_ports)
                    rotated_hubs = hub_ports[idx:] + hub_ports[:idx]
                    new_population.append([start_port] + rotated_hubs + [destination_port])

            population = new_population[:self.GA_POPULATION_SIZE]

            if generation % 20 == 0:
                print(f"  Generation {generation}: Best distance = {best_distance:.2f} km")

        # Ensure all required hubs are included
        if best_route:
            final_hubs = set(best_route[1:-1])
            missing_hubs = set(hub_ports) - final_hubs
            
            if missing_hubs:
                print(f"  Adding missing hubs to final route: {missing_hubs}")
                
                for hub in missing_hubs:
                    best_increase = float('inf')
                    best_position = -1
                    
                    for i in range(1, len(best_route)): 
                        test_route = best_route.copy()
                        test_route.insert(i, hub)
                        increase = self._total_distance(test_route) - best_distance
                        
                        if increase < best_increase:
                            best_increase = increase
                            best_position = i
                    
                    if best_position != -1:
                        best_route.insert(best_position, hub)
                        best_distance = self._total_distance(best_route)

        if not best_route or best_fitness <= 0:
            print(" Using fallback route with all hubs")
            best_route = [start_port] + hub_ports + [destination_port]
            best_distance = self._total_distance(best_route)

        print(f" Final {goal} route: {' → '.join(best_route)}")
        print(f" Total distance: {best_distance:.2f} km")
        print(f" Includes {len(best_route) - 2} intermediate ports")
        
        return best_route, best_distance

    # ========== WEATHER INTEGRATION ==========
    def _initialize_weather_service(self):
        """Lazy initialization of weather service"""
        if self.weather_service is None:
            try:
                from utils.weather_service import weather_service
                self.weather_service = weather_service
                print(" Weather service initialized")
            except ImportError as e:
                print(f" Weather service import error: {e}")
                print(" Using simulated weather data")
                self.weather_service = None
    
    def _adjust_for_weather(self, distance_km, weather_impact):
        """Adjust travel time based on weather impact and vessel sensitivity"""
        sensitivity = self.current_vessel.get("weather_sensitivity", 1.0)
        base_time = (distance_km / self.AVERAGE_SPEED_KMH) * self.WEATHER_FACTOR
        
        # Scale impact by vessel sensitivity
        effective_impact = weather_impact * sensitivity
        
        if effective_impact < 2:
            multiplier = 1.0
        elif effective_impact < 4:
            multiplier = 1.1
        elif effective_impact < 6:
            multiplier = 1.3
        elif effective_impact < 8:
            multiplier = 1.6
        else:
            multiplier = 2.0
        
        return base_time * multiplier

    def _calculate_vessel_fuel(self, distance_km, speed_kmh, weather_impact):
        """
        Calculate fuel consumption using non-linear relationship (Admiralty Coefficient).
        Fuel Consumption P is proportional to speed v^3.
        """
        base_rate = self.current_vessel["base_fuel_rate"]
        avg_speed = self.current_vessel["avg_speed_kmh"]
        
        # Speed factor (cubic power law for power, square for distance-based rate)
        speed_ratio = speed_kmh / avg_speed
        dynamic_rate = base_rate * (speed_ratio ** 2)
        
        # Weather penalty on fuel (waves/wind increase resistance)
        weather_penalty = 1.0 + (weather_impact * 0.05)
        
        return distance_km * dynamic_rate * weather_penalty

    def _is_in_eca(self, lat, lon):
        """Check if coordinates fall within an Emission Control Area"""
        for zone in self.ECA_ZONES:
            lats = zone["lat_range"]
            lons = zone["lon_range"]
            if lats[0] <= lat <= lats[1] and lons[0] <= lon <= lons[1]:
                return True, zone["name"], zone["cost_multiplier"]
        return False, None, 1.0

    def _calculate_route_costs(self, route_points, weather_impact_avg):
        """Calculate total distance, fuel, CO2, and adjusted costs including ECA"""
        total_distance = 0.0
        eca_dist = 0.0
        
        for i in range(len(route_points) - 1):
            p1 = route_points[i]
            p2 = route_points[i+1]
            dist = self._haversine(p1[0], p1[1], p2[0], p2[1])
            total_distance += dist
            
            # Sample midpoint for ECA check
            mid_lat = (p1[0] + p2[0]) / 2
            mid_lon = (p1[1] + p2[1]) / 2
            in_eca, _, _ = self._is_in_eca(mid_lat, mid_lon)
            if in_eca:
                eca_dist += dist
        
        fuel_tonnes = self._calculate_vessel_fuel(total_distance, self.AVERAGE_SPEED_KMH, weather_impact_avg)
        co2_tonnes = fuel_tonnes * 3.114
        
        # Scenario bunker price used by the paper, not a quotation.
        base_cost = fuel_tonnes * 600
        eca_premium = (eca_dist / total_distance) * fuel_tonnes * 250 if total_distance > 0 else 0
        
        return {
            'distance_km': total_distance,
            'fuel_tonnes': fuel_tonnes,
            'co2_tonnes': co2_tonnes,
            'eca_distance_km': eca_dist,
            'total_cost_usd': base_cost + eca_premium
        }
    
    def _get_weather_recommendation(self, fastest_weather, fuel_weather, goal):
        """Get recommendation based on weather comparison"""
        fastest_impact = fastest_weather['average_impact']
        fuel_impact = fuel_weather['average_impact']
        
        if goal == "fastest":
            if fastest_impact < 4:
                return "Fastest route has favorable weather conditions"
            elif fastest_impact < 6:
                return "Fastest route has moderate weather - proceed with caution"
            else:
                return "Consider fuel-efficient route due to poor weather on fastest route"
        
        elif goal == "fuel":
            if fuel_impact < 4:
                return "Fuel-efficient route has favorable weather conditions"
            elif fuel_impact < 6:
                return "Fuel-efficient route has moderate weather - proceed with caution"
            else:
                return "Consider fastest route due to poor weather on efficient route"
        
        else:
            if fastest_impact < fuel_impact:
                return "Weather favors fastest route"
            elif fuel_impact < fastest_impact:
                return "Weather favors fuel-efficient route"
            else:
                return "Both routes have similar weather conditions"

    # ========== COORDINATE CONVERSION ==========
    def _nodes_to_latlon(self, path_nodes):
        """Convert path nodes to coordinates."""
        coords = []
        for n in path_nodes:
            coord = self.sea_graph.nodes[n].get("coord")
            if coord:
                coords.append(coord)
        return coords

    def _build_full_route_coordinates(self, seq):
        """Convert a sequence of ports into lat/lon coordinates."""
        coords = []
        for i in range(len(seq) - 1):
            start = seq[i]
            end = seq[i + 1]
            path_nodes, _ = self.port_paths.get((start, end), (None, float("inf")))
            if path_nodes:
                seg = self._nodes_to_latlon(path_nodes)
                if coords and seg and coords[-1] == seg[0]:
                    coords.extend(seg[1:])
                else:
                    coords.extend(seg)
            else:
                if coords:
                    coords.append(self.PORT_LOCATIONS[end])
                else:
                    coords.append(self.PORT_LOCATIONS[start])
                    coords.append(self.PORT_LOCATIONS[end])
        return coords

    def _gc_interpolate(self, p1, p2, n=60):
        """Great circle interpolation between two points."""
        lat1, lon1 = map(math.radians, p1)
        lat2, lon2 = map(math.radians, p2)

        def to_vec(lat, lon):
            x = math.cos(lat) * math.cos(lon)
            y = math.cos(lat) * math.sin(lon)
            z = math.sin(lat)
            return (x, y, z)

        v1 = to_vec(lat1, lon1)
        v2 = to_vec(lat2, lon2)
        dot = max(min(v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2], 1.0), -1.0)
        omega = math.acos(dot)
        if abs(omega) < 1e-12:
            return [p1, p2]

        points = []
        for i in range(n):
            t = i / (n - 1)
            s1 = math.sin((1 - t) * omega) / math.sin(omega)
            s2 = math.sin(t * omega) / math.sin(omega)
            x = s1 * v1[0] + s2 * v2[0]
            y = s1 * v1[1] + s2 * v2[1]
            z = s1 * v1[2] + s2 * v2[2]
            lat = math.atan2(z, math.sqrt(x * x + y * y))
            lon = math.atan2(y, x)
            points.append((math.degrees(lat), math.degrees(lon)))
        return points

    # ========== PHYSICS CALCULATIONS ==========
    def _calculate_real_fuel(self, route, distance, coordinates, hull_days, departure_time):
        """
        Calculate fuel using all physics models
        """
        # Tropical SST / salinity are scenario values, not a measured field.
        water_temps = [28.0] * max(len(coordinates), 1)
        salinities = [35.0] * max(len(coordinates), 1)
        fouling = hull_fouling.calculate_fouling_penalty(hull_days, water_temps, salinities)
        
        total_fuel = 0.0
        calm_fuel = 0.0
        current_time = departure_time
        speed_knots = self.AVERAGE_SPEED_KMH / 1.852
        
        for i in range(len(coordinates) - 1):
            lat1, lon1 = coordinates[i]
            lat2, lon2 = coordinates[i + 1]
            seg_dist = self._haversine(lat1, lon1, lat2, lon2)
            if seg_dist <= 0:
                continue
            bearing = self._bearing_deg(lat1, lon1, lat2, lon2)
            mid_lat = (lat1 + lat2) / 2
            mid_lon = (lon1 + lon2) / 2
            current = ocean_currents.along_track(mid_lat, mid_lon, current_time.month, bearing)
            # Constant speed through water. Time, and therefore fuel, scales with SOG.
            sog = speed_knots + current["along_knots"]
            sog = max(sog, 1.0)
            calm_segment = vessel_physics.fuel_consumption(seg_dist, speed_knots, 15.0)
            segment_fuel = calm_segment * (speed_knots / sog)
            calm_fuel += calm_segment
            total_fuel += segment_fuel
            current_time += timedelta(hours=seg_dist / (sog * 1.852))
        
        total_fuel *= fouling["fuel_multiplier"]
        calm_fuel *= fouling["fuel_multiplier"]
        if total_fuel > 0 and calm_fuel > 0:
            current_benefit = (calm_fuel - total_fuel) / calm_fuel * 100
        else:
            current_benefit = 0.0
        
        return {
            'total': round(total_fuel, 1),
            'fouling_penalty': fouling['total_penalty_percent'],
            'fouling_level': fouling['fouling_level'],
            'ocean_current_benefit': round(current_benefit, 1),
            'segments': len(coordinates) - 1,
            'arrival_time': current_time.isoformat() if current_time else None,
            'fouling_breakdown': fouling['organism_breakdown']
        }

    def _bearing_deg(self, lat1, lon1, lat2, lon2):
        """Initial great-circle bearing, degrees clockwise from north."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)
        y = math.sin(dlon) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
        return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Haversine distance in km"""
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

    # ========== MAIN ROUTE CALCULATION ==========
    def calculate_optimal_routes(self, start_port, destination_port, hub_ports=None, 
                                goal="both", include_weather=True, cargo_tonnes=32500, 
                                hull_days=90, departure_time=None):
        """Main method to calculate routes with ALL physics models"""
        if hub_ports is None:
            hub_ports = []
        
        if departure_time is None:
            from datetime import datetime
            departure_time = datetime.now()
        
        print("\n" + "="*70)
        print(" ENHANCED ROUTE CALCULATION WITH PHYSICS")
        print("="*70)
        print(f" Departure: {departure_time}")
        print(f" Goal: {goal}")
        print(f" Cargo: {cargo_tonnes} tonnes")
        print(f" Hull days since cleaning: {hull_days}")
        
        # Get moon phase for departure
        moon = lunar_tides.moon_phase(departure_time)
        print(f" Moon: {moon['icon']} {moon['phase']} ({moon['illumination']}% illuminated)")
        
        self.current_hub_ports = hub_ports
        self.hull_days = hull_days
        self.departure_time = departure_time
        
        # Generate deterministic GA routes
        fastest_route, fastest_distance = self._run_genetic_algorithm(
            start_port, destination_port, hub_ports, "fastest"
        )
        fuel_route, fuel_distance = self._run_genetic_algorithm(
            start_port, destination_port, hub_ports, "fuel"
        )
        
        # Build route coordinates
        fast_coords = self._build_full_route_coordinates(fastest_route)
        fuel_coords = self._build_full_route_coordinates(fuel_route)
        direct_coords = self._gc_interpolate(
            self.PORT_LOCATIONS[start_port], 
            self.PORT_LOCATIONS[destination_port]
        )
        
        # Apply physics models to calculate REAL fuel
        fastest_physics = self._calculate_real_fuel(
            fastest_route, fastest_distance, fast_coords, hull_days, departure_time
        )
        fuel_physics = self._calculate_real_fuel(
            fuel_route, fuel_distance, fuel_coords, hull_days, departure_time
        )
        
        # Calculate base times
        fastest_time_base = self._estimate_travel_time_hours(fastest_distance)
        fuel_time_base = self._estimate_travel_time_hours(fuel_distance)
        
        # Initialize results structure with PHYSICS data
        results = {
            'fastest_route': {
                'ports': fastest_route,
                'distance_km': fastest_distance,
                'time_hours': fastest_time_base,
                'fuel_tonnes': fastest_physics['total'],
                'co2_tonnes': fastest_physics['total'] * 3.114,
                'coordinates': fast_coords,
                'physics': fastest_physics
            },
            'fuel_efficient_route': {
                'ports': fuel_route,
                'distance_km': fuel_distance,
                'time_hours': fuel_time_base,
                'fuel_tonnes': fuel_physics['total'],
                'co2_tonnes': fuel_physics['total'] * 3.114,
                'coordinates': fuel_coords,
                'physics': fuel_physics
            },
            'direct_route': {
                'coordinates': direct_coords
            },
            'port_locations': self.PORT_LOCATIONS,
            'deterministic_hash': self._get_deterministic_seed(
                start_port, destination_port, hub_ports, goal
            ),
            'environment': {
                'moon_phase': moon,
                'departure_time': departure_time.isoformat()
            }
        }
        
        # Weather integration
        if include_weather:
            print(" Processing weather data...")
            self._initialize_weather_service()
            
            if self.weather_service:
                fastest_weather = self.weather_service.get_route_weather(fast_coords)
                fuel_weather = self.weather_service.get_route_weather(fuel_coords)
            else:
                # Use deterministic simulated weather
                weather_seed = results['deterministic_hash']
                weather_rng = random.Random(weather_seed)
                fastest_weather = {
                    'weather_points': [],
                    'average_impact': round(weather_rng.uniform(2.0, 6.0), 1),
                    'overall_condition': weather_rng.choice(['Good', 'Moderate', 'Excellent']),
                    'recommendation': 'Deterministic simulated weather data',
                    'storm_glass_data': {
                        'average_swell': round(weather_rng.uniform(1.0, 3.0), 1),
                        'water_temp': round(18 + weather_rng.uniform(-5, 5), 1)
                    }
                }
                weather_seed_fuel = weather_seed + 1
                weather_rng_fuel = random.Random(weather_seed_fuel)
                fuel_weather = {
                    'weather_points': [],
                    'average_impact': round(weather_rng_fuel.uniform(2.0, 6.0), 1),
                    'overall_condition': weather_rng_fuel.choice(['Good', 'Moderate', 'Excellent']),
                    'recommendation': 'Deterministic simulated weather data',
                    'storm_glass_data': {
                        'average_swell': round(weather_rng_fuel.uniform(1.0, 3.0), 1),
                        'water_temp': round(18 + weather_rng_fuel.uniform(-5, 5), 1)
                    }
                }
            
            simulated = fastest_weather.get("recommendation") == "Deterministic simulated weather data"
            if simulated:
                results["fastest_route"]["weather_impact"] = {"status": "not_estimated"}
                results["fuel_efficient_route"]["weather_impact"] = {"status": "not_estimated"}
                results["weather_recommendation"] = (
                    "Weather is not estimated. A random field was not applied to time or fuel."
                )
            else:
                fastest_time_adjusted = self._adjust_for_weather(
                    fastest_distance, fastest_weather["average_impact"]
                )
                fuel_time_adjusted = self._adjust_for_weather(
                    fuel_distance, fuel_weather["average_impact"]
                )
                results["fastest_route"]["weather_impact"] = fastest_weather
                results["fastest_route"]["time_hours"] = fastest_time_adjusted
                results["fuel_efficient_route"]["weather_impact"] = fuel_weather
                results["fuel_efficient_route"]["time_hours"] = fuel_time_adjusted
                results["weather_recommendation"] = self._get_weather_recommendation(
                    fastest_weather, fuel_weather, goal
                )
        else:
            results["weather_recommendation"] = "Weather is not estimated."
        
        # Clean up
        if hasattr(self, 'current_hub_ports'):
            del self.current_hub_ports
        
        print("\n FUEL COMPARISON:")
        print(f"   Old method: {fastest_distance * self.FUEL_CONSUMPTION_PER_KM:.1f} tonnes")
        print(f"   New physics: {fastest_physics['total']:.1f} tonnes")
        print(f"   Difference: +{((fastest_physics['total']/(fastest_distance * self.FUEL_CONSUMPTION_PER_KM)-1)*100):.1f}%")
        print(f"   Hull fouling: +{fastest_physics['fouling_penalty']}%")
        print(f"   Ocean current: {fastest_physics['ocean_current_benefit']}% benefit")
        
        print(" Route calculation complete!")
        return results