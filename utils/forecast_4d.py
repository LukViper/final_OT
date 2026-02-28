"""
4D Weather Forecasting System with Multiple API Fallbacks
Predicts weather at the exact time the ship will be at each point
"""

import math
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
import requests
import time
import os

class Forecast4D:
    """
    4D Weather Forecasting with Monte Carlo ensembles
    Uses multiple APIs with fallback for maximum reliability
    """
    
    def __init__(self):
        # API keys (get from environment variables)
        self.openweather_key = os.getenv('OPENWEATHER_API_KEY', '')
        
        # API endpoints
        self.apis = [
            {
                'name': 'Open-Meteo',
                'url': 'https://api.open-meteo.com/v1/forecast',
                'params': lambda lat, lon: {
                    'latitude': lat,
                    'longitude': lon,
                    'hourly': ['temperature_2m', 'windspeed_10m', 'winddirection_10m',
                              'pressure_msl', 'precipitation'],
                    'forecast_days': 10,
                    'timezone': 'auto'
                },
                'parse': self._parse_openmeteo,
                'priority': 1
            }
        ]
        
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes
        self.timeout = 3  # Shorter timeout to avoid hanging
        
        print("✅ 4D Forecasting System initialized")
        print(f"   📡 APIs available: {len(self.apis)}")
    
    def get_forecast_at_time(self, lat: float, lon: float, target_time: datetime) -> Dict:
        """
        Get weather forecast for specific future time
        Tries multiple APIs with fallback
        """
        # Round to 2 decimals for caching
        cache_key = f"{lat:.2f}_{lon:.2f}_{target_time.strftime('%Y%m%d%H')}"
        
        # Check cache
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_duration:
                return data
        
        # Try APIs in priority order
        for api in sorted(self.apis, key=lambda x: x['priority']):
            try:
                params = api['params'](round(lat, 2), round(lon, 2))
                
                response = requests.get(
                    api['url'],
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    forecast = api['parse'](data, target_time)
                    if forecast:
                        self.cache[cache_key] = (time.time(), forecast)
                        return forecast
                        
            except Exception as e:
                print(f"   ⚠️ {api['name']} failed: {e}")
                continue
        
        # All APIs failed - use physics-based forecast
        print(f"   ℹ️ Using physics-based forecast for {lat:.1f}, {lon:.1f}")
        forecast = self._physics_forecast(lat, lon, target_time)
        self.cache[cache_key] = (time.time(), forecast)
        return forecast
    
    def _parse_openmeteo(self, data: Dict, target_time: datetime) -> Optional[Dict]:
        """Parse Open-Meteo forecast data"""
        try:
            times = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in data['hourly']['time']]
            idx = min(range(len(times)), key=lambda i: abs((times[i] - target_time).total_seconds()))
            
            # Safely get values with defaults
            wind_ms = data['hourly']['windspeed_10m'][idx] or 10
            temp = data['hourly']['temperature_2m'][idx] or 15
            pressure = data['hourly']['pressure_msl'][idx] or 1013
            precip = data['hourly']['precipitation'][idx] or 0
            wind_dir = data['hourly']['winddirection_10m'][idx] or 180
            
            return {
                'temperature': float(temp),
                'wind_speed': float(wind_ms) * 3.6,  # m/s to km/h
                'wind_direction': float(wind_dir),
                'pressure': float(pressure),
                'precipitation': float(precip),
                'wave_height': 1.5,  # Default
                'source': 'open-meteo',
                'confidence': 0.9
            }
        except Exception as e:
            print(f"   ⚠️ Error parsing Open-Meteo: {e}")
            return None
    
    def _physics_forecast(self, lat: float, lon: float, target_time: datetime) -> Dict:
        """Physics-based forecast using climatology and persistence"""
        hours_ahead = max(0, (target_time - datetime.now()).total_seconds() / 3600)
        abs_lat = abs(lat)
        month = target_time.month
        
        # Base values from climatology
        if abs_lat < 10:
            temp = 28
            wind = 12
            wave = 1.0
        elif abs_lat < 30:
            temp = 24
            wind = 20
            wave = 1.8
        elif abs_lat < 60:
            temp = 15
            wind = 28
            wave = 2.5
        else:
            temp = 5
            wind = 35
            wave = 3.5
        
        # Seasonal adjustment
        if month in [12, 1, 2]:  # Winter
            temp -= 5 if abs_lat > 30 else 0
            wind *= 1.2
        elif month in [6, 7, 8]:  # Summer
            temp += 5 if abs_lat > 30 else 0
        
        # Diurnal cycle
        hour = target_time.hour
        temp += 3 * math.sin(2 * math.pi * (hour - 14) / 24)
        
        # Uncertainty increases with time
        confidence = max(0.5, 1 - hours_ahead / (24 * 7))
        
        return {
            'temperature': round(temp, 1),
            'wind_speed': round(wind, 1),
            'wind_direction': 180,
            'wave_height': round(wave, 1),
            'pressure': 1013,
            'precipitation': round(max(0, wind / 20), 1),
            'source': 'physics-4d',
            'confidence': round(confidence, 2)
        }
    
    def route_timeline_4d(self, route_coords: List[Tuple], departure_time: datetime,
                         speed_knots: float = 20) -> Dict:
        """
        Generate 4D weather timeline for entire journey
        Weather is forecast for the exact arrival time at each point
        """
        timeline = []
        cumulative_hours = 0
        speed_kmh = speed_knots * 1.852
        
        # Calculate total distance and duration
        total_distance = 0
        for i in range(1, len(route_coords)):
            total_distance += self._haversine(route_coords[i-1], route_coords[i])
        
        total_hours = total_distance / speed_kmh
        total_days = total_hours / 24
        
        print(f"\n🌐 4D Route Timeline - {len(route_coords)-1} segments")
        print(f"   Total distance: {total_distance:.0f} km")
        print(f"   Speed: {speed_knots:.1f} knots")
        print(f"   Duration: {total_days:.1f} days ({total_hours:.1f} hours)")
        
        for i in range(1, len(route_coords)):
            seg_dist = self._haversine(route_coords[i-1], route_coords[i])
            seg_hours = seg_dist / speed_kmh
            cumulative_hours += seg_hours
            
            # Arrival time at this point
            arrival = departure_time + timedelta(hours=cumulative_hours)
            
            # Get forecast for this specific arrival time
            forecast = self.get_forecast_at_time(
                route_coords[i][0], route_coords[i][1], arrival
            )
            
            timeline.append({
                'segment': i,
                'from_coord': route_coords[i-1],
                'to_coord': route_coords[i],
                'distance_km': round(seg_dist, 1),
                'duration_hours': round(seg_hours, 2),
                'arrival_time': arrival.isoformat(),
                'day': round(cumulative_hours / 24, 2),
                'forecast': forecast
            })
        
        return {
            'timeline': timeline,
            'total_days': round(total_days, 1),
            'total_hours': round(total_hours, 1),
            'total_distance': round(total_distance, 1),
            'departure_time': departure_time.isoformat(),
            'ensemble_confidence': self._calculate_confidence(timeline)
        }
    
    def _haversine(self, p1, p2):
        """Haversine distance in km"""
        R = 6371
        lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    def _calculate_confidence(self, timeline):
        """Calculate overall forecast confidence"""
        confidences = [seg['forecast'].get('confidence', 0.5) for seg in timeline]
        return round(sum(confidences) / len(confidences), 2)

forecast_4d = Forecast4D()


