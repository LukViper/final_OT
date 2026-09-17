"""
Lunar and Tidal Model
Calculates moon phase and tidal effects on shipping
"""

import math
from datetime import datetime, timedelta
from typing import Dict, Tuple

class LunarTideModel:
    """Moon phase and tidal height predictions"""
    
    def __init__(self):
        # Lunar constants
        self.LUNAR_MONTH = 29.53058867  # days
        self.SYNODIC_MONTH = 29.530589
        self.TROPICAL_YEAR = 365.24219878
        
    def moon_phase(self, date: datetime) -> Dict:
        """
        Calculate current moon phase
        Returns: Phase name, illumination %, age in days
        """
        # Known new moon: 2000-01-06 18:14 UTC
        known_new_moon = datetime(2000, 1, 6, 18, 14)
        
        # Days since known new moon
        days_diff = (date - known_new_moon).total_seconds() / 86400.0
        
        # Moon age in current cycle
        moon_age = days_diff % self.LUNAR_MONTH
        
        # Illumination percentage (0-100%)
        illumination = 50 * (1 - math.cos(2 * math.pi * moon_age / self.LUNAR_MONTH))
        
        # Phase name
        if moon_age < 1.0:
            phase = "New Moon"
            phase_icon = "moon"
        elif moon_age < 7.4:
            phase = "Waxing Crescent"
            phase_icon = "moon"
        elif moon_age < 8.4:
            phase = "First Quarter"
            phase_icon = "moon"
        elif moon_age < 14.8:
            phase = "Waxing Gibbous"
            phase_icon = "moon"
        elif moon_age < 15.8:
            phase = "Full Moon"
            phase_icon = "moon"
        elif moon_age < 22.1:
            phase = "Waning Gibbous"
            phase_icon = "moon"
        elif moon_age < 23.1:
            phase = "Last Quarter"
            phase_icon = "moon"
        else:
            phase = "Waning Crescent"
            phase_icon = "moon"
        
        # Tidal range factor (spring/neap)
        # Spring tides at new/full moon (factor 1.2), neap at quarters (factor 0.8)
        tidal_factor = 1.0 + 0.2 * math.cos(2 * math.pi * (moon_age - 7.4) / 7.4)
        
        return {
            'phase': phase,
            'icon': phase_icon,
            'illumination': round(illumination, 1),
            'age_days': round(moon_age, 1),
            'tidal_factor': round(tidal_factor, 2),
            'next_full_moon': (date + timedelta(days=(15.8 - moon_age))).strftime('%Y-%m-%d')
        }
    
    def tide_height(self, lat: float, lon: float, date: datetime) -> Dict:
        """
        Estimate tidal height at location
        Simplified harmonic method
        """
        moon = self.moon_phase(date)
        
        # Lunar declination effect
        declination = 23.5 * math.sin(2 * math.pi * (date.timetuple().tm_yday - 80) / 365)
        
        # Latitude factor
        lat_factor = math.cos(math.radians(abs(lat) - declination))
        
        # Time of day factor (simplified M2 constituent)
        lunar_hour = (date.hour + date.minute/60) * 1.035  # Moon day is longer
        time_factor = math.cos(2 * math.pi * lunar_hour / 24.8)
        
        # Base tide range (meters) - varies by location
        if abs(lat) < 30:
            base_range = 1.5  # Tropical
        elif abs(lat) < 60:
            base_range = 3.0  # Temperate
        else:
            base_range = 2.0  # Polar
        
        # Calculate height
        height = base_range * moon['tidal_factor'] * lat_factor * time_factor
        
        # Determine tide state
        if height > 0.3:
            state = "High Tide" if time_factor > 0 else "Flood"
        elif height < -0.3:
            state = "Low Tide" if time_factor < 0 else "Ebb"
        else:
            state = "Slack Water"
        
        return {
            'height_meters': round(height, 2),
            'state': state,
            'base_range': base_range,
            'moon_factor': moon['tidal_factor'],
            'lat_factor': round(lat_factor, 2),
            'time_factor': round(time_factor, 2),
            'moon_phase': moon['phase'],
            'moon_icon': moon['icon']
        }
    
    def sailing_conditions(self, lat: float, lon: float, date: datetime) -> Dict:
        """
        Get sailing conditions based on lunar/tidal effects
        """
        tide = self.tide_height(lat, lon, date)
        moon = self.moon_phase(date)
        
        # Determine if conditions are favorable
        if abs(tide['height_meters']) < 0.5 and tide['state'] == "Slack Water":
            tidal_rating = "Excellent - Slack water"
        elif abs(tide['height_meters']) < 1.0:
            tidal_rating = "Good - Moderate currents"
        else:
            tidal_rating = "Caution - Strong currents"
        
        # Lunar illumination for night sailing
        if moon['illumination'] > 80:
            night_rating = "Excellent visibility at night"
        elif moon['illumination'] > 30:
            night_rating = "Good night visibility"
        else:
            night_rating = "Dark night - use navigation lights"
        
        return {
            'tidal_conditions': tidal_rating,
            'night_visibility': night_rating,
            'current_tide': tide,
            'moon_phase': moon,
            'recommendation': self._recommendation(tide, moon)
        }
    
    def _recommendation(self, tide: Dict, moon: Dict) -> str:
        return (
            f"Scenario only: tide state {tide['state']}, moon {moon['phase']}, "
            f"illumination {moon['illumination']}%. Not a tide prediction and not an entry clearance."
        )

# Singleton
lunar_tides = LunarTideModel()