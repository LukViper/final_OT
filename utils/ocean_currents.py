"""
Ocean Current Model
Major current systems and eddies
"""

import math
from typing import Dict, Tuple, List

class OceanCurrentModel:
    """Realistic ocean currents and eddies"""
    
    def __init__(self):
        # Major current systems
        self.currents = {
            # Name: (center_lat, center_lon, strength, direction, radius)
            'Gulf_Stream': {
                'type': 'western_boundary',
                'points': [
                    (25, -80, 2.5, 60),   # Florida Strait
                    (35, -75, 2.0, 45),   # Cape Hatteras
                    (40, -50, 1.5, 30),   # North Atlantic
                ],
                'seasonal_factor': {
                    'winter': 1.2,
                    'summer': 0.9
                }
            },
            'Kuroshio': {
                'type': 'western_boundary',
                'points': [
                    (20, 120, 2.2, 30),   # Philippines
                    (30, 135, 1.8, 45),   # Japan
                    (40, 145, 1.2, 60),   # North Pacific
                ],
                'seasonal_factor': {
                    'winter': 1.1,
                    'summer': 1.0
                }
            },
            'Agulhas': {
                'type': 'western_boundary',
                'points': [
                    (-30, 32, 2.0, 40),   # Mozambique Channel
                    (-35, 28, 2.5, 50),   # Agulhas Current
                    (-40, 25, 1.0, 60),   # Return Current
                ],
                'seasonal_factor': {
                    'winter': 1.3,
                    'summer': 0.8
                }
            },
            'Equatorial': {
                'type': 'zonal',
                'points': [
                    (0, -30, 0.8, 270),   # Atlantic
                    (0, 150, 0.9, 270),   # Pacific
                    (5, 90, 1.1, 90),     # Indian Monsoon
                ],
                'seasonal_factor': {
                    'winter': 0.9,
                    'summer': 1.2
                }
            },
            'Canary': {
                'type': 'eastern_boundary',
                'points': [
                    (30, -15, 0.5, 180),  # Off Morocco
                    (20, -20, 0.4, 180),  # Off Senegal
                ],
                'seasonal_factor': {
                    'winter': 1.0,
                    'summer': 1.1
                }
            }
        }
        
        # Eddies (mesoscale features)
        self.eddies = [
            {'center': (35, -70), 'strength': 0.8, 'radius': 200, 'direction': 90},
            {'center': (40, 150), 'strength': 0.6, 'radius': 150, 'direction': -90},
        ]
    
    def get_current(self, lat: float, lon: float, month: int) -> Dict:
        """
        Get current speed and direction at location
        """
        # Start with zero
        u_total = 0.0  # East component (m/s)
        v_total = 0.0  # North component (m/s)
        
        # Season factor
        season = 'winter' if month in [12, 1, 2] else 'summer'
        
        # Add major currents
        for name, current in self.currents.items():
            for (clat, clon, strength, direction) in current['points']:
                # Distance to current core
                dist = self._haversine_km(lat, lon, clat, clon)
                
                if dist < 1000:  # Within 1000km
                    # Gaussian decay
                    factor = math.exp(-dist**2 / (500**2))
                    
                    # Apply seasonal factor
                    factor *= current['seasonal_factor'][season]
                    
                    # Convert direction to components
                    dir_rad = math.radians(direction)
                    u = strength * factor * math.sin(dir_rad)
                    v = strength * factor * math.cos(dir_rad)
                    
                    u_total += u
                    v_total += v
        
        # Add eddies
        for eddy in self.eddies:
            dist = self._haversine_km(lat, lon, eddy['center'][0], eddy['center'][1])
            if dist < eddy['radius']:
                # Tangential velocity
                r_factor = 1.0 - (dist / eddy['radius'])
                tangent_speed = eddy['strength'] * r_factor
                
                # Direction around eddy
                angle = math.atan2(lat - eddy['center'][0], lon - eddy['center'][1])
                dir_eddy = angle + math.radians(eddy['direction'])
                
                u_eddy = tangent_speed * math.sin(dir_eddy)
                v_eddy = tangent_speed * math.cos(dir_eddy)
                
                u_total += u_eddy
                v_total += v_eddy
        
        # Calculate total speed and direction
        speed = math.sqrt(u_total**2 + v_total**2)
        
        if speed > 0:
            direction = math.degrees(math.atan2(u_total, v_total)) % 360
        else:
            direction = 0
        
        # Fuel benefit calculation
        if speed > 0.5:
            if abs(direction - 90) < 45 or abs(direction - 270) < 45:
                benefit = "Following current - fuel savings"
                fuel_factor = 1.0 - (speed * 0.1)  # Up to 10% savings
            elif abs(direction - 270) < 45 or abs(direction - 90) < 45:
                benefit = "Against current - fuel penalty"
                fuel_factor = 1.0 + (speed * 0.15)  # Up to 15% penalty
            else:
                benefit = "Cross current - minor effect"
                fuel_factor = 1.0 + (speed * 0.02)  # 2% penalty
        else:
            benefit = "No significant current"
            fuel_factor = 1.0
        
        return {
            'speed_knots': round(speed, 2),
            'direction_deg': round(direction),
            'u_component': round(u_total, 2),
            'v_component': round(v_total, 2),
            'fuel_factor': round(fuel_factor, 3),
            'benefit_text': benefit,
            'eddies_nearby': len([e for e in self.eddies if 
                                 self._haversine_km(lat, lon, e['center'][0], e['center'][1]) < e['radius']])
        }
    
    def _haversine_km(self, lat1, lon1, lat2, lon2):
        """Haversine distance in km"""
        R = 6371
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Singleton
ocean_currents = OceanCurrentModel()