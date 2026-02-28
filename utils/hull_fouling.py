"""
Advanced Hull Fouling Model
Based on ITTC and Biofouling journal (2024)
"""

import math
from typing import Dict, List

class HullFoulingModel:
    """Realistic biofouling growth and fuel penalty calculation"""
    
    def __init__(self):
        # Fouling organism types
        self.organisms = {
            'slime': {
                'growth_rate': 0.03,      # 3% per month
                'max_penalty': 0.05,       # 5% max
                'temp_optimum': (15, 30),  # °C
                'salinity_optimum': (25, 35)
            },
            'barnacles': {
                'growth_rate': 0.08,       # 8% per month
                'max_penalty': 0.15,        # 15% max
                'temp_optimum': (18, 28),
                'salinity_optimum': (30, 35)
            },
            'tubeworms': {
                'growth_rate': 0.05,        # 5% per month
                'max_penalty': 0.12,         # 12% max
                'temp_optimum': (10, 25),
                'salinity_optimum': (28, 35)
            },
            'algae': {
                'growth_rate': 0.10,         # 10% per month
                'max_penalty': 0.08,          # 8% max
                'temp_optimum': (5, 25),
                'salinity_optimum': (20, 35)
            }
        }
        
        # Cleaning costs
        self.cleaning_cost_per_m2 = {
            'in_water_cleaning': 25,
            'diver_cleaning': 45,
            'drydock': 150
        }
        
    def calculate_fouling_penalty(self, days_since_cleaning: int, 
                                  water_temps: List[float],
                                  salinities: List[float]) -> Dict:
        """
        Calculate total fouling penalty based on environmental conditions
        """
        months = days_since_cleaning / 30.0
        avg_temp = sum(water_temps) / len(water_temps) if water_temps else 20
        avg_salinity = sum(salinities) / len(salinities) if salinities else 35
        
        total_penalty = 0.0
        organism_breakdown = {}
        
        for name, org in self.organisms.items():
            # Temperature suitability
            t_min, t_max = org['temp_optimum']
            if t_min <= avg_temp <= t_max:
                temp_factor = 1.0
            elif avg_temp < t_min:
                temp_factor = max(0.1, (avg_temp - 5) / (t_min - 5))
            else:
                temp_factor = max(0.1, (t_max + 10 - avg_temp) / 10)
            
            # Salinity suitability
            s_min, s_max = org['salinity_optimum']
            if s_min <= avg_salinity <= s_max:
                sal_factor = 1.0
            else:
                sal_factor = max(0.2, 1.0 - abs(avg_salinity - s_min) / 20)
            
            # Growth calculation
            growth = org['growth_rate'] * months * temp_factor * sal_factor
            penalty = min(org['max_penalty'], growth)
            
            organism_breakdown[name] = {
                'penalty': round(penalty * 100, 1),
                'temp_factor': round(temp_factor, 2),
                'salinity_factor': round(sal_factor, 2),
                'growth_months': round(growth * 100 / org['max_penalty'], 1)
            }
            
            total_penalty += penalty
        
        # Biofilm synergy (barnacles grow on slime)
        synergy = 1.0 + (organism_breakdown['slime']['penalty'] / 100) * \
                        (organism_breakdown['barnacles']['penalty'] / 100) * 0.5
        
        total_penalty = min(0.40, total_penalty * synergy)  # Max 40% penalty
        
        # Fuel multiplier
        fuel_multiplier = 1.0 + total_penalty
        
        # Determine fouling level
        if total_penalty < 0.05:
            level = "CLEAN"
            cleaning_rec = "No action needed"
        elif total_penalty < 0.10:
            level = "LIGHT FOULING"
            cleaning_rec = "Plan cleaning within 3 months"
        elif total_penalty < 0.20:
            level = "MODERATE FOULING"
            cleaning_rec = "Schedule cleaning at next port"
        elif total_penalty < 0.30:
            level = "HEAVY FOULING"
            cleaning_rec = "Clean at next opportunity"
        else:
            level = "SEVERE FOULING"
            cleaning_rec = "IMMEDIATE CLEANING REQUIRED"
        
        # Economic impact
        annual_fuel_cost = 5000 * 300 * 650  # 5000t/month * 12 * $650
        annual_waste = annual_fuel_cost * total_penalty
        
        return {
            'fuel_multiplier': round(fuel_multiplier, 3),
            'total_penalty_percent': round(total_penalty * 100, 1),
            'fouling_level': level,
            'cleaning_recommendation': cleaning_rec,
            'organism_breakdown': organism_breakdown,
            'environment': {
                'avg_temp': round(avg_temp, 1),
                'avg_salinity': round(avg_salinity, 1),
                'synergy_factor': round(synergy, 2)
            },
            'economic_impact': {
                'annual_waste_usd': int(annual_waste),
                'cleaning_cost_usd': int(self.cleaning_cost_per_m2['in_water_cleaning'] * 5000),
                'roi_percent': round((annual_waste / (5000*45)) * 100, 1)
            }
        }

# Singleton
hull_fouling = HullFoulingModel()