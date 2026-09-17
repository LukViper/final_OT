#!/usr/bin/env python3
"""
MaritimeRoute-Pro — Weather Service Test Suite
Tests dual-source integration (OpenWeatherMap + Open-Meteo Marine)
"""
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.weather_service import weather_service

def main():
    print("=" * 60)
    print("   MaritimeRoute-Pro — Weather Service Test Suite")
    print("=" * 60)

    # ─── Test 1: API Key Validation ───
    print("\n Test 1: API Key Validation")
    print("-" * 40)
    key = weather_service.openweather_key
    if key:
        print(f"   API key loaded ({key[:4]}****{key[-4:]})")
    else:
        print("    No API key — atmospheric data uses fallback")

    # ─── Test 2: Single Location (dual-source) ───
    print("\n Test 2: Single Location Weather (Jebel Ali)")
    print("-" * 40)
    try:
        weather = weather_service.get_marine_weather(25.0108, 55.0610)
        assert isinstance(weather, dict), "Expected dict"
        print(f"   Weather data received (source: {weather.get('source', '?')})")
        print(f"     --- Atmospheric ---")
        print(f"     Temperature : {weather.get('temperature')}°C")
        print(f"     Wind Speed  : {weather.get('wind_speed')} km/h")
        print(f"     Visibility  : {weather.get('visibility')} km")
        print(f"     Pressure    : {weather.get('pressure')} hPa")
        print(f"     Humidity    : {weather.get('humidity')}%")
        print(f"     --- Marine (real data) ---")
        print(f"     Wave Height : {weather.get('wave_height')} m")
        print(f"     Wave Period : {weather.get('wave_period')} s")
        print(f"     Swell Height: {weather.get('swell_wave_height')} m")
        print(f"     Swell Period: {weather.get('swell_wave_period')} s")
        print(f"     Ocean Curr. : {weather.get('ocean_current_velocity')} km/h")
        print(f"     SST         : {weather.get('sea_surface_temperature')}°C")
        print(f"     Condition   : {weather.get('condition')}")
    except Exception as e:
        print(f"   FAILED: {e}")

    # ─── Test 3: Cache Hit ───
    print("\n Test 3: Cache Hit (same coordinates)")
    print("-" * 40)
    try:
        t1 = time.time()
        w1 = weather_service.get_marine_weather(25.0108, 55.0610)
        d1 = time.time() - t1

        t2 = time.time()
        w2 = weather_service.get_marine_weather(25.0108, 55.0610)
        d2 = time.time() - t2

        print(f"  First call  : {int(d1 * 1000)} ms")
        print(f"  Second call : {int(d2 * 1000)} ms (cached)")
        assert d2 < 0.01, "Cache should be near-instant"
        print("   Cache working — second call was significantly faster")
    except Exception as e:
        print(f"   FAILED: {e}")

    # ─── Test 4: Never Returns None ───
    print("\n Test 4: Never Returns None")
    print("-" * 40)
    coords = [(0, 0), (60, -30), (-45, 170), (90, 0)]
    all_ok = True
    for lat, lon in coords:
        w = weather_service.get_marine_weather(lat, lon)
        if not isinstance(w, dict):
            print(f"   ({lat:4},{lon:5}) returned {type(w)}")
            all_ok = False
        else:
            print(f"   ({lat:4},{lon:5}) → {w['condition']:>8}, {w['temperature']:5.1f}°C, "
                  f"wave={w.get('wave_height', '?')}m, source={w['source']}")
    if all_ok:
        print("   All coordinates returned valid data")

    # ─── Test 5: Route Weather Analysis ───
    print("\n Test 5: Route Weather Analysis")
    print("-" * 40)
    try:
        route = [(25.0, 55.0), (18.0, 72.0), (6.0, 79.5), (1.3, 103.8)]
        result = weather_service.get_route_weather(route)
        assert isinstance(result, dict), "Expected dict"
        assert 'weather_points' in result
        assert 'statistics' in result
        assert 'recommendations' in result
        assert 'storm_glass_data' in result

        print(f"   Route analysis successful!")
        print(f"     Points analysed   : {len(result['weather_points'])}")
        print(f"     Average impact    : {result['average_impact']}/10")
        print(f"     Overall condition : {result['overall_condition']}")
        print(f"     Recommendation    : {result['recommendation']}")
        print(f"     Safety rating     : {result['recommendations']['safety_rating']}")
        print(f"     Weather alert     : {result['recommendations']['weather_alert']}")

        sg = result.get('storm_glass_data', {})
        print(f"     --- Oceanographic (from real data) ---")
        print(f"     Avg Swell         : {sg.get('average_swell')} m")
        print(f"     Water temp (SST)  : {sg.get('water_temp')}°C")
        print(f"     Current speed     : {sg.get('current_speed')} km/h")
    except Exception as e:
        print(f"   FAILED: {e}")

    # ─── Test 6: Empty Route ───
    print("\n Test 6: Empty Route Handling")
    print("-" * 40)
    try:
        empty = weather_service.get_route_weather([])
        assert isinstance(empty, dict), "Expected dict"
        assert empty.get('weather_points') == []
        print("   Empty route handled correctly")
        print(f"     Condition     : {empty.get('overall_condition')}")
        print(f"     Recommendation: {empty.get('recommendation')}")
    except Exception as e:
        print(f"   FAILED: {e}")

    # ─── Test 7: Backward Compatibility ───
    print("\n Test 7: Backward Compatibility (get_route_weather_impact)")
    print("-" * 40)
    try:
        compat = weather_service.get_route_weather_impact([(25, 55), (18, 72)])
        assert 'average_impact' in compat
        assert 'weather_points' in compat
        print("   Backward-compat alias works correctly")
    except Exception as e:
        print(f"   FAILED: {e}")

    # ─── Test 8: Marine data accuracy check ───
    print("\n Test 8: Marine Data Source Verification")
    print("-" * 40)
    try:
        w = weather_service.get_marine_weather(10.0, 80.0)
        src = w.get('source', '')
        has_marine = 'open-meteo-marine' in src
        if has_marine:
            print(f"   Real marine data present (source: {src})")
            assert isinstance(w.get('wave_height'), (int, float))
            assert isinstance(w.get('swell_wave_height'), (int, float))
            assert isinstance(w.get('ocean_current_velocity'), (int, float))
            print(f"     Wave: {w['wave_height']}m, Swell: {w['swell_wave_height']}m, "
                  f"Current: {w['ocean_current_velocity']} km/h")
        else:
            print(f"    Marine API unavailable, using estimates (source: {src})")
    except Exception as e:
        print(f"   FAILED: {e}")

    print("\n" + "=" * 60)
    print("   All weather service tests complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()