# check_imports.py
import sys
import os

print("🔍 Checking Python Imports...")
print(f"Python Version: {sys.version}")
print(f"Current Directory: {os.getcwd()}")

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("\n📦 Trying to import weather_service...")
    from utils.weather_service import weather_service
    print("✅ Successfully imported weather_service")
    
    print("\n📦 Trying to import route_calculator...")
    from utils.route_calculator import ShippingRouteOptimizer
    print("✅ Successfully imported ShippingRouteOptimizer")
    
    print("\n📦 Testing module dependencies...")
    import requests
    import networkx as nx
    print("✅ All dependencies available")
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("\n💡 Try installing missing packages:")
    print("pip install requests networkx python-dotenv pytz")

except Exception as e:
    print(f"❌ Other Error: {e}")