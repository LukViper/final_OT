from flask import Flask, render_template, request, jsonify
from utils.route_calculator import ShippingRouteOptimizer
import json
import time
from datetime import datetime
import threading
from collections import defaultdict, deque
import heapq
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Add Analytics class
class RealTimeAnalytics:
    def __init__(self):
        self.route_calculations = deque(maxlen=100)
        self.performance_metrics = {
            'total_calculations': 0,
            'total_distance_saved': 0.0,
            'total_fuel_saved': 0.0,
            'total_time_saved': 0.0,
            'total_co2_reduced': 0.0,
            'total_cost_saved': 0.0
        }
        self.port_usage = defaultdict(int)
        self.algorithm_performance = {
            'A*': {'count': 0, 'avg_time': 0.0},
            'Genetic': {'count': 0, 'avg_time': 0.0}
        }
        self.hourly_activity = defaultdict(int)
        self.lock = threading.Lock()
    
    def log_calculation(self, start_port, destination_port, hub_ports, fastest_route, fuel_route, calculation_time):
        """Log every route calculation in real-time"""
        with self.lock:
            # Calculate savings with safe defaults
            fastest_fuel = fastest_route.get('fuel_tonnes', 0) or 0
            fuel_fuel = fuel_route.get('fuel_tonnes', 0) or 0
            fastest_time = fastest_route.get('time_hours', 0) or 0
            fuel_time = fuel_route.get('time_hours', 0) or 0
            fastest_dist = fastest_route.get('distance_km', 0) or 0
            fuel_dist = fuel_route.get('distance_km', 0) or 0
            
            fuel_savings = fastest_fuel - fuel_fuel
            time_savings = (fuel_time - fastest_time) / 24 if fuel_time and fastest_time else 0
            distance_savings = fastest_dist - fuel_dist
            co2_savings = fuel_savings * 3.114 if fuel_savings else 0
            cost_savings = fuel_savings * 600 if fuel_savings else 0
            
            calculation_record = {
                'id': len(self.route_calculations) + 1,
                'timestamp': datetime.now().isoformat(),
                'start_port': start_port or "Unknown",
                'destination_port': destination_port or "Unknown",
                'hub_ports': hub_ports or [],
                'fastest_route': fastest_route,
                'fuel_route': fuel_route,
                'calculation_time': calculation_time or 0,
                'savings': {
                    'fuel': max(0, fuel_savings) if fuel_savings else 0,
                    'distance': max(0, distance_savings) if distance_savings else 0,
                    'time': max(0, -time_savings) if time_savings else 0,
                    'co2': max(0, co2_savings) if co2_savings else 0,
                    'cost': max(0, cost_savings) if cost_savings else 0
                }
            }
            
            self.route_calculations.append(calculation_record)
            
            # Update metrics
            self.performance_metrics['total_calculations'] += 1
            self.performance_metrics['total_distance_saved'] += calculation_record['savings']['distance']
            self.performance_metrics['total_fuel_saved'] += calculation_record['savings']['fuel']
            self.performance_metrics['total_time_saved'] += calculation_record['savings']['time']
            self.performance_metrics['total_co2_reduced'] += calculation_record['savings']['co2']
            self.performance_metrics['total_cost_saved'] += calculation_record['savings']['cost']
            
            # Update port usage
            all_ports = []
            if fastest_route and 'ports' in fastest_route:
                all_ports.extend(fastest_route['ports'])
            if fuel_route and 'ports' in fuel_route:
                all_ports.extend(fuel_route['ports'])
            
            for port in all_ports:
                if port:
                    self.port_usage[port] += 1
            
            # Update hourly activity
            hour = datetime.now().strftime('%H:00')
            self.hourly_activity[hour] += 1
            
            # Update algorithm performance
            self.algorithm_performance['A*']['count'] += 1
            self.algorithm_performance['Genetic']['count'] += 1
    
    def get_realtime_data(self):
        """Get real-time analytics data for frontend"""
        with self.lock:
            recent_calculations = list(self.route_calculations)[-10:]
            
            # Get top 10 ports
            total_port_uses = sum(self.port_usage.values())
            top_ports = heapq.nlargest(10, self.port_usage.items(), key=lambda x: x[1])
            port_usage_percent = {
                port: (count / total_port_uses * 100) if total_port_uses > 0 else 0
                for port, count in top_ports
            }
            
            # Calculate algorithm performance percentages
            total_algo_calls = sum(algo['count'] for algo in self.algorithm_performance.values())
            
            if total_algo_calls > 0:
                a_star_perf = (self.algorithm_performance['A*']['count'] / total_algo_calls) * 100
                genetic_perf = (self.algorithm_performance['Genetic']['count'] / total_algo_calls) * 100
            else:
                a_star_perf = 0.0
                genetic_perf = 0.0
            
            # Calculate total optimization based on actual savings
            if self.performance_metrics['total_calculations'] > 0:
                avg_fuel_savings = self.performance_metrics['total_fuel_saved'] / self.performance_metrics['total_calculations']
                avg_distance_saved = self.performance_metrics['total_distance_saved'] / self.performance_metrics['total_calculations']
                avg_time_saved = self.performance_metrics['total_time_saved'] / self.performance_metrics['total_calculations']
                
                fuel_optimization = min((avg_fuel_savings / 50) * 100, 40) if avg_fuel_savings > 0 else 0
                distance_optimization = min((avg_distance_saved / 1000) * 100, 30) if avg_distance_saved > 0 else 0
                time_optimization = min((avg_time_saved / 5) * 100, 30) if avg_time_saved > 0 else 0
                
                total_optimization = min(fuel_optimization + distance_optimization + time_optimization, 100)
            else:
                total_optimization = 0.0
            
            # Calculate average calculation time
            if self.route_calculations:
                avg_calc_time = sum(calc['calculation_time'] for calc in self.route_calculations) / len(self.route_calculations)
            else:
                avg_calc_time = 0.0
            
            # Determine fastest algorithm
            if a_star_perf > genetic_perf:
                fastest_algorithm = "A* Algorithm"
            elif genetic_perf > a_star_perf:
                fastest_algorithm = "Genetic Algorithm"
            else:
                fastest_algorithm = "Both Equal"
            
            return {
                'performance_metrics': {
                    'total_calculations': self.performance_metrics['total_calculations'],
                    'total_distance_saved': round(self.performance_metrics['total_distance_saved'], 1),
                    'total_fuel_saved': round(self.performance_metrics['total_fuel_saved'], 1),
                    'total_time_saved': round(self.performance_metrics['total_time_saved'], 1),
                    'total_co2_reduced': round(self.performance_metrics['total_co2_reduced'], 1),
                    'total_cost_saved': round(self.performance_metrics['total_cost_saved'], 0)
                },
                'recent_calculations': [
                    {
                        'start_port': calc.get('start_port', 'Unknown'),
                        'destination_port': calc.get('destination_port', 'Unknown'),
                        'timestamp': calc.get('timestamp', datetime.now().isoformat()),
                        'calculation_time': calc.get('calculation_time', 0)
                    }
                    for calc in recent_calculations
                ],
                'port_usage': port_usage_percent,
                'algorithm_stats': {
                    'total_calculations': self.performance_metrics['total_calculations'],
                    'average_calculation_time': round(avg_calc_time, 2),
                    'fastest_algorithm': fastest_algorithm,
                    'routes_calculated': self.performance_metrics['total_calculations'],
                    'performance_metrics': {
                        'a_star_performance': round(a_star_perf, 1),
                        'genetic_algorithm_performance': round(genetic_perf, 1),
                        'total_optimization': round(total_optimization, 1)
                    }
                },
                'timestamp': datetime.now().isoformat()
            }

# Initialize analytics and optimizer
realtime_analytics = RealTimeAnalytics()
route_optimizer = ShippingRouteOptimizer()

_CHECK_MESH = None


def _check_mesh():
    global _CHECK_MESH
    if _CHECK_MESH is None:
        from research.navigable_mesh import build_mesh
        _CHECK_MESH = build_mesh(
            (32.0, 9.5, 62.0, 32.5),
            resolution=0.25,
            strait_half_width_deg=0.30,
        )
    return _CHECK_MESH


@app.route('/api/check-route')
def check_route():
    """Coastline-mesh check for the one route the page can verify."""
    from research.navigable_mesh import (
        JEBEL_ALI,
        great_circle_km,
        haversine_km,
        path_crosses_bab_el_mandeb,
        path_detours_east,
        path_goes_south_of_gulf,
        shortest_path,
    )
    from research.baselines import SERVICE_SPEED_KN, baseline_1, baseline_2
    from research.run_decomposition import _polyline_file_path, _sample_great_circle

    canal = (30.5852, 32.2654)
    mesh = shortest_path(_check_mesh(), JEBEL_ALI, canal, method="astar")
    dijkstra = shortest_path(_check_mesh(), JEBEL_ALI, canal, method="dijkstra")
    gc_km = great_circle_km(JEBEL_ALI, canal)
    coords = mesh["coords"]
    checks = [
        {"name": "Enters the Bab el-Mandeb", "pass": path_crosses_bab_el_mandeb(coords)},
        {"name": "Does not go east of 62°E", "pass": not path_detours_east(coords, 62.0)},
        {"name": "Does not leave south toward the Cape", "pass": not path_goes_south_of_gulf(coords)},
        {"name": "Sea path is longer than the great circle", "pass": mesh["distance_km"] > gc_km},
        {"name": "A* matches Dijkstra", "pass": abs(mesh["distance_km"] - dijkstra["distance_km"]) < 1e-6},
    ]
    polyline = _polyline_file_path(JEBEL_ALI, canal)
    b1 = baseline_1(gc_km, SERVICE_SPEED_KN)
    b2 = baseline_2(mesh["distance_km"], SERVICE_SPEED_KN)
    working = all(item["pass"] for item in checks)
    polyline_km = None
    if polyline and len(polyline) > 1:
        polyline_km = sum(
            haversine_km(a[0], a[1], b[0], b[1]) for a, b in zip(polyline, polyline[1:])
        )
    return jsonify({
        "name": "Jebel Ali to Suez Canal",
        "start_port": "Jebel_Ali",
        "destination_port": "Suez_Canal",
        "working": working,
        "mesh_km": round(mesh["distance_km"], 3),
        "great_circle_km": round(gc_km, 3),
        "polyline_km": None if polyline_km is None else round(polyline_km, 3),
        "ratio": round(mesh["distance_km"] / gc_km, 4),
        "mesh_fuel_t": round(b2["fuel_t"], 4),
        "great_circle_fuel_t": round(b1["fuel_t"], 4),
        "mesh_co2_t": round(b2["co2_t"], 4),
        "great_circle_co2_t": round(b1["co2_t"], 4),
        "mesh_hours": round(b2["hours"], 4),
        "speed_knots": SERVICE_SPEED_KN,
        "bunker_usd_per_t": 600,
        "weather": "not_estimated",
        "hull": "clean",
        "polyline_drawn": polyline is not None,
        "checks": checks,
        "mesh_coordinates": coords,
        "great_circle_coordinates": _sample_great_circle(JEBEL_ALI, canal),
        "polyline_coordinates": polyline or [],
        "note": "Calm-water Holtrop-Mennen at 18 kn, clean hull. Weather is not estimated. The great circle crosses Arabia and is not a voyage.",
    })


@app.route('/')
def index():
    ports = list(route_optimizer.PORT_LOCATIONS.keys())
    return render_template('index.html', ports=ports)

@app.route('/calculate-routes', methods=['POST'])
def calculate_routes():
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get values with defaults
        start_port = data.get('start_port')
        destination_port = data.get('destination_port')
        hub_ports = data.get('hub_ports', [])
        goal = data.get('goal', 'both')
        include_weather = data.get('include_weather', True)
        
        # Get new parameters
        vessel_type = data.get('vessel_type', 'Container_Ship')
        cargo_tonnes = data.get('cargo_tonnes', 32500)
        speed_knots = data.get('speed_knots', 20)
        hull_days = data.get('hull_days', 90)
        departure_time_str = data.get('departure_time')
        constraints = data.get('constraints', {})
        
        # Get physics model toggles
        use_holtrop = data.get('use_holtrop', True)
        use_fouling = data.get('use_fouling', True)
        use_currents = data.get('use_currents', True)
        use_tides = data.get('use_tides', True)
        use_weather = data.get('use_weather', True)
        use_eca = data.get('use_eca', True)
        
        ensemble_size = data.get('ensemble_size', 10)
        
        # Parse departure time - FIX: Make it timezone-naive
        if departure_time_str:
            try:
                # Parse ISO format and remove timezone info
                dt = datetime.fromisoformat(departure_time_str.replace('Z', '+00:00'))
                # Convert to naive datetime (remove timezone)
                departure_time = dt.replace(tzinfo=None)
            except:
                departure_time = datetime.now()
        else:
            departure_time = datetime.now()
        
        # Validate required fields
        if not start_port or not destination_port:
            return jsonify({'error': 'Please select both start and destination ports'}), 400
        
        print(f"\n Calculating route: {start_port} → {destination_port}")
        print(f"   Vessel: {vessel_type}, Cargo: {cargo_tonnes}t, Speed: {speed_knots} knots")
        print(f"   Hull days: {hull_days}, Departure: {departure_time}")
        print(f"   Constraints: {constraints}")
        print(f"   Physics Models: Holtrop={use_holtrop}, Fouling={use_fouling}, Currents={use_currents}, Tides={use_tides}, Weather={use_weather}, ECA={use_eca}")
        print(f"   Ensemble Size: {ensemble_size}")
        
        # Set vessel type in optimizer
        if vessel_type in route_optimizer.VESSEL_PROFILES:
            route_optimizer.current_vessel = route_optimizer.VESSEL_PROFILES[vessel_type]
            route_optimizer.AVERAGE_SPEED_KMH = route_optimizer.current_vessel["avg_speed_kmh"]
            route_optimizer.FUEL_CONSUMPTION_PER_KM = route_optimizer.current_vessel["base_fuel_rate"]
        
        if not use_fouling:
            hull_days = 0
        route_optimizer.hull_days = hull_days
        
        # Set departure time
        route_optimizer.departure_time = departure_time
        
        # Calculate routes with all parameters
        results = route_optimizer.calculate_optimal_routes(
            start_port=start_port,
            destination_port=destination_port,
            hub_ports=hub_ports,
            goal=goal,
            include_weather=include_weather and use_weather,
            cargo_tonnes=cargo_tonnes,
            hull_days=hull_days,
            departure_time=departure_time
        )
        
        # Add calculation time
        calculation_time = time.time() - start_time
        results['calculation_time'] = round(calculation_time, 2)
        
        # Add vessel info
        results['vessel_info'] = {
            'type': vessel_type,
            'cargo_tonnes': cargo_tonnes,
            'speed_knots': speed_knots,
            'hull_days': hull_days
        }
        
        # Add constraints
        results['constraints'] = constraints
        
        results['ensemble_confidence'] = None
        weather_impact = (results.get('fastest_route') or {}).get('weather_impact') or {}
        if include_weather and use_weather and weather_impact.get('confidence') is not None:
            results['ensemble_confidence'] = weather_impact['confidence']
        
        # Log to analytics
        try:
            realtime_analytics.log_calculation(
                start_port, destination_port, hub_ports,
                results.get('fastest_route', {}),
                results.get('fuel_efficient_route', {}),
                calculation_time
            )
        except Exception as e:
            print(f" Analytics logging error: {e}")
        
        print(f" Route calculation complete in {calculation_time:.2f}s")
        return jsonify(results)
        
    except Exception as e:
        print(f" Fatal error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/realtime-analytics')
def get_realtime_analytics():
    """Get real-time analytics data with fallback"""
    try:
        analytics_data = realtime_analytics.get_realtime_data()
        return jsonify(analytics_data)
    except Exception as e:
        print(f"Analytics error: {e}")
        traceback.print_exc()
        return jsonify({
            'error': 'analytics unavailable',
            'performance_metrics': {
                'total_calculations': 0,
                'total_distance_saved': 0.0,
                'total_fuel_saved': 0.0,
                'total_time_saved': 0.0,
                'total_co2_reduced': 0.0,
                'total_cost_saved': 0
            },
            'recent_calculations': [],
            'port_usage': {},
            'algorithm_stats': {
                'total_calculations': 0,
                'average_calculation_time': 0.0,
                'fastest_algorithm': None,
                'routes_calculated': 0,
                'performance_metrics': {
                    'a_star_performance': 0.0,
                    'genetic_algorithm_performance': 0.0,
                    'total_optimization': 0.0
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/analytics')
def analytics_page():
    """Analytics page with real-time data"""
    try:
        analytics_data = realtime_analytics.get_realtime_data()
    except Exception:
        analytics_data = {
            'error': 'analytics unavailable',
            'performance_metrics': {
                'total_calculations': 0,
                'total_distance_saved': 0.0,
                'total_fuel_saved': 0.0,
                'total_time_saved': 0.0,
                'total_co2_reduced': 0.0,
                'total_cost_saved': 0
            }
        }
    
    ports = list(route_optimizer.PORT_LOCATIONS.keys())
    return render_template('analytics.html', 
                         analytics_data=analytics_data,
                         ports=ports)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("="*60)
    print("Lane-constrained route calculator")
    print("="*60)
    print("Access the application at: http://localhost:5006")
    print("Reported study numbers come from experiments/run_study.py, not this UI.")
    print("Models in use:")
    print("   - Holtrop-Mennen resistance (utils/holtrop_mennen.py)")
    print("   - Scenario fouling multiplier (not an ITTC procedure)")
    print("   - Schematic ocean-current cores")
    print("   - A* on the lane graph; order crossover for hub permutations")
    print("="*60)
    print("⏹  Press CTRL+C to stop the server")
    print("="*60)
    app.run(debug=True, port=5006, host='0.0.0.0')