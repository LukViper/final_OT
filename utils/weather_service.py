import os
import requests
import time
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import ssl
import urllib3

# Disable SSL warnings if needed (not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Maritime weather service with dual-source API integration
    """
    
    MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"
    MARINE_PARAMS = (
        "wave_height,wave_direction,wave_period,"
        "swell_wave_height,swell_wave_direction,swell_wave_period,"
        "ocean_current_velocity,ocean_current_direction,"
        "sea_surface_temperature"
    )
    
    # Alternative API endpoints (some might work when others fail)
    ALT_API_URLS = [
        "https://api.open-meteo.com/v1/forecast",
        "https://open-meteo.com/v1/forecast",
        "https://marine-api.open-meteo.com/v1/marine"
    ]

    def __init__(self):
        self.openweather_key = os.getenv('OPENWEATHER_API_KEY', '').strip()
        self.openweather_url = "https://api.openweathermap.org/data/2.5"
        self.cache: Dict[str, Tuple[float, Dict]] = {}
        self.cache_duration = 1800  # 30 minutes
        self.last_request_time = 0.0
        self.min_request_interval = 1.0
        self.max_retries = 2
        self.base_retry_delay = 1.0
        self.session = requests.Session()
        
        # Configure session to handle SSL better
        self.session.verify = True
        self.session.headers.update({
            'User-Agent': 'MaritimeRouteOptimizer/1.0'
        })
        
        if not self.openweather_key:
            print("⚠️  No OPENWEATHER_API_KEY found. Using fallback data.")
        else:
            masked = self.openweather_key[:4] + "****" + self.openweather_key[-4:]
            print(f"✅ OpenWeather API key loaded ({masked})")
        
        print("✅ Weather Service initialized (fallback mode enabled)")

    def get_marine_weather(self, lat: float, lon: float) -> Dict:
        """Get weather data with multiple fallback options"""
        try:
            # SAFETY: Check for None values
            if lat is None or lon is None:
                print(f"  ⚠️ Invalid coordinates received: lat={lat}, lon={lon}")
                return self._generate_fallback_weather(0, 0)
            
            # SAFETY: Convert to float and handle potential errors
            try:
                lat_float = float(lat)
                lon_float = float(lon)
            except (TypeError, ValueError):
                print(f"  ⚠️ Could not convert coordinates: {lat}, {lon}")
                return self._generate_fallback_weather(0, 0)
            
            # SAFETY: Create cache key safely
            try:
                cache_key = f"weather_{lat_float:.2f}_{lon_float:.2f}"
            except (TypeError, ValueError):
                cache_key = f"weather_{hash((lat_float, lon_float))}"
            
            # Check cache
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
            
            # Try multiple APIs
            weather = self._fetch_with_fallback(lat_float, lon_float)
            
            # If all APIs fail, use deterministic fallback
            if weather is None:
                print(f"  ℹ️ Using fallback weather for {lat_float:.1f}, {lon_float:.1f}")
                weather = self._generate_fallback_weather(lat_float, lon_float)
            
            self._set_cache(cache_key, weather)
            return weather
            
        except Exception as e:
            print(f"  ⚠️ Weather error in get_marine_weather: {e}")
            return self._generate_fallback_weather(0, 0)
    
    def _fetch_with_fallback(self, lat: float, lon: float) -> Optional[Dict]:
        """Try multiple API endpoints with fallback"""
        
        # SAFETY: Ensure lat/lon are valid numbers
        if lat is None or lon is None:
            return None
        
        # SAFETY: Round safely
        try:
            lat_rounded = round(float(lat), 2) if lat is not None else 0
            lon_rounded = round(float(lon), 2) if lon is not None else 0
        except (TypeError, ValueError) as e:
            print(f"  ⚠️ Error rounding coordinates: {e}")
            return None
        
        # Try Open-Meteo Marine first
        try:
            params = {
                'latitude': lat_rounded,
                'longitude': lon_rounded,
                'current': self.MARINE_PARAMS,
                'timezone': 'auto'
            }
            
            response = self.session.get(
                self.MARINE_API_URL,
                params=params,
                timeout=8,
                verify=False  # Temporary fix for SSL issues
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_marine(data)
            else:
                print(f"  ⚠️ Marine API returned {response.status_code}")
                
        except Exception as e:
            print(f"  ⚠️ Marine API failed: {e}")
        
        # Try standard forecast API as backup
        try:
            params = {
                'latitude': lat_rounded,
                'longitude': lon_rounded,
                'hourly': ['temperature_2m', 'windspeed_10m'],
                'forecast_days': 1,
                'timezone': 'auto'
            }
            
            response = self.session.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params,
                timeout=8,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_standard_forecast(data)
            else:
                print(f"  ⚠️ Forecast API returned {response.status_code}")
                
        except Exception as e:
            print(f"  ⚠️ Forecast API failed: {e}")
        
        return None
    
    def _parse_standard_forecast(self, data: Dict) -> Optional[Dict]:
        """Parse standard forecast data"""
        try:
            current = data.get('hourly', {})
            if current and len(current.get('temperature_2m', [])) > 0:
                # SAFETY: Get values with defaults
                temp = current['temperature_2m'][0]
                if temp is None:
                    temp = 20
                
                wind_speed = current.get('windspeed_10m', [15])[0]
                if wind_speed is None:
                    wind_speed = 15
                    
                return {
                    'temperature': float(temp),
                    'wind_speed': float(wind_speed) * 3.6,
                    'wind_direction': 180,
                    'wave_height': 1.5,
                    'precipitation': 0,
                    'visibility': 10,
                    'condition': 'moderate',
                    'pressure': 1013,
                    'humidity': 70,
                    'cloud_cover': 50,
                    'source': 'forecast-api'
                }
        except Exception as e:
            print(f"  ⚠️ Error parsing forecast: {e}")
        return None

    def _parse_marine(self, data: Dict) -> Optional[Dict]:
        """Parse Open-Meteo Marine API response"""
        try:
            current = data.get('current', {})
            if not current:
                return None
                
            # SAFETY: Safely get values with defaults and type conversion
            wind_speed = current.get('wind_speed')
            if wind_speed is None:
                wind_speed = 15
            try:
                wind_speed = float(wind_speed)
            except (TypeError, ValueError):
                wind_speed = 15
                
            wave_height = current.get('wave_height')
            if wave_height is None:
                wave_height = 1.5
            try:
                wave_height = float(wave_height)
            except (TypeError, ValueError):
                wave_height = 1.5
                
            wind_direction = current.get('wind_direction', 180)
            if wind_direction is None:
                wind_direction = 180
            try:
                wind_direction = float(wind_direction)
            except (TypeError, ValueError):
                wind_direction = 180
                
            # Add more safety for other fields
            swell_wave_height = current.get('swell_wave_height')
            if swell_wave_height is None:
                swell_wave_height = 1.0
            try:
                swell_wave_height = float(swell_wave_height)
            except (TypeError, ValueError):
                swell_wave_height = 1.0
                
            ocean_current = current.get('ocean_current_velocity')
            if ocean_current is None:
                ocean_current = 0.5
            try:
                ocean_current = float(ocean_current)
            except (TypeError, ValueError):
                ocean_current = 0.5
                
            sea_temp = current.get('sea_surface_temperature')
            if sea_temp is None:
                sea_temp = 20
            try:
                sea_temp = float(sea_temp)
            except (TypeError, ValueError):
                sea_temp = 20
            
            return {
                'temperature': 20.0,
                'wind_speed': wind_speed,
                'wind_direction': wind_direction,
                'wave_height': wave_height,
                'swell_wave_height': swell_wave_height,
                'ocean_current_velocity': ocean_current,
                'sea_surface_temperature': sea_temp,
                'source': 'open-meteo-marine'
            }
        except Exception as e:
            print(f"  ⚠️ Error parsing marine data: {e}")
            return None

    def _generate_fallback_weather(self, lat: float, lon: float) -> Dict:
        """Deterministic fallback using latitude and month"""
        try:
            from datetime import datetime
            month = datetime.now().month
            
            # SAFETY: Handle None or invalid lat
            try:
                if lat is None or lon is None:
                    abs_lat = 20
                else:
                    abs_lat = abs(float(lat))
            except (TypeError, ValueError):
                abs_lat = 20  # Default to temperate
            
            # Temperature by latitude
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
            
            # SAFETY: Round safely
            try:
                temp_rounded = round(temp, 1)
                wind_rounded = round(wind, 1)
                wave_rounded = round(wave, 1)
                precip_rounded = round(max(0, wind / 20), 1)
            except:
                temp_rounded = 20
                wind_rounded = 15
                wave_rounded = 1.5
                precip_rounded = 0
            
            return {
                'temperature': temp_rounded,
                'wind_speed': wind_rounded,
                'wind_direction': 180,
                'wave_height': wave_rounded,
                'precipitation': precip_rounded,
                'visibility': 10,
                'condition': 'moderate',
                'pressure': 1013,
                'humidity': 70,
                'cloud_cover': 50,
                'source': 'fallback-climatology'
            }
        except Exception as e:
            print(f"  ⚠️ Error in fallback weather: {e}")
            # Ultimate fallback
            return {
                'temperature': 20,
                'wind_speed': 15,
                'wind_direction': 180,
                'wave_height': 1.5,
                'precipitation': 0,
                'visibility': 10,
                'condition': 'moderate',
                'pressure': 1013,
                'humidity': 70,
                'cloud_cover': 50,
                'source': 'fallback-default'
            }

    def get_route_weather(self, route_coordinates: List[Tuple[float, float]]) -> Dict:
        """Analyze weather along route"""
        try:
            if not route_coordinates:
                return self._get_default_route_weather()
            
            weather_points = []
            total_impact = 0.0
            
            # Sample points along route
            num_points = min(8, len(route_coordinates))
            step = max(1, len(route_coordinates) // num_points)
            
            print(f"\n🌤️ Fetching weather for {num_points} points along route...")
            
            points_fetched = 0
            for i in range(0, len(route_coordinates), step):
                lat, lon = route_coordinates[i]
                
                # SAFETY: Skip invalid coordinates
                if lat is None or lon is None:
                    continue
                    
                weather = self.get_marine_weather(lat, lon)
                
                # SAFETY: Get values with defaults
                wind = weather.get('wind_speed', 15)
                if wind is None:
                    wind = 15
                wave = weather.get('wave_height', 1.5)
                if wave is None:
                    wave = 1.5
                
                # Calculate impact score
                impact = (wind / 20) + (wave * 1.5)
                impact = max(1, min(10, impact))
                
                # SAFETY: Round safely
                try:
                    impact_rounded = round(impact, 1)
                except:
                    impact_rounded = 3.0
                
                weather_points.append({
                    'coordinates': [lat, lon],
                    'weather': weather,
                    'impact_score': impact_rounded
                })
                total_impact += impact
                points_fetched += 1
            
            if points_fetched == 0:
                return self._get_default_route_weather()
            
            avg_impact = total_impact / points_fetched
            
            # SAFETY: Round safely
            try:
                avg_impact_rounded = round(avg_impact, 1)
                max_impact = round(max(p['impact_score'] for p in weather_points), 2)
                min_impact = round(min(p['impact_score'] for p in weather_points), 2)
            except:
                avg_impact_rounded = 3.0
                max_impact = 3.0
                min_impact = 3.0
            
            return {
                'weather_points': weather_points,
                'average_impact': avg_impact_rounded,
                'overall_condition': self._impact_to_condition(avg_impact),
                'recommendation': self._get_recommendation(avg_impact),
                'statistics': {
                    'average_impact': avg_impact_rounded,
                    'max_impact': max_impact,
                    'min_impact': min_impact
                }
            }
            
        except Exception as e:
            print(f"⚠️ Route weather error: {e}")
            return self._get_default_route_weather()
    
    def _impact_to_condition(self, score: float) -> str:
        if score < 2.5: return "Excellent"
        if score < 4.0: return "Good"
        if score < 6.0: return "Moderate"
        if score < 8.0: return "Poor"
        return "Dangerous"
    
    def _get_recommendation(self, avg_impact: float) -> str:
        if avg_impact < 3:
            return "✅ Favorable conditions along entire route"
        elif avg_impact < 5:
            return "👍 Normal sailing conditions - proceed as planned"
        elif avg_impact < 7:
            return "⚠️ Moderate weather - consider speed adjustments"
        else:
            return "⛈️ Rough weather expected - consider delaying departure"
    
    def _get_default_route_weather(self) -> Dict:
        return {
            'weather_points': [],
            'average_impact': 3.0,
            'overall_condition': "Moderate",
            'recommendation': "Using climatology data (weather API unavailable)",
            'statistics': {
                'average_impact': 3.0,
                'max_impact': 3.0,
                'min_impact': 3.0
            }
        }
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            ts, data = self.cache[key]
            if time.time() - ts < self.cache_duration:
                return data
        return None
    
    def _set_cache(self, key: str, data: Dict):
        self.cache[key] = (time.time(), data)


# Singleton instance
weather_service = WeatherService()