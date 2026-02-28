#!/usr/bin/env python3
"""
4D Route Optimization Test
Tests how different departure times affect fuel consumption
"""

from utils.route_calculator import ShippingRouteOptimizer
from datetime import datetime, timedelta

def test_4d_routes():
    """Test 4D routing with multiple departure times"""
    
    print("\n" + "="*80)
    print("🌐 4D ROUTE OPTIMIZATION - JOURNAL-GRADE VALIDATION")
    print("="*80)
    
    # Initialize optimizer
    optimizer = ShippingRouteOptimizer()
    
    # Test different departure times
    departures = [
        datetime.now(),
        datetime.now() + timedelta(days=3),
        datetime.now() + timedelta(days=7)
    ]
    
    results = []
    
    for i, dep in enumerate(departures):
        print(f"\n{'='*60}")
        print(f"📅 SCENARIO {i+1}: Departure {dep.strftime('%Y-%m-%d %H:%M')}")
        print('='*60)
        
        try:
            result = optimizer.calculate_route_4d(
                "Singapore", 
                "Tokyo",
                departure_time=dep,
                speed_knots=20
            )
            results.append(result)
        except Exception as e:
            print(f"❌ Error in scenario {i+1}: {e}")
            continue
    
    # Compare results
    if results:
        print("\n" + "="*80)
        print("📊 4D WEATHER IMPACT ANALYSIS")
        print("="*80)
        print(f"\n{'Departure':<20} {'4D Fuel (t)':<15} {'Static (t)':<15} {'Impact':<10} {'Confidence':<10}")
        print("-"*70)
        
        for i, result in enumerate(results):
            impact = result['savings_percent']
            conf = result.get('confidence', 0.5) * 100
            print(f"{departures[i].strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{result['fuel_4d']:<15.1f} "
                  f"{result['fuel_static']:<15.1f} "
                  f"{impact:>+6.1f}%    "
                  f"{conf:>6.0f}%")
        
        # Find best scenario
        best_idx = min(range(len(results)), key=lambda i: results[i]['fuel_4d'])
        print("\n" + "="*80)
        print(f"✅ OPTIMAL DEPARTURE: {departures[best_idx].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Fuel consumption: {results[best_idx]['fuel_4d']:.1f} tonnes")
        print(f"   vs static baseline: {results[best_idx]['fuel_static']:.1f} tonnes")
        print(f"   Weather penalty: {results[best_idx]['savings_percent']:+.1f}%")
        print("="*80)
    
    return results

if __name__ == "__main__":
    results = test_4d_routes()