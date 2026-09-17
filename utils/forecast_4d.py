"""
4D Weather Forecasting System with Multi-Source Ensemble
Predicts weather at exact arrival times with uncertainty quantification
"""

import math
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional, Any
import requests
import time
import os
import logging
import shelve
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Forecast4D:
    """
    4D Weather Forecasting with Monte Carlo ensembles and multi-source fallback.
    
    Features:
    - Multi-API parallel requests with confidence scoring
    - Spatial grid caching with expiration
    - Linear temporal interpolation between forecast hours
    - Physics-based wave growth model
    - Ensemble uncertainty quantification
    - Weather impact on vessel speed
    - Threaded segment processing
    - Persistent disk cache
    """
    
    # API Configuration
    API_SOURCES = [
        {
            'name': 'Open-Meteo',
            'url': 'https://api.open-meteo.com/v1/forecast',
            'priority': 1,
            'timeout': 3,
            'retries': 2,
            'confidence_base': 0.95,
            'requires_key': False,
            'variables': ['temperature_2m', 'windspeed_10m', 'winddirection_10m',
                         'pressure_msl', 'precipitation']
        },
        {
            'name': 'Open-Meteo Marine',
            'url': 'https://marine-api.open-meteo.com/v1/marine',
            'priority': 2,
            'timeout': 3,
            'retries': 2,
            'confidence_base': 0.94,
            'requires_key': False,
            'variables': ['wave_height', 'swell_wave_height', 'swell_wave_direction',
                         'swell_wave_period', 'ocean_current_velocity']
        },
        {
            'name': 'OpenWeatherMap',
            'url': 'https://api.openweathermap.org/data/2.5/forecast',
            'priority': 3,
            'timeout': 5,
            'retries': 3,
            'confidence_base': 0.88,
            'requires_key': True,
            'variables': ['temp', 'wind_speed', 'wind_deg', 'pressure', 'humidity']
        },
        {
            'name': 'Copernicus Marine',
            'url': 'https://nrt.cmems-du.eu/motu/api/Motu',
            'priority': 4,
            'timeout': 8,
            'retries': 2,
            'confidence_base': 0.96,
            'requires_key': True,
            'variables': ['sea_surface_temperature', 'sea_water_velocity']
        }
    ]
    
    # Physical constants
    G = 9.81  # m/s²
    RHO_AIR = 1.225  # kg/m³
    RHO_WATER = 1025  # kg/m³
    
    # Spatial grid for caching (0.1° ≈ 11km resolution)
    CACHE_GRID_SIZE = 0.1
    CACHE_DURATION = 1800  # 30 seconds
    CACHE_FILE = 'weather_cache.db'
    
    def __init__(self):
        """Initialize forecasting system with API keys and cache."""
        self.api_keys = self._load_api_keys()
        self.active_apis = self._filter_apis_by_key()
        
        # Initialize caches
        self.memory_cache: Dict[str, Tuple[float, Dict]] = {}
        self.disk_cache = shelve.open(self.CACHE_FILE, writeback=True)
        
        # Statistics
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'api_failures': 0,
            'avg_response_time': 0.0
        }
        
        logger.info(f"✅ 4D Forecasting System initialized")
        logger.info(f"   📡 APIs available: {len(self.active_apis)}")
        logger.info(f"   🗺️  Grid resolution: {self.CACHE_GRID_SIZE}°")
        
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables."""
        return {
            'OPENWEATHER_API_KEY': os.getenv('OPENWEATHER_API_KEY', ''),
            'TOMORROW_IO_API_KEY': os.getenv('TOMORROW_IO_API_KEY', ''),
            'WEATHERBIT_API_KEY': os.getenv('WEATHERBIT_API_KEY', ''),
            'COPERNICUS_USERNAME': os.getenv('COPERNICUS_USERNAME', ''),
            'COPERNICUS_PASSWORD': os.getenv('COPERNICUS_PASSWORD', '')
        }
    
    def _filter_apis_by_key(self) -> List[Dict]:
        """Filter APIs based on available keys."""
        filtered = []
        for api in self.API_SOURCES:
            if api['requires_key']:
                key_name = f"{api['name'].upper()}_API_KEY".replace(' ', '_')
                if self.api_keys.get(key_name):
                    api['key'] = self.api_keys[key_name]
                    filtered.append(api)
                    logger.info(f"   ✅ {api['name']} enabled")
            else:
                filtered.append(api)
                logger.info(f"   ✅ {api['name']} enabled (free)")
        return filtered
    
    def _grid_key(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert coordinates to grid cell key for spatial caching."""
        return (
            round(lat / self.CACHE_GRID_SIZE) * self.CACHE_GRID_SIZE,
            round(lon / self.CACHE_GRID_SIZE) * self.CACHE_GRID_SIZE
        )
    
    def _cache_key(self, lat: float, lon: float, target_time: datetime) -> str:
        """Generate unique cache key for request."""
        grid_lat, grid_lon = self._grid_key(lat, lon)
        time_key = target_time.strftime('%Y%m%d%H')
        return f"{grid_lat:.1f}_{grid_lon:.1f}_{time_key}"
    
    def _check_caches(self, cache_key: str) -> Optional[Dict]:
        """Check memory and disk caches."""
        # Memory cache (fastest)
        if cache_key in self.memory_cache:
            timestamp, data = self.memory_cache[cache_key]
            if time.time() - timestamp < self.CACHE_DURATION:
                self.stats['cache_hits'] += 1
                return data
            else:
                del self.memory_cache[cache_key]
        
        # Disk cache (persistent)
        if cache_key in self.disk_cache:
            data = self.disk_cache[cache_key]
            if time.time() - data.get('timestamp', 0) < self.CACHE_DURATION:
                self.memory_cache[cache_key] = (data['timestamp'], data)
                self.stats['cache_hits'] += 1
                return data
        
        self.stats['cache_misses'] += 1
        return None
    
    def _update_caches(self, cache_key: str, data: Dict):
        """Update both memory and disk caches."""
        cache_entry = {
            'timestamp': time.time(),
            'data': data
        }
        self.memory_cache[cache_key] = (cache_entry['timestamp'], cache_entry)
        self.disk_cache[cache_key] = cache_entry
        self.disk_cache.sync()
    
    def _linear_interpolate(self, t: float, t0: float, t1: float, 
                           v0: float, v1: float) -> float:
        """Linear interpolation between two time points."""
        if t1 == t0:
            return v0
        return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    
    def _parse_openmeteo(self, data: Dict, target_time: datetime) -> Optional[Dict]:
        """Parse Open-Meteo forecast with linear interpolation."""
        try:
            times = [datetime.fromisoformat(t.replace('Z', '+00:00')) 
                    for t in data['hourly']['time']]
            
            # Find surrounding indices
            idx = None
            for i, t in enumerate(times):
                if t >= target_time:
                    idx = i
                    break
            
            if idx is None or idx == 0:
                # Use nearest if at boundaries
                idx = min(range(len(times)), 
                         key=lambda i: abs((times[i] - target_time).total_seconds()))
                t0 = times[idx]
                t1 = times[idx]
                temp0 = data['hourly']['temperature_2m'][idx]
                temp1 = temp0
                wind0 = data['hourly']['windspeed_10m'][idx]
                wind1 = wind0
                press0 = data['hourly']['pressure_msl'][idx]
                press1 = press0
                precip0 = data['hourly']['precipitation'][idx]
                precip1 = precip0
                wind_dir0 = data['hourly']['winddirection_10m'][idx]
                wind_dir1 = wind_dir0
            else:
                t0 = times[idx-1]
                t1 = times[idx]
                temp0 = data['hourly']['temperature_2m'][idx-1]
                temp1 = data['hourly']['temperature_2m'][idx]
                wind0 = data['hourly']['windspeed_10m'][idx-1]
                wind1 = data['hourly']['windspeed_10m'][idx]
                press0 = data['hourly']['pressure_msl'][idx-1]
                press1 = data['hourly']['pressure_msl'][idx]
                precip0 = data['hourly']['precipitation'][idx-1]
                precip1 = data['hourly']['precipitation'][idx]
                wind_dir0 = data['hourly']['winddirection_10m'][idx-1]
                wind_dir1 = data['hourly']['winddirection_10m'][idx]
            
            target_seconds = target_time.timestamp()
            t0_seconds = t0.timestamp()
            t1_seconds = t1.timestamp()
            
            return {
                'temperature': self._linear_interpolate(
                    target_seconds, t0_seconds, t1_seconds, temp0, temp1),
                'wind_speed': self._linear_interpolate(
                    target_seconds, t0_seconds, t1_seconds, wind0, wind1) * 3.6,
                'wind_direction': self._linear_interpolate(
                    target_seconds, t0_seconds, t1_seconds, wind_dir0, wind_dir1),
                'pressure': self._linear_interpolate(
                    target_seconds, t0_seconds, t1_seconds, press0, press1),
                'precipitation': self._linear_interpolate(
                    target_seconds, t0_seconds, t1_seconds, precip0, precip1),
                'source': 'open-meteo',
                'confidence': 0.9
            }
        except Exception as e:
            logger.error(f"Error parsing Open-Meteo: {e}")
            return None
    
    def _fetch_api(self, api: Dict, lat: float, lon: float, 
                   target_time: datetime) -> Optional[Dict]:
        """Fetch data from single API with retries."""
        for attempt in range(api.get('retries', 1) + 1):
            try:
                start_time = time.time()
                
                # Build parameters based on API type
                if api['name'] == 'Open-Meteo':
                    params = {
                        'latitude': lat,
                        'longitude': lon,
                        'hourly': api['variables'],
                        'forecast_days': 10,
                        'timezone': 'auto'
                    }
                elif api['name'] == 'OpenWeatherMap':
                    params = {
                        'lat': lat,
                        'lon': lon,
                        'appid': api['key'],
                        'units': 'metric',
                        'cnt': 40
                    }
                else:
                    params = api.get('params', lambda lat, lon: {})(lat, lon)
                
                response = requests.get(
                    api['url'],
                    params=params,
                    timeout=api['timeout']
                )
                
                response_time = time.time() - start_time
                self.stats['api_calls'] += 1
                
                # Update rolling average
                self.stats['avg_response_time'] = (
                    0.9 * self.stats['avg_response_time'] + 0.1 * response_time
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if api['name'] == 'Open-Meteo':
                        return self._parse_openmeteo(data, target_time)
                    elif api['name'] == 'OpenWeatherMap':
                        return self._parse_openweather(data, target_time)
                    # Add other parsers as needed
                    
            except requests.Timeout:
                logger.warning(f"{api['name']} timeout (attempt {attempt+1})")
            except requests.ConnectionError:
                logger.warning(f"{api['name']} connection error (attempt {attempt+1})")
            except Exception as e:
                logger.warning(f"{api['name']} failed: {e} (attempt {attempt+1})")
            
            if attempt < api.get('retries', 1):
                time.sleep(2 ** attempt)  # Exponential backoff
        
        self.stats['api_failures'] += 1
        return None
    
    def _estimate_confidence(self, api: Dict, forecast: Dict, 
                            target_time: datetime, lat: float, lon: float) -> float:
        """Calculate confidence score based on multiple factors."""
        # Base confidence from API
        confidence = api['confidence_base']
        
        # Time horizon penalty (exponential decay)
        hours_ahead = max(0, (target_time - datetime.now()).total_seconds() / 3600)
        confidence *= math.exp(-hours_ahead / 48)  # 50% confidence at 48 hours
        
        # Grid distance penalty
        grid_lat, grid_lon = self._grid_key(lat, lon)
        lat_diff = abs(lat - grid_lat) * 111  # km per degree
        lon_diff = abs(lon - grid_lon) * 111 * math.cos(math.radians(lat))
        distance_km = math.sqrt(lat_diff**2 + lon_diff**2)
        confidence *= math.exp(-distance_km / 100)  # 50% penalty at 100km
        
        # Forecast internal consistency
        if 'ensemble' in forecast:
            spread = forecast['ensemble'].get('spread', 0.3)
            confidence *= (1 - min(spread, 0.5))
        
        return max(0.3, min(0.98, confidence))  # Clamp between 0.3 and 0.98
    
    def _physics_forecast(self, lat: float, lon: float, 
                          target_time: datetime) -> Dict:
        """Enhanced physics-based forecast with wave growth model."""
        hours_ahead = max(0, (target_time - datetime.now()).total_seconds() / 3600)
        abs_lat = abs(lat)
        month = target_time.month
        is_northern = lat >= 0
        
        # 1. Temperature from climatology
        if abs_lat < 10:
            base_temp = 28
            seasonal_amp = 0
        elif abs_lat < 30:
            base_temp = 24
            seasonal_amp = 4
        elif abs_lat < 60:
            base_temp = 15
            seasonal_amp = 8
        else:
            base_temp = 0
            seasonal_amp = 12
        
        # Seasonal adjustment
        seasonal = seasonal_amp * math.sin(2 * math.pi * (month - 7) / 12)
        
        # Diurnal cycle
        hour = target_time.hour
        diurnal = 3 * math.sin(2 * math.pi * (hour - 14) / 24)
        
        temperature = base_temp + seasonal + diurnal
        
        # 2. Wind speed and direction
        if abs_lat < 10:  # Doldrums
            wind_speed = 8 + 5 * math.sin(2 * math.pi * (hour - 12) / 24)
            wind_dir = 90  # Variable
        elif abs_lat < 30:  # Trade winds
            wind_speed = 20 + 3 * math.sin(2 * math.pi * (hour - 14) / 24)
            wind_dir = 60 if is_northern else 300
        elif abs_lat < 60:  # Westerlies
            wind_speed = 28 + 7 * math.sin(2 * math.pi * (hour - 15) / 24)
            wind_dir = 240 if is_northern else 300
        else:  # Polar easterlies
            wind_speed = 18 + 5 * math.sin(2 * math.pi * (hour - 12) / 24)
            wind_dir = 90 if is_northern else 270
        
        # Seasonal wind adjustment
        if month in [12, 1, 2]:  # Winter
            wind_speed *= 1.2 if abs_lat > 30 else 1.0
        elif month in [6, 7, 8]:  # Summer
            wind_speed *= 0.8 if abs_lat > 30 else 1.0
        
        # Fetch-limited significant wave height (CERC/SPM form), not a JONSWAP
        # spectrum. An earlier version used 0.041, the JONSWAP peak-enhancement
        # factor, in place of the fetch-limited height coefficient.
        fetch_km = 100
        u10 = max(wind_speed / 3.6, 0.5)  # forecast wind is km/h
        g = self.G
        f_tilde = g * fetch_km * 1000 / u10**2
        hs = (u10 ** 2 / g) * 0.0016 * f_tilde ** 0.5
        wave_height = min(max(hs, 0.0), 8.0)
        
        # 4. Pressure (simplified)
        pressure = 1013 + 10 * math.sin(2 * math.pi * (month - 1) / 12)
        
        # 5. Uncertainty quantification
        uncertainty = 0.1 + 0.02 * hours_ahead / 24
        confidence = max(0.5, 1 - hours_ahead / (24 * 10))
        
        # 6. Ensemble spread (Monte Carlo)
        ensemble_size = 10
        ensemble = []
        for i in range(ensemble_size):
            member = {
                'temperature': temperature + np.random.normal(0, 2 * uncertainty),
                'wind_speed': max(0, wind_speed + np.random.normal(0, 5 * uncertainty)),
                'wind_direction': (wind_dir + np.random.normal(0, 30 * uncertainty)) % 360,
                'wave_height': max(0, wave_height + np.random.normal(0, 0.5 * uncertainty)),
                'pressure': pressure + np.random.normal(0, 10 * uncertainty),
                'member_id': i
            }
            ensemble.append(member)
        
        # Calculate ensemble statistics
        temps = [m['temperature'] for m in ensemble]
        winds = [m['wind_speed'] for m in ensemble]
        waves = [m['wave_height'] for m in ensemble]
        
        return {
            'temperature': round(temperature, 1),
            'wind_speed': round(wind_speed, 1),
            'wind_direction': round(wind_dir),
            'wave_height': round(wave_height, 1),
            'pressure': round(pressure),
            'precipitation': round(max(0, wind_speed / 20), 1),
            'source': 'physics-4d',
            'confidence': round(confidence, 2),
            'uncertainty': round(uncertainty, 2),
            'ensemble': {
                'mean_temp': round(np.mean(temps), 1),
                'std_temp': round(np.std(temps), 1),
                'mean_wind': round(np.mean(winds), 1),
                'std_wind': round(np.std(winds), 1),
                'mean_wave': round(np.mean(waves), 1),
                'std_wave': round(np.std(waves), 1),
                'spread': round(np.std(winds) / (np.mean(winds) + 0.1), 2),
                'members': ensemble_size
            }
        }
    
    def get_forecast_at_time(self, lat: float, lon: float, 
                             target_time: datetime,
                             ensemble_size: int = 1) -> Dict:
        """
        Get weather forecast for specific future time with ensemble.
        
        Args:
            lat: Latitude (degrees)
            lon: Longitude (degrees)
            target_time: Target datetime
            ensemble_size: Number of ensemble members (1 = deterministic)
            
        Returns:
            Dictionary with forecast data and confidence scores
        """
        try:
            # Validate inputs
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError(f"Invalid coordinates: ({lat}, {lon})")
            
            lat_float = float(lat)
            lon_float = float(lon)
            cache_key = self._cache_key(lat_float, lon_float, target_time)
            
            # Check caches
            cached = self._check_caches(cache_key)
            if cached is not None:
                return cached['data']
            
            # Try APIs in parallel for first N sources
            futures = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                for api in self.active_apis[:3]:  # Limit parallel requests
                    future = executor.submit(
                        self._fetch_api, api, lat_float, lon_float, target_time
                    )
                    futures.append((api, future))
                
                # Process results as they complete
                best_forecast = None
                best_confidence = 0
                
                for api, future in futures:
                    try:
                        forecast = future.result(timeout=api['timeout'] + 1)
                        if forecast:
                            confidence = self._estimate_confidence(
                                api, forecast, target_time, lat_float, lon_float
                            )
                            forecast['confidence'] = confidence
                            
                            if confidence > best_confidence:
                                best_confidence = confidence
                                best_forecast = forecast
                                best_forecast['source'] = api['name']
                    except Exception as e:
                        logger.error(f"Error processing {api['name']}: {e}")
            
            # Fallback to physics-based if all APIs failed
            if best_forecast is None:
                logger.info(f"Using physics-based forecast for {lat:.1f}, {lon:.1f}")
                best_forecast = self._physics_forecast(lat_float, lon_float, target_time)
            
            # Add ensemble if requested
            if ensemble_size > 1 and best_forecast:
                best_forecast = self._generate_ensemble(best_forecast, ensemble_size)
            
            # Cache result
            self._update_caches(cache_key, best_forecast)
            
            return best_forecast
            
        except Exception as e:
            logger.error(f"Fatal error in get_forecast_at_time: {e}")
            return self._physics_forecast(lat, lon, target_time)
    
    def _generate_ensemble(self, base_forecast: Dict, size: int) -> Dict:
        """Generate ensemble members around base forecast."""
        ensemble = base_forecast.copy()
        members = []
        
        uncertainty = base_forecast.get('uncertainty', 0.1)
        
        for i in range(size):
            member = base_forecast.copy()
            member['temperature'] += np.random.normal(0, 2 * uncertainty)
            member['wind_speed'] += np.random.normal(0, 5 * uncertainty)
            member['wind_speed'] = max(0, member['wind_speed'])
            member['wave_height'] += np.random.normal(0, 0.5 * uncertainty)
            member['wave_height'] = max(0, member['wave_height'])
            member['pressure'] += np.random.normal(0, 10 * uncertainty)
            member['ensemble_member'] = i + 1
            members.append(member)
        
        # Calculate ensemble statistics
        temps = [m['temperature'] for m in members]
        winds = [m['wind_speed'] for m in members]
        waves = [m['wave_height'] for m in members]
        
        ensemble['ensemble'] = {
            'mean_temp': round(np.mean(temps), 1),
            'std_temp': round(np.std(temps), 1),
            'min_temp': round(min(temps), 1),
            'max_temp': round(max(temps), 1),
            'mean_wind': round(np.mean(winds), 1),
            'std_wind': round(np.std(winds), 1),
            'min_wind': round(min(winds), 1),
            'max_wind': round(max(winds), 1),
            'mean_wave': round(np.mean(waves), 1),
            'std_wave': round(np.std(waves), 1),
            'members': members,
            'spread': round(np.std(winds) / (np.mean(winds) + 0.1), 2)
        }
        
        return ensemble
    
    def weather_impact_on_speed(self, wind_speed: float, wave_height: float,
                                wind_direction: float, heading: float) -> float:
        """
        Calculate weather impact on vessel speed.
        
        Returns speed multiplier (1.0 = no impact, <1.0 = slowdown)
        """
        # Head wind/sea component
        angle_diff = abs((wind_direction - heading + 180) % 360 - 180)
        
        # Wind impact (Beaufort scale based)
        if wind_speed < 20:
            wind_factor = 1.0
        elif wind_speed < 30:
            wind_factor = 0.95
        elif wind_speed < 40:
            wind_factor = 0.88
        elif wind_speed < 50:
            wind_factor = 0.78
        elif wind_speed < 60:
            wind_factor = 0.65
        else:
            wind_factor = 0.50
        
        # Wave impact
        if wave_height < 1.5:
            wave_factor = 1.0
        elif wave_height < 2.5:
            wave_factor = 0.92
        elif wave_height < 4.0:
            wave_factor = 0.80
        elif wave_height < 6.0:
            wave_factor = 0.65
        else:
            wave_factor = 0.45
        
        # Combine based on direction
        if angle_diff < 45:  # Head seas
            factor = min(wind_factor, wave_factor)
        elif angle_diff < 135:  # Beam seas
            factor = 0.95 * min(wind_factor, wave_factor)
        else:  # Following seas
            factor = 1.0  # Following seas can actually help
        
        return max(0.3, min(1.0, factor))
    
    def route_timeline_4d(self, route_coords: List[Tuple], 
                          departure_time: datetime,
                          speed_knots: float = 20,
                          ensemble_size: int = 1,
                          parallel: bool = True) -> Dict:
        """
        Generate 4D weather timeline for entire journey.
        
        Args:
            route_coords: List of (lat, lon) coordinates
            departure_time: Departure datetime (should be timezone-naive)
            speed_knots: Nominal vessel speed (knots)
            ensemble_size: Number of ensemble members
            parallel: Use parallel processing for segments
            
        Returns:
            Dictionary with timeline and ensemble statistics
        """
        # FIX: Ensure departure_time is timezone-naive
        if departure_time.tzinfo is not None:
            departure_time = departure_time.replace(tzinfo=None)
        
        timeline = []
        cumulative_hours = 0
        speed_kmh = speed_knots * 1.852
        
        # Calculate total distance and duration
        total_distance = 0
        segment_distances = []
        for i in range(1, len(route_coords)):
            dist = self._haversine(route_coords[i-1], route_coords[i])
            segment_distances.append(dist)
            total_distance += dist
        
        total_hours = total_distance / speed_kmh
        total_days = total_hours / 24
        
        logger.info(f"\n🌐 4D Route Timeline - {len(route_coords)-1} segments")
        logger.info(f"   Total distance: {total_distance:.0f} km")
        logger.info(f"   Nominal speed: {speed_knots:.1f} knots")
        logger.info(f"   Base duration: {total_days:.1f} days ({total_hours:.1f} hours)")
        
        # Prepare segment data
        segments = []
        cumulative = 0
        for i in range(1, len(route_coords)):
            seg_dist = segment_distances[i-1]
            seg_hours = seg_dist / speed_kmh
            cumulative += seg_hours
            arrival = departure_time + timedelta(hours=cumulative)
            
            segments.append({
                'index': i,
                'from_coord': route_coords[i-1],
                'to_coord': route_coords[i],
                'distance_km': seg_dist,
                'base_hours': seg_hours,
                'arrival_time': arrival,
                'lat': route_coords[i][0],
                'lon': route_coords[i][1]
            })
        
        # Fetch forecasts in parallel if requested
        if parallel and len(segments) > 3:
            forecasts = [None] * len(segments)
            
            with ThreadPoolExecutor(max_workers=min(10, len(segments))) as executor:
                future_to_idx = {
                    executor.submit(
                        self.get_forecast_at_time,
                        seg['lat'], seg['lon'],
                        seg['arrival_time'],
                        ensemble_size
                    ): idx for idx, seg in enumerate(segments)
                }
                
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        forecasts[idx] = future.result()
                    except Exception as e:
                        logger.error(f"Segment {idx} forecast failed: {e}")
                        forecasts[idx] = self._physics_forecast(
                            segments[idx]['lat'], segments[idx]['lon'],
                            segments[idx]['arrival_time']
                        )
        else:
            # Sequential processing
            forecasts = []
            for seg in segments:
                forecast = self.get_forecast_at_time(
                    seg['lat'], seg['lon'], seg['arrival_time'], ensemble_size
                )
                forecasts.append(forecast)
        
        # Build timeline with weather impacts
        adjusted_total_hours = 0
        weather_impacts = []
        
        for i, (seg, forecast) in enumerate(zip(segments, forecasts)):
            # Calculate weather impact on speed
            heading = self._calculate_bearing(
                seg['from_coord'][0], seg['from_coord'][1],
                seg['to_coord'][0], seg['to_coord'][1]
            )
            
            speed_factor = self.weather_impact_on_speed(
                forecast.get('wind_speed', 15),
                forecast.get('wave_height', 1.5),
                forecast.get('wind_direction', 180),
                heading
            )
            
            # Adjust segment duration
            adjusted_hours = seg['base_hours'] / speed_factor
            adjusted_total_hours += adjusted_hours
            
            # Calculate fuel multiplier (simplified)
            if speed_factor < 0.7:
                fuel_mult = 1.5  # Severe slowdown increases fuel per hour
            elif speed_factor < 0.85:
                fuel_mult = 1.25
            elif speed_factor < 0.95:
                fuel_mult = 1.1
            else:
                fuel_mult = 1.0
            
            weather_impacts.append({
                'segment': i + 1,
                'speed_factor': round(speed_factor, 2),
                'fuel_multiplier': fuel_mult,
                'adjusted_hours': round(adjusted_hours, 2)
            })
            
            timeline.append({
                'segment': i + 1,
                'from_coord': seg['from_coord'],
                'to_coord': seg['to_coord'],
                'distance_km': round(seg['distance_km'], 1),
                'base_hours': round(seg['base_hours'], 2),
                'adjusted_hours': round(adjusted_hours, 2),
                'arrival_time': seg['arrival_time'].isoformat(),
                'day': round((i + 1) * seg['base_hours'] / 24, 2),
                'forecast': forecast,
                'heading': round(heading),
                'weather_impact': speed_factor
            })
        
        # Calculate ensemble confidence
        confidences = [seg['forecast'].get('confidence', 0.5) for seg in timeline]
        ensemble_confidence = sum(confidences) / len(confidences)
        
        # Total impact statistics
        total_delay = adjusted_total_hours - total_hours
        avg_speed_factor = sum(wi['speed_factor'] for wi in weather_impacts) / len(weather_impacts)
        
        logger.info(f"\n📊 4D Impact Analysis:")
        logger.info(f"   Adjusted duration: {adjusted_total_hours/24:.1f} days "
                   f"({adjusted_total_hours:.1f} hours)")
        logger.info(f"   Weather delay: {total_delay:.1f} hours "
                   f"({total_delay/24:.1f} days)")
        logger.info(f"   Avg speed factor: {avg_speed_factor:.2f}")
        logger.info(f"   Ensemble confidence: {ensemble_confidence*100:.0f}%")
        
        return {
            'timeline': timeline,
            'total_days': round(adjusted_total_hours / 24, 1),
            'total_hours': round(adjusted_total_hours, 1),
            'base_days': round(total_days, 1),
            'base_hours': round(total_hours, 1),
            'total_distance': round(total_distance, 1),
            'departure_time': departure_time.isoformat(),
            'ensemble_confidence': round(ensemble_confidence, 2),
            'weather_impacts': weather_impacts,
            'total_delay_hours': round(total_delay, 1),
            'avg_speed_factor': round(avg_speed_factor, 2),
            'stats': self.stats
        }
    
    def _haversine(self, p1: Tuple[float, float], 
                   p2: Tuple[float, float]) -> float:
        """Haversine distance in km using numpy for speed."""
        lat1, lon1 = np.radians(p1)
        lat2, lon2 = np.radians(p2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        return 6371 * c
    
    def _calculate_bearing(self, lat1: float, lon1: float,
                          lat2: float, lon2: float) -> float:
        """Calculate initial bearing from point1 to point2."""
        lat1, lon1 = np.radians(lat1), np.radians(lon1)
        lat2, lon2 = np.radians(lat2), np.radians(lon2)
        
        dlon = lon2 - lon1
        
        x = np.sin(dlon) * np.cos(lat2)
        y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        
        bearing = np.degrees(np.arctan2(x, y))
        return (bearing + 360) % 360
    
    def get_stats(self) -> Dict:
        """Return performance statistics."""
        return self.stats.copy()
    
    def clear_cache(self):
        """Clear all caches."""
        self.memory_cache.clear()
        self.disk_cache.clear()
        self.disk_cache.sync()
        logger.info("Cache cleared")

# Singleton instance
forecast_4d = Forecast4D()