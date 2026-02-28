// Configuration
const CONFIG = {
  AVERAGE_SPEED_KMH: 37.0,
  FUEL_CONSUMPTION_PER_KM: 0.04,
  WEATHER_FACTOR: 1.25,
  EMISSION_FACTOR: 3.15,
};

// Navigation Configuration
const NAV_CONFIG = {
  sections: {
    planner: {
      name: "Route Planner",
      icon: "🗺️",
      visible: true,
    },
    analytics: {
      name: "Analytics",
      icon: "📊",
      visible: true,
    },
    ports: {
      name: "Port Database",
      icon: "⚓",
      visible: true,
    },
    tools: {
      name: "Tools",
      icon: "🔧",
      visible: true,
      submenu: {
        fleet: { name: "Fleet Management", icon: "🚢" },
        reports: { name: "Reports", icon: "📈" },
        weather: { name: "Weather Data", icon: "🌤️" },
        fuel: { name: "Fuel Prices", icon: "⛽" },
      },
    },
  },
  routeTypes: {
    fastest: { name: "Fastest Route", color: "#ff6b35" },
    efficient: { name: "Efficient Route", color: "#2ecc71" },
    direct: { name: "Direct Route", color: "#3498db" },
  },
};

let map;
let routeLayers = {
  fastest: null,
  fuel: null,
  direct: null,
};
let portMarkers = [];
let currentMapData = null;

// Initialize the application
// Initialize the application - UPDATED VERSION
document.addEventListener("DOMContentLoaded", function () {
  console.log("📱 Initializing application with fresh state...");

  // Clear any existing data first
  currentMapData = null;
  routeLayers = {
    fastest: null,
    fuel: null,
    direct: null,
  };
  portMarkers = [];

  // Initialize map
  initializeMap();
  setupEventListeners();

  // Show legend but ensure no routes are shown
  document.getElementById("mapLegend").style.display = "block";

  // Reset statistics to defaults
  resetStatistics();

  // Clear any routes that might still be on the map
  setTimeout(() => {
    refreshMapWithNewData();
    map.setView([20, 0], 2);
  }, 100);
  setTimeout(() => {
    updateDashboardHeightBasedOnComparison();
  }, 100);
});
function resetAllData() {
  console.log("🔄 Resetting all application data...");

  // Clear current data
  currentMapData = null;

  // Clear route layers
  Object.keys(routeLayers).forEach((routeType) => {
    if (routeLayers[routeType]) {
      if (routeLayers[routeType] instanceof L.LayerGroup) {
        routeLayers[routeType].clearLayers();
      }
      if (map && map.hasLayer(routeLayers[routeType])) {
        map.removeLayer(routeLayers[routeType]);
      }
      routeLayers[routeType] = null;
    }
  });

  // Clear markers
  portMarkers.forEach((marker) => {
    if (marker && marker.remove && map) {
      map.removeLayer(marker);
    }
  });
  portMarkers = [];

  // Clear weather markers
  if (window.weatherMarkers) {
    window.weatherMarkers.forEach((marker) => {
      if (marker && marker.remove && map) {
        map.removeLayer(marker);
      }
    });
    window.weatherMarkers = [];
  }

  // Reset form
  document.getElementById("startPort").value = "";
  document.getElementById("destinationPort").value = "";

  const hubPortsSelect = document.getElementById("hubPorts");
  if (hubPortsSelect) {
    Array.from(hubPortsSelect.options).forEach((option) => {
      option.selected = false;
    });
  }

  // Reset radio buttons
  document.querySelectorAll('input[name="goal"]').forEach((radio) => {
    radio.checked = radio.value === "both";
  });

  document.querySelectorAll('input[name="weather"]').forEach((radio) => {
    radio.checked = radio.value === "true";
  });

  // Update selected ports display
  updateSelectedPortsDisplay();

  // Hide results panel
  const resultsPanel = document.getElementById("resultsPanel");
  if (resultsPanel) {
    resultsPanel.style.display = "none";
  }

  // Clear comparison content
  const comparisonDiv = document.querySelector(".route-comparison");
  if (comparisonDiv) {
    comparisonDiv.innerHTML =
      '<p class="text-muted">Select ports and calculate routes to see results...</p>';
  }

  // Reset statistics
  resetStatistics();
  resetDashboardHeight();

  // Reset map view
  if (map) {
    map.setView([20, 0], 2);
  }

  console.log("✅ All data reset successfully");
}
function initializeMap() {
  console.log("🗺️ Initializing fresh map...");

  // First, clear the map container if it already exists
  const mapContainer = document.getElementById("map");
  if (mapContainer && mapContainer._leaflet_id) {
    mapContainer._leaflet_id = null;
  }

  // Initialize map centered on world
  map = L.map("map", {
    zoomControl: true,
    attributionControl: true,
    preferCanvas: true,
  }).setView([20, 0], 2);

  // Clear any existing layers first
  map.eachLayer((layer) => {
    if (layer instanceof L.TileLayer) {
      // Keep tile layers
      return;
    }
    map.removeLayer(layer);
  });

  // Add base layers
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(map);

  // Add OpenSeaMap layer
  L.tileLayer("https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png", {
    attribution: "© OpenSeaMap contributors",
    maxZoom: 18,
    opacity: 0.7,
  }).addTo(map);

  // Add initial instruction popup after a short delay
  setTimeout(() => {
    const instructionPopup = L.popup()
      .setLatLng([20, 0])
      .setContent(
        `
        <div style="text-align: center; padding: 10px;">
            <h3>🚢 Shipping Route Optimizer</h3>
            <p>Select ports and click "Calculate Optimal Routes" to see shipping routes on the map.</p>
            <p><strong>Try selecting hub ports to see different route options!</strong></p>
        </div>
        `
      )
      .openOn(map);
  }, 500);

  console.log("✅ Map initialized with fresh state");
}

function showRouteSuggestions() {
  const startPort = document.getElementById("startPort").value;
  const destinationPort = document.getElementById("destinationPort").value;

  if (startPort && destinationPort && startPort !== destinationPort) {
    console.log(`Route: ${startPort} → ${destinationPort}`);
  }
}
function updateSelectedPortsDisplay() {
  const hubPortsSelect = document.getElementById("hubPorts");
  const selectedPortsContainer = document.getElementById("selectedPorts");
  const selectedPortsList = document.getElementById("selectedPortsList");

  const selectedOptions = Array.from(hubPortsSelect.selectedOptions);
  const selectedPorts = selectedOptions
    .map((opt) => opt.value)
    .filter((port) => port !== "");

  if (selectedPorts.length > 0) {
    selectedPortsContainer.style.display = "block";
    selectedPortsList.innerHTML = "";

    selectedPorts.forEach((port) => {
      const portTag = document.createElement("div");
      portTag.className = "port-tag selected";
      portTag.innerHTML = `
                ${port}
                <button type="button" class="port-tag-remove" onclick="removePortFromSelection('${port}')">×</button>
            `;
      selectedPortsList.appendChild(portTag);
    });

    // ✅ FIXED: Dashboard height UNCHANGED when selecting ports
    // Only visual display changes, no height adjustment
  } else {
    selectedPortsContainer.style.display = "none";
    // Dashboard height unchanged
  }
}
function adjustDashboardHeightForSelectedPorts(selectedPorts) {
  const dashboard = document.querySelector(".metrics-dashboard");
  const resultsPanel = document.getElementById("resultsPanel");

  if (!dashboard) return;

  // Base height without any ports
  let baseHeight = 850; // px

  // Each port tag adds height
  const portTagHeight = 32; // approximate height of each port tag in px
  const portTagMargin = 8; // margin between tags

  // Calculate additional height needed for the selected ports container
  let additionalHeight = 0;

  if (selectedPorts.length > 0) {
    // Height for selected ports section
    const portsContainerHeight = 80; // Base height for the container

    // Height for the port tags themselves (arranged in rows)
    const tagsPerRow = 3; // Approximate tags per row
    const rows = Math.ceil(selectedPorts.length / tagsPerRow);
    const tagsHeight = rows * (portTagHeight + portTagMargin);

    additionalHeight = portsContainerHeight + tagsHeight;
  }

  // Add margin to ensure no overlap
  const safetyMargin = 40; // extra pixels to prevent overlap

  // Set the new height
  const newHeight = baseHeight + additionalHeight + safetyMargin;

  dashboard.style.minHeight = `${newHeight}px`;
  dashboard.style.height = `${newHeight}px`;

  console.log("Dashboard height adjusted:", {
    baseHeight,
    additionalHeight,
    safetyMargin,
    newHeight,
    selectedPortsCount: selectedPorts.length,
  });
}
function resetDashboardHeight() {
  const dashboard = document.querySelector(".metrics-dashboard");
  if (dashboard) {
    dashboard.style.minHeight = "850px";
    dashboard.style.height = "850px";
  }
}
function removePortFromSelection(port) {
  const hubPortsSelect = document.getElementById("hubPorts");
  const option = Array.from(hubPortsSelect.options).find(
    (opt) => opt.value === port
  );

  if (option) {
    option.selected = false;
    updateSelectedPortsDisplay();
  }
}
function clearSelectedPorts() {
  const hubPortsSelect = document.getElementById("hubPorts");
  Array.from(hubPortsSelect.options).forEach((option) => {
    option.selected = false;
  });
  updateSelectedPortsDisplay();

  // Reset dashboard height when ports are cleared
  const dashboard = document.querySelector(".metrics-dashboard");
  if (dashboard) {
    dashboard.style.minHeight = "850px";
    dashboard.style.height = "850px";
  }
}
async function calculateRoutes() {
  const startPort = document.getElementById("startPort").value;
  const destinationPort = document.getElementById("destinationPort").value;
  const hubPortsSelect = document.getElementById("hubPorts");
  const hubPorts = Array.from(hubPortsSelect.selectedOptions)
    .map((opt) => opt.value)
    .filter((port) => port !== "");
  const goal = document.querySelector('input[name="goal"]:checked').value;
  const includeWeather =
    document.querySelector('input[name="weather"]:checked').value === "true";

  // Validate inputs
  if (!startPort || !destinationPort) {
   notify.warning("Please select both start and destination ports", "Port Selection Required");
    return;
  }

  if (startPort === destinationPort) {
   notify.error("Start and destination ports cannot be the same", "Invalid Selection");
    return;
  }

  // 1. Clear the map BEFORE showing loading
  console.log("🗺️ Clearing map for fresh calculation...");
  refreshMapWithNewData();

  // 2. Show loading
  document.getElementById("loadingOverlay").style.display = "flex";
  document.getElementById("calculateBtn").disabled = true;

  // 3. Reset results panel
  const resultsPanel = document.getElementById("resultsPanel");
  if (resultsPanel) {
    resultsPanel.style.display = "none";
  }

  const comparisonDiv = document.querySelector(".route-comparison");
  if (comparisonDiv) {
    comparisonDiv.innerHTML =
      '<p class="text-muted">Calculating routes... Please wait.</p>';
  }

  // 5. Reset statistics
  resetStatistics();

  try {
    const response = await fetch("/calculate-routes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start_port: startPort,
        destination_port: destinationPort,
        hub_ports: hubPorts,
        goal: goal,
        include_weather: includeWeather,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server error ${response.status}: ${errorText}`);
    }

    const data = await response.json();

    // Validate response structure
    if (!data || typeof data !== "object") {
      throw new Error("Invalid response format from server");
    }

    // Check if we have valid route data
    if (!data || (!data.fastest_route && !data.fuel_efficient_route)) {
     notify.error("No routes could be calculated with the current parameters. Please try different ports.", "Calculation Failed");
      return;
    }

    // Display results
    currentMapData = data;
    displayResults(data);
    displayRoutesOnMap(data);
    updateRouteStatistics(data); // This calls updateRouteComparison

    // ✅ CRITICAL: Wait for route comparison to be generated, THEN update height
    setTimeout(() => {
      updateDashboardHeightBasedOnComparison();
    }, 300); // Small delay to ensure DOM is updated

    if (data.algorithm_performance) {
      updateAlgorithmPerformance(data.algorithm_performance);
    }
  } catch (error) {
    console.error("❌ Error calculating routes:", error);
   notify.error("Error calculating routes: " + error.message, "Calculation Error");

  } finally {
    document.getElementById("loadingOverlay").style.display = "none";
    document.getElementById("calculateBtn").disabled = false;
  }
}
// Add this to handle page refresh/load
window.addEventListener("beforeunload", function () {
  // Clear any cached data
  localStorage.removeItem("lastRouteData");
  sessionStorage.clear();
});

// Also call reset when the page loads
window.addEventListener("load", function () {
  setTimeout(resetAllData, 50);
});

function updateElementWithClass(id, value, className) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
    element.className = "comparison-value " + className;
  }
}
// Reset statistics to default state
function resetStatistics() {
  updateElement("avgTransitTime", "--");
  updateElement("fuelEfficiency", "--");
  updateElement("distanceSaved", "--");
  updateElement("costSavings", "--");
  updateElement("statsLastUpdated", "--");

  // Reset comparison values to "--"
  updateElement("timeDifference", "--");
  updateElement("fuelDifference", "--");
  updateElement("recommendedRoute", "--");

  // Hide comparison section
  const comparisonSection = document.getElementById("routeComparison");
  if (comparisonSection) {
    comparisonSection.style.display = "none";
  }
}

function updateRouteStatistics(data) {
  if (!data) return;

  const fastestRoute = data.fastest_route || {};
  const fuelRoute = data.fuel_efficient_route || {};

  console.log("📊 Updating route statistics with data:", data);

  // Calculate average transit time
  const avgTime =
    ((fastestRoute.time_hours || 0) + (fuelRoute.time_hours || 0)) / 2;
  document.getElementById("avgTransitTime").textContent =
    avgTime > 0 ? `${(avgTime / 24).toFixed(1)} days` : "--";

  // Calculate fuel efficiency (lower is better)
  const fuelEfficiency =
    ((fuelRoute.fuel_tonnes || 0) / (fuelRoute.distance_km || 1)) * 100;
  document.getElementById("fuelEfficiency").textContent =
    fuelEfficiency > 0 ? `${fuelEfficiency.toFixed(2)} t/100km` : "--";

  // ✅ FIXED: Calculate distance saved - FASTEST vs FUEL-EFFICIENT
  const distanceSaved =
    (fastestRoute.distance_km || 0) - (fuelRoute.distance_km || 0);
  if (distanceSaved > 0) {
    document.getElementById(
      "distanceSaved"
    ).textContent = `${distanceSaved.toFixed(0)} km saved`;
  } else if (distanceSaved < 0) {
    document.getElementById("distanceSaved").textContent = `${Math.abs(
      distanceSaved
    ).toFixed(0)} km added`;
  } else {
    document.getElementById("distanceSaved").textContent = "No difference";
  }

const fuelPricePerTonne = 650; // USD per tonne (updated from 600)
const costSavings = ((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) * fuelPricePerTonne;

if (costSavings > 0) {
    document.getElementById("costSavings").textContent = `$${costSavings.toFixed(0)} saved`;
} else if (costSavings < 0) {
    document.getElementById("costSavings").textContent = `-$${Math.abs(costSavings).toFixed(0)}`;
} else {
    document.getElementById("costSavings").textContent = "--";
}

  // Update route comparison
  updateRouteComparison(fastestRoute, fuelRoute);

  // Update timestamp
  document.getElementById(
    "statsLastUpdated"
  ).textContent = `Updated: ${new Date().toLocaleTimeString()}`;
}
function safeNumberFormat(value, decimals = 2) {
  if (value === undefined || value === null || isNaN(value)) {
    return "N/A";
  }
  return Number(value).toFixed(decimals);
}
function toggleWeatherIntegration() {
  const weatherRadios = document.querySelectorAll('input[name="weather"]');
  weatherRadios.forEach((radio) => {
    if (radio.value === "true") {
      radio.checked = true;
    }
  });
  // Recalculate routes with weather enabled
  if (currentMapData) {
    calculateRoutes();
  }
}
function displayResults(data) {
  const resultsPanel = document.getElementById("resultsPanel");
  const comparisonDiv = document.querySelector(".route-comparison");

  resultsPanel.style.display = "block";

  // Safe data access with defaults
  const fastestRoute = data.fastest_route || {};
  const fuelRoute = data.fuel_efficient_route || {};

  const fastestPorts = fastestRoute.ports || [];
  const fuelPorts = fuelRoute.ports || [];

  // Get selected intermediate ports
  const hubPortsSelect = document.getElementById("hubPorts");
  const selectedHubs = Array.from(hubPortsSelect.selectedOptions)
    .map((opt) => opt.value)
    .filter((port) => port !== "");

  // Format route path correctly
  function formatRoutePath(ports) {
    if (!ports || ports.length === 0) return "No route available";
    return ports.join(" → ");
  }

  // Calculate sensible values
  const avgTime = ((fastestRoute.time_hours || 0) + (fuelRoute.time_hours || 0)) / 2 / 24;
  const fuelEfficiency = ((fuelRoute.fuel_tonnes || 0) / (fuelRoute.distance_km || 1)) * 100;
  const distanceDiff = (fastestRoute.distance_km || 0) - (fuelRoute.distance_km || 0);
  const costDiff = ((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) * 600;

  // Update statistics
  document.getElementById("avgTransitTime").textContent = avgTime.toFixed(1) + " days";
  document.getElementById("fuelEfficiency").textContent = fuelEfficiency.toFixed(2) + " t/100km";
  
  if (distanceDiff > 0) {
    document.getElementById("distanceSaved").textContent = distanceDiff.toFixed(0) + " km saved";
  } else if (distanceDiff < 0) {
    document.getElementById("distanceSaved").textContent = Math.abs(distanceDiff).toFixed(0) + " km added";
  } else {
    document.getElementById("distanceSaved").textContent = "No difference";
  }
  
  document.getElementById("costSavings").textContent = 
    (costDiff > 0 ? "+$" : "-$") + Math.abs(costDiff).toFixed(0);

  // Update route comparison
  const timeDiff = (fuelRoute.time_hours || 0) - (fastestRoute.time_hours || 0);
  const fuelDiff = (fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0);

  document.getElementById("timeDifference").textContent = 
    (timeDiff > 0 ? "+" : "") + (timeDiff/24).toFixed(1) + " days";
  document.getElementById("fuelDifference").textContent = 
    (fuelDiff > 0 ? "-" : "+") + Math.abs(fuelDiff).toFixed(1) + " tonnes";
  
  if (Math.abs(fuelDiff) > 50) {
    document.getElementById("recommendedRoute").textContent = 
      fuelDiff > 0 ? "Efficient Route 🌿" : "Fastest Route 🚀";
  } else {
    document.getElementById("recommendedRoute").textContent = "Balanced Route ⚖️";
  }

  // Update route cards HTML
  comparisonDiv.innerHTML = `
    <div class="route-cards">
      <div class="route-card fastest">
        <div class="route-card-header">
          <span class="route-icon">🚀</span>
          <span class="route-title">Fastest Route</span>
          ${fastestPorts.length > 2 ? '<span class="route-badge">With Intermediate Ports</span>' : ''}
        </div>
        <div class="route-path">
          <strong>Path:</strong> ${formatRoutePath(fastestPorts)}
        </div>
        <div class="route-stats-grid">
          <div class="stat-card">
            <div class="stat-value">${(fastestRoute.distance_km || 0).toFixed(0)} km</div>
            <div class="stat-label">Distance</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${((fastestRoute.time_hours || 0)/24).toFixed(1)} days</div>
            <div class="stat-label">Time</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${(fastestRoute.fuel_tonnes || 0).toFixed(1)} tonnes</div>
            <div class="stat-label">Fuel</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${((fastestRoute.fuel_tonnes || 0) * 3.15).toFixed(1)} tonnes</div>
            <div class="stat-label">CO₂</div>
          </div>
        </div>
      </div>
      
      <div class="route-card fuel-efficient">
        <div class="route-card-header">
          <span class="route-icon">🌿</span>
          <span class="route-title">Fuel-Efficient Route</span>
          ${fuelPorts.length > 2 ? '<span class="route-badge">With Intermediate Ports</span>' : ''}
        </div>
        <div class="route-path">
          <strong>Path:</strong> ${formatRoutePath(fuelPorts)}
        </div>
        <div class="route-stats-grid">
          <div class="stat-card">
            <div class="stat-value">${(fuelRoute.distance_km || 0).toFixed(0)} km</div>
            <div class="stat-label">Distance</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${((fuelRoute.time_hours || 0)/24).toFixed(1)} days</div>
            <div class="stat-label">Time</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${(fuelRoute.fuel_tonnes || 0).toFixed(1)} tonnes</div>
            <div class="stat-label">Fuel</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${((fuelRoute.fuel_tonnes || 0) * 3.15).toFixed(1)} tonnes</div>
            <div class="stat-label">CO₂</div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Update results meta
  const resultsMeta = document.getElementById("resultsMeta");
  if (fastestPorts.length > 0 && fuelPorts.length > 0) {
    const totalPorts = new Set([...fastestPorts, ...fuelPorts]).size;
    const maxDistance = Math.max(fastestRoute.distance_km || 0, fuelRoute.distance_km || 0);
    resultsMeta.textContent = `${totalPorts} ports • ${(maxDistance/1000).toFixed(1)}k km`;
  }

  document.getElementById("statsLastUpdated").textContent = 
    `Updated: ${new Date().toLocaleTimeString()}`;
}
function updateFooterStats() {
    // Update live calculations
    const routesCalculated = document.getElementById('footerRoutesCalculated');
    if (routesCalculated) {
        routesCalculated.textContent = '1,247';
    }
    
    // Update fuel saved
    const fuelSaved = document.getElementById('footerFuelSaved');
    if (fuelSaved) {
        fuelSaved.textContent = '45.2t';
    }
    
    // Update live calculations counter
    const liveCalcs = document.getElementById('liveCalculations');
    if (liveCalcs) {
        const current = parseInt(liveCalcs.textContent) || 18;
        liveCalcs.textContent = (current + Math.floor(Math.random() * 3)).toString();
    }
    
    // Update active users
    const activeUsers = document.getElementById('activeUsers');
    if (activeUsers) {
        const base = 42;
        activeUsers.textContent = (base + Math.floor(Math.random() * 5)).toString();
    }
    
    // Update last updated time
    const lastUpdated = document.getElementById('footerLastUpdated');
    if (lastUpdated) {
        const now = new Date();
        const minutesAgo = Math.floor(Math.random() * 5);
        lastUpdated.textContent = `${minutesAgo} min ago`;
    }
    
    // Update response time
    const responseTime = document.getElementById('responseTime');
    if (responseTime) {
        responseTime.textContent = `${35 + Math.floor(Math.random() * 25)}ms`;
    }
}

// Update footer stats every 30 seconds
setInterval(updateFooterStats, 30000);

// Initial update
document.addEventListener('DOMContentLoaded', updateFooterStats);
// Add this function to update footer statistics
function updateFooterStatistics() {
    // Update route calculations count
    const routesCount = document.getElementById('footerRoutesCalculated');
    if (routesCount) {
        const current = parseInt(routesCount.textContent) || 1247;
        // Simulate occasional updates
        if (Math.random() > 0.7) {
            routesCount.textContent = (current + 1).toString();
        }
    }
    
    // Update fuel saved (simulated)
    const fuelSaved = document.getElementById('footerFuelSaved');
    if (fuelSaved && Math.random() > 0.8) {
        const current = parseFloat(fuelSaved.textContent) || 45.2;
        fuelSaved.textContent = (current + 0.1).toFixed(1) + 't';
    }
    
    // Update live statistics
    const liveCalculations = document.getElementById('liveCalculations');
    if (liveCalculations) {
        const base = 18;
        liveCalculations.textContent = (base + Math.floor(Math.random() * 5)).toString();
    }
    
    // Update response time
    const responseTime = document.getElementById('responseTime');
    if (responseTime) {
        responseTime.textContent = `${40 + Math.floor(Math.random() * 20)}ms`;
    }
}

// Update footer stats periodically
setInterval(updateFooterStatistics, 10000);

// Initial update
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(updateFooterStatistics, 1000);
});
// ========== ENHANCED WEATHER HELPER FUNCTIONS ==========

function getWeatherClass(impactScore) {
  if (impactScore < 2) return "weather-excellent";
  if (impactScore < 4) return "weather-good";
  if (impactScore < 6) return "weather-moderate";
  if (impactScore < 8) return "weather-poor";
  return "weather-dangerous";
}

function getImpactColorClass(impactScore) {
  if (impactScore < 2) return "color-excellent";
  if (impactScore < 4) return "color-good";
  if (impactScore < 6) return "color-moderate";
  if (impactScore < 8) return "color-poor";
  return "color-dangerous";
}

function getWeatherIcon(impactScore) {
  if (impactScore < 2) return "☀️";
  if (impactScore < 4) return "⛅";
  if (impactScore < 6) return "🌤️";
  if (impactScore < 8) return "🌧️";
  return "⛈️";
}

function getWindCondition(impactScore) {
  if (impactScore < 2) return "Calm (0-20 km/h)";
  if (impactScore < 4) return "Light Breeze (20-40 km/h)";
  if (impactScore < 6) return "Moderate Wind (40-60 km/h)";
  if (impactScore < 8) return "Strong Wind (60-80 km/h)";
  return "Gale Force (>80 km/h)";
}

function getWaveCondition(impactScore) {
  if (impactScore < 2) return "Slight (0-1m)";
  if (impactScore < 4) return "Moderate (1-2m)";
  if (impactScore < 6) return "Rough (2-4m)";
  if (impactScore < 8) return "Very Rough (4-6m)";
  return "High (>6m)";
}

function calculateTimeImpact(impactScore) {
    // Return percentage increase in travel time based on weather impact
    if (impactScore < 2) return "0-5%";
    if (impactScore < 4) return "5-15%";
    if (impactScore < 6) return "15-30%";
    if (impactScore < 8) return "30-50%";
    return "50%+";
}

function calculateFuelImpact(impactScore) {
  // Return percentage increase in fuel consumption
  if (impactScore < 2) return "0-3%";
  if (impactScore < 4) return "3-8%";
  if (impactScore < 6) return "8-15%";
  if (impactScore < 8) return "15-25%";
  return "25%+";
}

function getBeaufortScale(windSpeedKmh) {
  if (windSpeedKmh < 2) return { scale: 0, description: "Calm" };
  if (windSpeedKmh < 6) return { scale: 1, description: "Light Air" };
  if (windSpeedKmh < 12) return { scale: 2, description: "Light Breeze" };
  if (windSpeedKmh < 20) return { scale: 3, description: "Gentle Breeze" };
  if (windSpeedKmh < 29) return { scale: 4, description: "Moderate Breeze" };
  if (windSpeedKmh < 39) return { scale: 5, description: "Fresh Breeze" };
  if (windSpeedKmh < 50) return { scale: 6, description: "Strong Breeze" };
  if (windSpeedKmh < 62) return { scale: 7, description: "Near Gale" };
  if (windSpeedKmh < 75) return { scale: 8, description: "Gale" };
  if (windSpeedKmh < 89) return { scale: 9, description: "Strong Gale" };
  if (windSpeedKmh < 103) return { scale: 10, description: "Storm" };
  return { scale: 11, description: "Violent Storm" };
}

function generateWeatherInsights(fastestWeather, fuelWeather) {
  const insights = [];
  const fastestImpact = fastestWeather.average_impact;
  const fuelImpact = fuelWeather.average_impact;

  // Calculate wind and wave data averages
  const fastestWindAvg = calculateAverageWind(
    fastestWeather.weather_points || []
  );
  const fuelWindAvg = calculateAverageWind(fuelWeather.weather_points || []);
  const fastestWaveAvg = calculateAverageWave(
    fastestWeather.weather_points || []
  );
  const fuelWaveAvg = calculateAverageWave(fuelWeather.weather_points || []);

  // 1. Overall condition comparison
  if (Math.abs(fastestImpact - fuelImpact) > 2) {
    const betterRoute =
      fastestImpact < fuelImpact ? "Fastest" : "Fuel-Efficient";
    const diff = Math.abs(fastestImpact - fuelImpact).toFixed(1);
    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">📈</span>
                <span class="insight-text">
                    <strong>${betterRoute} route has significantly better weather conditions</strong> 
                    (${diff} point impact difference). The difference is substantial enough to affect fuel efficiency by ${(
      diff * 2
    ).toFixed(1)}%.
                </span>
            </div>
        `);
  }

  // 2. Wind comparison analysis
  if (Math.abs(fastestWindAvg - fuelWindAvg) > 10) {
    const windDiff = Math.abs(fastestWindAvg - fuelWindAvg).toFixed(0);
    const betterWindRoute =
      fastestWindAvg < fuelWindAvg ? "Fastest" : "Fuel-Efficient";
    const fastestBeaufort = getBeaufortScale(fastestWindAvg);
    const fuelBeaufort = getBeaufortScale(fuelWindAvg);

    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">💨</span>
                <span class="insight-text">
                    <strong>Wind conditions differ significantly:</strong> 
                    ${betterWindRoute} route has ${windDiff} km/h lower average wind speed.
                    (Beaufort ${fastestBeaufort.scale} vs ${fuelBeaufort.scale})
                </span>
            </div>
        `);
  }

  // 3. Wave height analysis
  if (Math.abs(fastestWaveAvg - fuelWaveAvg) > 0.5) {
    const waveDiff = Math.abs(fastestWaveAvg - fuelWaveAvg).toFixed(1);
    const betterWaveRoute =
      fastestWaveAvg < fuelWaveAvg ? "Fastest" : "Fuel-Efficient";

    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">🌊</span>
                <span class="insight-text">
                    <strong>Wave heights vary between routes:</strong> 
                    ${betterWaveRoute} route has ${waveDiff}m lower average wave height, 
                    which can improve passenger comfort and reduce hull stress.
                </span>
            </div>
        `);
  }

  // 4. Risk assessment
  if (fastestImpact > 6 || fuelImpact > 6) {
    const riskyRoutes = [];
    if (fastestImpact > 6) riskyRoutes.push("Fastest");
    if (fuelImpact > 6) riskyRoutes.push("Efficient");

    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">⚠️</span>
                <span class="insight-text">
                    <strong>High-risk weather detected on ${riskyRoutes.join(
                      " and "
                    )} route(s)</strong> 
                    - Consider delaying departure or adjusting route. Expected travel time increase: ${calculateTimeImpact(
                      Math.max(fastestImpact, fuelImpact)
                    )}.
                </span>
            </div>
        `);
  }

  // 5. Fuel efficiency impact
  const fuelDiff = fastestImpact - fuelImpact;
  if (Math.abs(fuelDiff) > 1) {
    const betterFuelRoute = fuelDiff < 0 ? "Fastest" : "Fuel-Efficient";
    const fuelImpactPercent = (Math.abs(fuelDiff) * 1.5).toFixed(1);

    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">⛽</span>
                <span class="insight-text">
                    <strong>Weather impact on fuel consumption:</strong> 
                    ${betterFuelRoute} route is expected to use ${fuelImpactPercent}% less fuel due to better weather conditions.
                </span>
            </div>
        `);
  }

  // 6. Optimal sailing conditions
  if (fastestImpact < 3 && fuelImpact < 3) {
    insights.push(`
            <div class="insight-item">
                <span class="insight-icon"></span>
                <span class="insight-text">
                    <strong>Excellent sailing conditions on both routes</strong> 
                    - Minimal weather impact expected. This is optimal for passenger comfort and schedule reliability.
                </span>
            </div>
        `);
  }

  // 7. Route-specific advantages
  if (fastestWeather.weather_points && fuelWeather.weather_points) {
    const fastestVariability = calculateWeatherVariability(
      fastestWeather.weather_points
    );
    const fuelVariability = calculateWeatherVariability(
      fuelWeather.weather_points
    );

    if (Math.abs(fastestVariability - fuelVariability) > 10) {
      const moreStableRoute =
        fastestVariability < fuelVariability ? "Fastest" : "Fuel-Efficient";
      insights.push(`
                <div class="insight-item">
                    <span class="insight-icon">📊</span>
                    <span class="insight-text">
                        <strong>Weather stability varies:</strong> 
                        ${moreStableRoute} route has more consistent weather conditions, 
                        making it easier to maintain optimal speed and fuel efficiency.
                    </span>
                </div>
            `);
    }
  }

  return insights.length > 0
    ? insights.join("")
    : `
        <div class="insight-item">
            <span class="insight-icon">ℹ️</span>
            <span class="insight-text">Both routes have very similar weather conditions. Choose based on distance, fuel efficiency, or other operational factors.</span>
        </div>
    `;
}

function generateRecommendation(fastestImpact, fuelImpact) {
  const diff = fastestImpact - fuelImpact;

  if (Math.abs(diff) < 0.5) {
    return "Both routes have nearly identical weather conditions. Recommendation: Choose based on operational priorities (time vs fuel).";
  }

  if (diff < 0) {
    // Fastest route has better weather
    if (diff < -2) {
      return (
        "STRONG RECOMMENDATION: Fastest Route. Significantly better weather conditions (+" +
        Math.abs(diff).toFixed(1) +
        " points) make this the clear choice despite potentially higher fuel consumption."
      );
    } else {
      return "RECOMMENDATION: Fastest Route. Better weather conditions provide smoother sailing and more reliable schedule adherence.";
    }
  } else {
    // Fuel route has better weather
    if (diff > 2) {
      return (
        "STRONG RECOMMENDATION: Fuel-Efficient Route. Avoid poor weather on faster route while saving " +
        calculateFuelSavings(diff) +
        " tonnes of fuel."
      );
    } else {
      return "RECOMMENDATION: Fuel-Efficient Route. Slightly better weather conditions combined with fuel savings make this the optimal choice.";
    }
  }
}

function getRecommendationClass(fastestImpact, fuelImpact) {
  const diff = fastestImpact - fuelImpact;
  if (Math.abs(diff) < 1) return "recommendation-neutral";
  return diff < 0 ? "recommendation-positive" : "recommendation-caution";
}

function getRecommendationIcon(fastestImpact, fuelImpact) {
  const diff = fastestImpact - fuelImpact;
  if (Math.abs(diff) < 1) return "⚖️";
  return diff < 0 ? "✅" : "⚠️";
}

function renderWeatherPoints(weatherPoints, routeType) {
  if (!weatherPoints || weatherPoints.length === 0) return "";

  const routeColor = routeType === "fastest" ? "#ff6b35" : "#2ecc71";

  return `
        <div class="weather-route-points ${routeType}-points">
            <h6>${
              routeType === "fastest"
                ? "🚀 Fastest Route"
                : "🌿 Efficient Route"
            }</h6>
            <div class="points-list">
                ${weatherPoints
                  .slice(0, 5)
                  .map((point, index) => {
                    const weather = point.weather || {};
                    const beaufort = getBeaufortScale(weather.wind_speed || 0);
                    const timeImpact = calculateTimeImpact(point.impact_score);
                    const fuelImpact = calculateFuelImpact(point.impact_score);

                    return `
                    <div class="weather-point">
                        <div class="point-header">
                            <span class="point-number">Point #${
                              index + 1
                            }</span>
                            <span class="point-condition ${getWeatherClass(
                              point.impact_score
                            )}">
                                ${getWeatherIcon(point.impact_score)} ${
                      weather.condition || "N/A"
                    }
                            </span>
                        </div>
                        <div class="point-details">
                            <div class="point-detail">
                                <span class="detail-label">Wind:</span>
                                <span class="detail-value">${(
                                  weather.wind_speed || 0
                                ).toFixed(0)} km/h (Bft ${
                      beaufort.scale
                    })</span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Waves:</span>
                                <span class="detail-value">${(
                                  weather.wave_height || 0
                                ).toFixed(1)} m</span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Temp:</span>
                                <span class="detail-value">${(
                                  weather.temperature || 0
                                ).toFixed(1)}°C</span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Impact:</span>
                                <span class="detail-value ${getImpactColorClass(
                                  point.impact_score
                                )}">
                                    ${point.impact_score.toFixed(1)}/10
                                </span>
                            </div>
                            <div class="point-impact">
                                <span class="impact-label">Time Impact:</span>
                                <span>${timeImpact}</span>
                                <span class="impact-label">Fuel Impact:</span>
                                <span>${fuelImpact}</span>
                            </div>
                        </div>
                    </div>
                `;
                  })
                  .join("")}
            </div>
            ${
              weatherPoints.length > 5
                ? `
            <div class="more-points">
                <small>+ ${
                  weatherPoints.length - 5
                } more weather points analyzed along this route</small>
            </div>
            `
                : ""
            }
        </div>
    `;
}

// ========== ENHANCED WEATHER METRICS FOR STORM GLASS API ==========

function getEnhancedWeatherMetrics(weather, routeType) {
  if (!weather) return "";

  const avgWind = calculateAverageWind(weather.weather_points || []);
  const avgWave = calculateAverageWave(weather.weather_points || []);
  const beaufort = getBeaufortScale(avgWind);
  const timeImpact = calculateTimeImpact(weather.average_impact);
  const fuelImpact = calculateFuelImpact(weather.average_impact);

  // Storm Glass specific metrics (if available)
  const hasStormGlassData = weather.storm_glass_data || false;

  return `
        <div class="weather-metrics">
            <div class="weather-metric">
                <span class="metric-label">Impact Score</span>
                <span class="metric-value ${getImpactColorClass(
                  weather.average_impact
                )}">
                    ${weather.average_impact.toFixed(1)}/10
                </span>
                <div class="impact-bar">
                    <div class="impact-fill" style="width: ${
                      weather.average_impact * 10
                    }%"></div>
                </div>
                <div class="metric-subtext">Lower is better</div>
            </div>
            
            <div class="weather-metric">
                <span class="metric-label">Wind Speed</span>
                <span class="metric-value">${avgWind.toFixed(0)} km/h</span>
                <div class="metric-subtext">
                    <span class="beaufort-indicator">Bft ${
                      beaufort.scale
                    }</span>
                    ${beaufort.description}
                </div>
            </div>
            
            <div class="weather-metric">
                <span class="metric-label">Wave Height</span>
                <span class="metric-value">${avgWave.toFixed(1)} m</span>
                <div class="metric-subtext">${getWaveCondition(
                  weather.average_impact
                )}</div>
            </div>
            
            <div class="weather-metric">
                <span class="metric-label">Visibility</span>
                <span class="metric-value">${calculateAverageVisibility(
                  weather.weather_points || []
                ).toFixed(1)} km</span>
                <div class="metric-subtext">
                    ${getVisibilityCondition(
                      calculateAverageVisibility(weather.weather_points || [])
                    )}
                </div>
            </div>
            
            <div class="weather-metric">
                <span class="metric-label">Time Impact</span>
                <span class="metric-value ${
                  weather.average_impact > 4
                    ? "color-moderate"
                    : "color-excellent"
                }">
                    ${timeImpact}
                </span>
                <div class="metric-subtext">Estimated delay</div>
            </div>
            
            <div class="weather-metric">
                <span class="metric-label">Fuel Impact</span>
                <span class="metric-value ${
                  weather.average_impact > 4
                    ? "color-moderate"
                    : "color-excellent"
                }">
                    ${fuelImpact}
                </span>
                <div class="metric-subtext">Consumption increase</div>
            </div>
            
            ${
              hasStormGlassData
                ? `
            <div class="weather-metric">
                <span class="metric-label">Swell Height</span>
                <span class="metric-value">${
                  weather.storm_glass_data?.average_swell || "N/A"
                } m</span>
                <div class="metric-subtext">From Storm Glass API</div>
            </div>
            
            <div class="weather-metric">
                <span class="metric-label">Water Temp</span>
                <span class="metric-value">${
                  weather.storm_glass_data?.water_temp || "N/A"
                }°C</span>
                <div class="metric-subtext">Sea surface</div>
            </div>
            `
                : ""
            }
        </div>
    `;
}

function calculateAverageVisibility(weatherPoints) {
  if (!weatherPoints || weatherPoints.length === 0) return 10;
  const sum = weatherPoints.reduce(
    (acc, point) => acc + (point.weather?.visibility || 10),
    0
  );
  return sum / weatherPoints.length;
}

function getVisibilityCondition(visibilityKm) {
  if (visibilityKm > 10) return "Excellent";
  if (visibilityKm > 5) return "Good";
  if (visibilityKm > 2) return "Moderate";
  if (visibilityKm > 1) return "Poor";
  return "Very Poor";
}

// Enhanced weather point display with Storm Glass data
function renderWeatherPoints(weatherPoints, routeType) {
  if (!weatherPoints || weatherPoints.length === 0) return "";

  const routeColor = routeType === "fastest" ? "#ff6b35" : "#2ecc71";
  const routeName =
    routeType === "fastest" ? "🚀 Fastest Route" : "🌿 Efficient Route";

  return `
        <div class="weather-route-points ${routeType}-points">
            <h6>${routeName}</h6>
            <div class="points-list">
                ${weatherPoints
                  .slice(0, 5)
                  .map((point, index) => {
                    const weather = point.weather || {};
                    const beaufort = getBeaufortScale(weather.wind_speed || 0);
                    const timeImpact = calculateTimeImpact(point.impact_score);
                    const fuelImpact = calculateFuelImpact(point.impact_score);

                    return `
                    <div class="weather-point">
                        <div class="point-header">
                            <span class="point-number">Point #${
                              index + 1
                            }</span>
                            <span class="point-condition ${getWeatherClass(
                              point.impact_score
                            )}">
                                ${getWeatherIcon(point.impact_score)} ${
                      weather.condition || "N/A"
                    }
                            </span>
                        </div>
                        <div class="point-details">
                            <div class="point-detail">
                                <span class="detail-label">Wind</span>
                                <span class="detail-value">
                                    ${(weather.wind_speed || 0).toFixed(0)} km/h
                                    <span class="beaufort-tag">Bft ${
                                      beaufort.scale
                                    }</span>
                                </span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Waves</span>
                                <span class="detail-value">${(
                                  weather.wave_height || 0
                                ).toFixed(1)} m</span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Visibility</span>
                                <span class="detail-value">${(
                                  weather.visibility || 10
                                ).toFixed(1)} km</span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Temp</span>
                                <span class="detail-value">${(
                                  weather.temperature || 0
                                ).toFixed(1)}°C</span>
                            </div>
                            ${
                              weather.precipitation > 0
                                ? `
                            <div class="point-detail">
                                <span class="detail-label">Precip</span>
                                <span class="detail-value">${weather.precipitation.toFixed(
                                  1
                                )} mm</span>
                            </div>
                            `
                                : ""
                            }
                        </div>
                        <div class="point-impact">
                            <div class="impact-group">
                                <span class="impact-label">Time Impact:</span>
                                <span class="impact-value">${timeImpact}</span>
                            </div>
                            <div class="impact-group">
                                <span class="impact-label">Fuel Impact:</span>
                                <span class="impact-value">${fuelImpact}</span>
                            </div>
                        </div>
                    </div>
                `;
                  })
                  .join("")}
            </div>
            ${
              weatherPoints.length > 5
                ? `
            <div class="more-points">
                <span class="more-icon">📈</span>
                <span class="more-text">
                    +${
                      weatherPoints.length - 5
                    } more weather points analyzed along this route
                </span>
            </div>
            `
                : ""
            }
        </div>
    `;
}

function calculateFuelSavings(impactDifference) {
  // Estimate fuel savings based on weather impact difference
  return (impactDifference * 1.2).toFixed(1);
}

function calculateAverageWind(weatherPoints) {
  if (!weatherPoints || weatherPoints.length === 0) return 0;
  const sum = weatherPoints.reduce(
    (acc, point) => acc + (point.weather?.wind_speed || 0),
    0
  );
  return sum / weatherPoints.length;
}

function calculateAverageWave(weatherPoints) {
  if (!weatherPoints || weatherPoints.length === 0) return 0;
  const sum = weatherPoints.reduce(
    (acc, point) => acc + (point.weather?.wave_height || 0),
    0
  );
  return sum / weatherPoints.length;
}

function calculateWeatherVariability(weatherPoints) {
  if (!weatherPoints || weatherPoints.length < 2) return 0;
  const impacts = weatherPoints.map((p) => p.impact_score || 0);
  const mean = impacts.reduce((a, b) => a + b) / impacts.length;
  const variance =
    impacts.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / impacts.length;
  return Math.sqrt(variance) * 10; // Scale for readability
}

function calculateConfidenceLevel(fastestWeather, fuelWeather) {
  const fastestPoints = fastestWeather.weather_points?.length || 0;
  const fuelPoints = fuelWeather.weather_points?.length || 0;
  const totalPoints = fastestPoints + fuelPoints;

  if (totalPoints >= 15) return "High (≥15 data points)";
  if (totalPoints >= 8) return "Medium (8-14 data points)";
  return "Low (<8 data points)";
}

function getRecommendationDetails(fastestWeather, fuelWeather) {
  const fastestImpact = fastestWeather.average_impact;
  const fuelImpact = fuelWeather.average_impact;
  const diff = fastestImpact - fuelImpact;

  const details = [];

  if (Math.abs(diff) < 0.5) {
    details.push("• Weather conditions nearly identical");
    details.push("• Decision should focus on operational priorities");
    details.push("• Consider vessel-specific factors");
  } else if (diff < 0) {
    details.push("• Fastest route has better weather conditions");
    details.push(
      "• Expected time savings: " + calculateTimeImpact(Math.abs(diff))
    );
    details.push("• Passenger comfort likely better on this route");
  } else {
    details.push("• Efficient route avoids weather challenges");
    details.push("• Fuel savings: ~" + calculateFuelSavings(diff) + " tonnes");
    details.push("• Lower operational risk on this route");
  }

  return details
    .map((detail) => `<div class="detail-item">${detail}</div>`)
    .join("");
}

function addWeatherMarkers(data) {
  // Clear existing weather markers
  if (window.weatherMarkers) {
    window.weatherMarkers.forEach((marker) => map.removeLayer(marker));
  }
  window.weatherMarkers = [];

  // Add weather markers for fastest route
  if (data.fastest_route?.weather_impact?.weather_points) {
    data.fastest_route.weather_impact.weather_points.forEach((point, index) => {
      const marker = L.marker(point.coordinates)
        .bindPopup(
          `
                    <div class="weather-marker-popup">
                        <h5>🚀 Fastest Route - Point ${index + 1}</h5>
                        <p><strong>Condition:</strong> ${
                          point.weather.condition
                        }</p>
                        <p><strong>Wind Speed:</strong> ${point.weather.wind_speed.toFixed(
                          1
                        )} km/h</p>
                        <p><strong>Wave Height:</strong> ${point.weather.wave_height.toFixed(
                          1
                        )} m</p>
                        <p><strong>Temperature:</strong> ${point.weather.temperature.toFixed(
                          1
                        )}°C</p>
                        <p><strong>Weather Impact:</strong> ${point.impact_score.toFixed(
                          1
                        )}/10</p>
                    </div>
                `
        )
        .addTo(map);

      // Add weather icon based on condition
      const icon = getWeatherIcon(point.impact_score);
      const customIcon = L.divIcon({
        html: `<div style="background-color: rgba(255, 107, 53, 0.8); border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; border: 2px solid white;">${icon}</div>`,
        className: "weather-marker",
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      });

      marker.setIcon(customIcon);
      window.weatherMarkers.push(marker);
    });
  }

  // Add weather markers for fuel-efficient route
  if (data.fuel_efficient_route?.weather_impact?.weather_points) {
    data.fuel_efficient_route.weather_impact.weather_points.forEach(
      (point, index) => {
        const marker = L.marker(point.coordinates)
          .bindPopup(
            `
                    <div class="weather-marker-popup">
                        <h5>🌿 Efficient Route - Point ${index + 1}</h5>
                        <p><strong>Condition:</strong> ${
                          point.weather.condition
                        }</p>
                        <p><strong>Wind Speed:</strong> ${point.weather.wind_speed.toFixed(
                          1
                        )} km/h</p>
                        <p><strong>Wave Height:</strong> ${point.weather.wave_height.toFixed(
                          1
                        )} m</p>
                        <p><strong>Temperature:</strong> ${point.weather.temperature.toFixed(
                          1
                        )}°C</p>
                        <p><strong>Weather Impact:</strong> ${point.impact_score.toFixed(
                          1
                        )}/10</p>
                    </div>
                `
          )
          .addTo(map);

        const icon = getWeatherIcon(point.impact_score);
        const customIcon = L.divIcon({
          html: `<div style="background-color: rgba(46, 204, 113, 0.8); border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; border: 2px solid white;">${icon}</div>`,
          className: "weather-marker",
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        });

        marker.setIcon(customIcon);
        window.weatherMarkers.push(marker);
      }
    );
  }
}

// ========== WEATHER HELPER FUNCTIONS ==========

function getWeatherClass(impactScore) {
  if (impactScore < 2) return "weather-excellent";
  if (impactScore < 4) return "weather-good";
  if (impactScore < 6) return "weather-moderate";
  if (impactScore < 8) return "weather-poor";
  return "weather-dangerous";
}

function getImpactColorClass(impactScore) {
  if (impactScore < 2) return "color-excellent";
  if (impactScore < 4) return "color-good";
  if (impactScore < 6) return "color-moderate";
  if (impactScore < 8) return "color-poor";
  return "color-dangerous";
}

function getWeatherIcon(impactScore) {
  if (impactScore < 2) return "☀️";
  if (impactScore < 4) return "⛅";
  if (impactScore < 6) return "🌤️";
  if (impactScore < 8) return "🌧️";
  return "⛈️";
}

function getWindCondition(impactScore) {
  if (impactScore < 2) return "Calm (0-20 km/h)";
  if (impactScore < 4) return "Light Breeze (20-40 km/h)";
  if (impactScore < 6) return "Moderate Wind (40-60 km/h)";
  if (impactScore < 8) return "Strong Wind (60-80 km/h)";
  return "Gale Force (>80 km/h)";
}

function calculateTimeImpact(impactScore) {
  // Return percentage increase in travel time
  if (impactScore < 2) return "0-10";
  if (impactScore < 4) return "10-30";
  if (impactScore < 6) return "30-60";
  if (impactScore < 8) return "60-100";
  return "100+";
}

function generateWeatherInsights(fastestWeather, fuelWeather) {
  const insights = [];
  const fastestImpact = fastestWeather.average_impact;
  const fuelImpact = fuelWeather.average_impact;

  if (Math.abs(fastestImpact - fuelImpact) > 2) {
    const betterRoute =
      fastestImpact < fuelImpact ? "Fastest" : "Fuel-Efficient";
    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">📈</span>
                <span class="insight-text">
                    <strong>${betterRoute} route has significantly better weather conditions</strong> 
                    (${Math.abs(fastestImpact - fuelImpact).toFixed(
                      1
                    )} point difference)
                </span>
            </div>
        `);
  }

  if (fastestImpact > 6 || fuelImpact > 6) {
    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">⚠️</span>
                <span class="insight-text">
                    <strong>Potential delays expected</strong> due to poor weather conditions 
                    (${fastestImpact > 6 ? "Fastest route" : ""}${
      fastestImpact > 6 && fuelImpact > 6 ? " and " : ""
    }${fuelImpact > 6 ? "Efficient route" : ""})
                </span>
            </div>
        `);
  }

  if (fastestImpact < 3 && fuelImpact < 3) {
    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">👍</span>
                <span class="insight-text">
                    <strong>Excellent sailing conditions</strong> on both routes. Minimal weather impact expected.
                </span>
            </div>
        `);
  }

  // Add fuel consumption insight
  const fuelDiff = fastestImpact - fuelImpact;
  if (Math.abs(fuelDiff) > 1) {
    insights.push(`
            <div class="insight-item">
                <span class="insight-icon">⛽</span>
                <span class="insight-text">
                    <strong>Weather may affect fuel efficiency</strong> by 
                    ${Math.abs(fuelDiff).toFixed(1)}% between routes.
                </span>
            </div>
        `);
  }

  return insights.length > 0
    ? insights.join("")
    : `
        <div class="insight-item">
            <span class="insight-icon">ℹ️</span>
            <span class="insight-text">Both routes have similar weather conditions.</span>
        </div>
    `;
}

function generateRecommendation(fastestImpact, fuelImpact) {
  const diff = fastestImpact - fuelImpact;

  if (Math.abs(diff) < 1) {
    return "Both routes have similar weather conditions. Choose based on other factors.";
  }

  if (diff < 0) {
    // Fastest route has better weather
    if (diff < -2) {
      return "Strongly recommend Fastest Route due to significantly better weather conditions.";
    } else {
      return "Weather slightly favors Fastest Route. Consider taking it for smoother sailing.";
    }
  } else {
    // Fuel route has better weather
    if (diff > 2) {
      return "Strongly recommend Fuel-Efficient Route to avoid poor weather on faster route.";
    } else {
      return "Weather conditions are better on Fuel-Efficient Route. Consider the trade-off.";
    }
  }
}

function getRecommendationClass(fastestImpact, fuelImpact) {
  const diff = fastestImpact - fuelImpact;
  if (Math.abs(diff) < 1) return "recommendation-neutral";
  return diff < 0 ? "recommendation-positive" : "recommendation-caution";
}

function getRecommendationIcon(fastestImpact, fuelImpact) {
  const diff = fastestImpact - fuelImpact;
  if (Math.abs(diff) < 1) return "⚖️";
  return diff < 0 ? "✅" : "⚠️";
}

function renderWeatherPoints(weatherPoints, routeType) {
  if (!weatherPoints || weatherPoints.length === 0) return "";

  return `
        <div class="weather-route-points ${routeType}-points">
            <h6>${
              routeType === "fastest"
                ? "🚀 Fastest Route"
                : "🌿 Efficient Route"
            }</h6>
            <div class="points-list">
                ${weatherPoints
                  .slice(0, 5)
                  .map(
                    (point, index) => `
                    <div class="weather-point">
                        <div class="point-header">
                            <span class="point-number">#${index + 1}</span>
                            <span class="point-condition ${getWeatherClass(
                              point.impact_score
                            )}">
                                ${getWeatherIcon(point.impact_score)} ${
                      point.weather.condition
                    }
                            </span>
                        </div>
                        <div class="point-details">
                            <div class="point-detail">
                                <span class="detail-label">Wind:</span>
                                <span class="detail-value">${point.weather.wind_speed.toFixed(
                                  0
                                )} km/h</span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Waves:</span>
                                <span class="detail-value">${point.weather.wave_height.toFixed(
                                  1
                                )} m</span>
                            </div>
                            <div class="point-detail">
                                <span class="detail-label">Impact:</span>
                                <span class="detail-value ${getImpactColorClass(
                                  point.impact_score
                                )}">
                                    ${point.impact_score.toFixed(1)}/10
                                </span>
                            </div>
                        </div>
                    </div>
                `
                  )
                  .join("")}
            </div>
        </div>
    `;
}

function addWeatherMarkers(data) {
  // Clear existing weather markers
  if (window.weatherMarkers) {
    window.weatherMarkers.forEach((marker) => map.removeLayer(marker));
  }
  window.weatherMarkers = [];

  // Add weather markers for fastest route
  if (data.fastest_route?.weather_impact?.weather_points) {
    data.fastest_route.weather_impact.weather_points.forEach((point, index) => {
      const marker = L.marker(point.coordinates)
        .bindPopup(
          `
                    <div class="weather-marker-popup">
                        <h5>🚀 Fastest Route - Point ${index + 1}</h5>
                        <p><strong>Condition:</strong> ${
                          point.weather.condition
                        }</p>
                        <p><strong>Wind Speed:</strong> ${point.weather.wind_speed.toFixed(
                          1
                        )} km/h</p>
                        <p><strong>Wave Height:</strong> ${point.weather.wave_height.toFixed(
                          1
                        )} m</p>
                        <p><strong>Temperature:</strong> ${point.weather.temperature.toFixed(
                          1
                        )}°C</p>
                        <p><strong>Weather Impact:</strong> ${point.impact_score.toFixed(
                          1
                        )}/10</p>
                    </div>
                `
        )
        .addTo(map);

      // Add weather icon based on condition
      const icon = getWeatherIcon(point.impact_score);
      const customIcon = L.divIcon({
        html: `<div style="background-color: rgba(255, 107, 53, 0.8); border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; border: 2px solid white;">${icon}</div>`,
        className: "weather-marker",
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      });

      marker.setIcon(customIcon);
      window.weatherMarkers.push(marker);
    });
  }

  // Add weather markers for fuel-efficient route
  if (data.fuel_efficient_route?.weather_impact?.weather_points) {
    data.fuel_efficient_route.weather_impact.weather_points.forEach(
      (point, index) => {
        const marker = L.marker(point.coordinates)
          .bindPopup(
            `
                    <div class="weather-marker-popup">
                        <h5>🌿 Efficient Route - Point ${index + 1}</h5>
                        <p><strong>Condition:</strong> ${
                          point.weather.condition
                        }</p>
                        <p><strong>Wind Speed:</strong> ${point.weather.wind_speed.toFixed(
                          1
                        )} km/h</p>
                        <p><strong>Wave Height:</strong> ${point.weather.wave_height.toFixed(
                          1
                        )} m</p>
                        <p><strong>Temperature:</strong> ${point.weather.temperature.toFixed(
                          1
                        )}°C</p>
                        <p><strong>Weather Impact:</strong> ${point.impact_score.toFixed(
                          1
                        )}/10</p>
                    </div>
                `
          )
          .addTo(map);

        const icon = getWeatherIcon(point.impact_score);
        const customIcon = L.divIcon({
          html: `<div style="background-color: rgba(46, 204, 113, 0.8); border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; border: 2px solid white;">${icon}</div>`,
          className: "weather-marker",
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        });

        marker.setIcon(customIcon);
        window.weatherMarkers.push(marker);
      }
    );
  }
}

function displayRoutesOnMap(data) {
  console.log("🗺️ Displaying routes on map...");

  // ========== CRITICAL FIX: Clear ALL existing layers FIRST ==========
  if (window.currentRouteLayers) {
    window.currentRouteLayers.forEach((layer) => {
      if (layer && map && map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    });
    window.currentRouteLayers = [];
  }

  // Also clear the existing routeLayers object
  Object.keys(routeLayers).forEach((key) => {
    if (routeLayers[key]) {
      if (Array.isArray(routeLayers[key])) {
        routeLayers[key].forEach((layer) => {
          if (layer && map && map.hasLayer(layer)) {
            map.removeLayer(layer);
          }
        });
      } else if (routeLayers[key] instanceof L.LayerGroup) {
        routeLayers[key].clearLayers();
        if (map && map.hasLayer(routeLayers[key])) {
          map.removeLayer(routeLayers[key]);
        }
      } else if (routeLayers[key] && map && map.hasLayer(routeLayers[key])) {
        map.removeLayer(routeLayers[key]);
      }
      routeLayers[key] = null;
    }
  });

  // Clear port markers
  portMarkers.forEach((marker) => {
    if (marker && marker.remove && map) {
      map.removeLayer(marker);
    }
  });
  portMarkers = [];

  // Clear weather markers
  if (window.weatherMarkers) {
    window.weatherMarkers.forEach((marker) => {
      if (marker && marker.remove && map) {
        map.removeLayer(marker);
      }
    });
    window.weatherMarkers = [];
  }

  // Initialize the new layer tracker
  if (!window.currentRouteLayers) {
    window.currentRouteLayers = [];
  }

  // Check if we have valid data
  if (!data) {
    console.warn("⚠️ No data provided to displayRoutesOnMap");
    return;
  }

  const fastestRoute = data.fastest_route || {};
  const fuelRoute = data.fuel_efficient_route || {};
  const directRoute = data.direct_route || {};

  const fastestPorts = fastestRoute.ports || [];
  const fuelPorts = fuelRoute.ports || [];

  // Only proceed if we have coordinates
  if (!fastestRoute.coordinates && !fuelRoute.coordinates) {
    console.warn("⚠️ No route coordinates to display on map");
    return;
  }

  // Draw routes
  if (fastestRoute.coordinates && fastestRoute.coordinates.length > 1) {
    const polyline = L.polyline(fastestRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.fastest.color,
      weight: 4,
      opacity: 0.7,
      lineCap: "round",
    }).addTo(map);

    // Add dashed version for better visibility
    const dashedLine = L.polyline(fastestRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.fastest.color,
      weight: 2,
      opacity: 0.3,
      dashArray: "15, 10",
      lineCap: "round",
    }).addTo(map);

    const routeGroup = L.layerGroup([polyline, dashedLine]);
    routeLayers.fastest = routeGroup;
    window.currentRouteLayers.push(routeGroup);

    // Add popup with route info
    polyline.bindPopup(`
            <div style="text-align: center; padding: 5px;">
                <h4 style="color: ${
                  NAV_CONFIG.routeTypes.fastest.color
                }; margin: 0 0 10px 0;">🚀 Fastest Route</h4>
                <p style="margin: 5px 0;"><strong>Distance:</strong> ${safeNumberFormat(
                  fastestRoute.distance_km
                )} km</p>
                <p style="margin: 5px 0;"><strong>Time:</strong> ${safeNumberFormat(
                  fastestRoute.time_hours / 24,
                  1
                )} days</p>
                <p style="margin: 5px 0;"><strong>Fuel:</strong> ${safeNumberFormat(
                  fastestRoute.fuel_tonnes,
                  1
                )} tonnes</p>
                ${
                  fastestPorts.length > 2
                    ? `<p style="margin: 5px 0;"><strong>Intermediate Ports:</strong> ${fastestPorts
                        .slice(1, -1)
                        .join(", ")}</p>`
                    : '<p style="margin: 5px 0; color: #888;"><em>Direct Route</em></p>'
                }
            </div>
        `);
  }

  if (fuelRoute.coordinates && fuelRoute.coordinates.length > 1) {
    const polyline = L.polyline(fuelRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.efficient.color,
      weight: 4,
      opacity: 0.7,
      lineCap: "round",
    }).addTo(map);

    // Add dashed version for better visibility
    const dashedLine = L.polyline(fuelRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.efficient.color,
      weight: 2,
      opacity: 0.3,
      dashArray: "10, 15",
      lineCap: "round",
    }).addTo(map);

    const routeGroup = L.layerGroup([polyline, dashedLine]);
    routeLayers.fuel = routeGroup;
    window.currentRouteLayers.push(routeGroup);

    // Add popup with route info
    polyline.bindPopup(`
            <div style="text-align: center; padding: 5px;">
                <h4 style="color: ${
                  NAV_CONFIG.routeTypes.efficient.color
                }; margin: 0 0 10px 0;">🌿 Fuel-Efficient Route</h4>
                <p style="margin: 5px 0;"><strong>Distance:</strong> ${safeNumberFormat(
                  fuelRoute.distance_km
                )} km</p>
                <p style="margin: 5px 0;"><strong>Time:</strong> ${safeNumberFormat(
                  fuelRoute.time_hours / 24,
                  1
                )} days</p>
                <p style="margin: 5px 0;"><strong>Fuel:</strong> ${safeNumberFormat(
                  fuelRoute.fuel_tonnes,
                  1
                )} tonnes</p>
                ${
                  fuelPorts.length > 2
                    ? `<p style="margin: 5px 0;"><strong>Intermediate Ports:</strong> ${fuelPorts
                        .slice(1, -1)
                        .join(", ")}</p>`
                    : '<p style="margin: 5px 0; color: #888;"><em>Direct Route</em></p>'
                }
            </div>
        `);
  }

  // Add direct route if available
  if (directRoute.coordinates && directRoute.coordinates.length > 1) {
    const polyline = L.polyline(directRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.direct.color,
      weight: 2,
      opacity: 0.4,
      dashArray: "5, 10",
      lineCap: "round",
    }).addTo(map);

    routeLayers.direct = polyline;
    window.currentRouteLayers.push(polyline);

    polyline.bindPopup(`
            <div style="text-align: center; padding: 5px;">
                <h4 style="color: ${
                  NAV_CONFIG.routeTypes.direct.color
                }; margin: 0 0 10px 0;">📐 Direct Route</h4>
                <p style="margin: 5px 0; color: #888;"><em>Great circle route (for reference)</em></p>
                <p style="margin: 5px 0;"><strong>Direct distance:</strong> ${safeNumberFormat(
                  calculateDirectDistance(
                    data.port_locations[fastestPorts[0]],
                    data.port_locations[fastestPorts[fastestPorts.length - 1]]
                  )
                )} km</p>
            </div>
        `);
  }

  // Add port markers
  if (data.port_locations) {
    addPortMarkers(data.port_locations, fastestPorts, fuelPorts);
  }

  // Zoom to show all routes
  zoomToRoutes();

  // Update legend
  updateLegend(fastestPorts, fuelPorts);
}

function calculateDirectDistance(coord1, coord2) {
  if (!coord1 || !coord2) return 0;

  const R = 6371; // Earth's radius in km
  const lat1 = (coord1[0] * Math.PI) / 180;
  const lon1 = (coord1[1] * Math.PI) / 180;
  const lat2 = (coord2[0] * Math.PI) / 180;
  const lon2 = (coord2[1] * Math.PI) / 180;

  const dlat = lat2 - lat1;
  const dlon = lon2 - lon1;

  const a =
    Math.sin(dlat / 2) * Math.sin(dlat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dlon / 2) * Math.sin(dlon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// ADD THIS FUNCTION to update the legend:
function updateLegend(fastestPorts, fuelPorts) {
  const legendContent = document.querySelector(".legend-content");
  if (!legendContent) return;

  // Get selected hubs
  const hubPortsSelect = document.getElementById("hubPorts");
  const selectedHubs = Array.from(hubPortsSelect.selectedOptions)
    .map((opt) => opt.value)
    .filter((port) => port !== "");

  // Create legend HTML
  legendContent.innerHTML = `
        <div class="legend-item">
            <div class="color-swatch" style="background-color: #27ae60;"></div>
            <span>Start Port</span>
        </div>
        <div class="legend-item">
            <div class="color-swatch" style="background-color: #e74c3c;"></div>
            <span>Destination Port</span>
        </div>
        <div class="legend-item">
            <div class="color-swatch" style="background-color: ${
              NAV_CONFIG.routeTypes.fastest.color
            };"></div>
            <span>Fastest Route</span>
        </div>
        <div class="legend-item">
            <div class="color-swatch" style="background-color: ${
              NAV_CONFIG.routeTypes.efficient.color
            };"></div>
            <span>Fuel-Efficient Route</span>
        </div>
        <div class="legend-item">
            <div class="color-swatch" style="background-color: ${
              NAV_CONFIG.routeTypes.direct.color
            }; opacity: 0.4;"></div>
            <span>Direct Route (reference)</span>
        </div>
        ${
          selectedHubs.length > 0
            ? `
        <div class="legend-item">
            <div class="color-swatch" style="background-color: #9b59b6;"></div>
            <span>Intermediate Ports</span>
        </div>
        `
            : ""
        }
    `;
}

function addPortMarkers(portLocations, fastestPorts, fuelPorts) {
  Object.entries(portLocations).forEach(([port, coords]) => {
    let color = "#94a3b8"; // gray
    let iconHtml = "⚓";
    let popupClass = "other-port";

    if (port === fastestPorts[0]) {
      color = "#27ae60"; // darkgreen
      iconHtml = "🟢";
      popupClass = "start-port";
    } else if (port === fastestPorts[fastestPorts.length - 1]) {
      color = "#e74c3c"; // darkred
      iconHtml = "🔴";
      popupClass = "destination-port";
    } else if (fastestPorts.includes(port) && fuelPorts.includes(port)) {
      color = "#9b59b6"; // purple
      iconHtml = "🟣";
      popupClass = "shared-hub";
    } else if (fastestPorts.includes(port)) {
      color = "#ff6b35"; // orange
      iconHtml = "🟠";
      popupClass = "fastest-hub";
    } else if (fuelPorts.includes(port)) {
      color = "#2ecc71"; // green
      iconHtml = "🟢";
      popupClass = "fuel-hub";
    }

    // Create custom icon
    const customIcon = L.divIcon({
      html: `<div style="background-color: ${color}; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${iconHtml}</div>`,
      className: "custom-port-icon",
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const marker = L.marker(coords, { icon: customIcon })
      .bindPopup(
        `
                <div style="text-align: center;" class="${popupClass}">
                    <strong>${port}</strong><br>
                    Lat: ${safeNumberFormat(coords[0], 4)}<br>
                    Lon: ${safeNumberFormat(coords[1], 4)}<br>
                    ${port === fastestPorts[0] ? "<em>Start Port</em>" : ""}
                    ${
                      port === fastestPorts[fastestPorts.length - 1]
                        ? "<em>Destination Port</em>"
                        : ""
                    }
                    ${
                      fastestPorts.includes(port) &&
                      port !== fastestPorts[0] &&
                      port !== fastestPorts[fastestPorts.length - 1]
                        ? "<em>Route Hub</em>"
                        : ""
                    }
                </div>
            `
      )
      .addTo(map);

    portMarkers.push(marker);
  });
}

// Navigation functions
function navLoadSection(section) {
  console.log("Loading section:", section);

  // Remove active class from all nav items
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.remove("active");
  });

  // Add active class to clicked nav item
  const clickedItem = event.target.closest(".nav-item");
  if (clickedItem) {
    clickedItem.classList.add("active");
  }

  // Handle different sections
  switch (section) {
    case "planner":
      showPlannerSection();
      break;
    case "analytics":
      showAnalyticsSection();
      break;
    case "ports":
      showPortsDatabase();
      break;
    case "fleet":
    case "reports":
    case "weather":
    case "fuel":
      showToolSection(section);
      break;
    default:
      showPlannerSection();
      alert(`${section} section coming soon!`);
  }
}

function showPlannerSection() {
  // Show main content
  document.querySelector(".main-content").style.display = "grid";

  // Hide analytics section
  const analyticsSection = document.getElementById("analyticsSection");
  if (analyticsSection) {
    analyticsSection.style.display = "none";
  }

  // Ensure map is properly sized
  setTimeout(() => {
    if (map) {
      map.invalidateSize();
    }
  }, 100);
}

function showAnalyticsSection() {
  // Hide main content
  document.querySelector(".main-content").style.display = "none";

  // Show analytics section
  const analyticsSection = document.getElementById("analyticsSection");
  if (analyticsSection) {
    analyticsSection.style.display = "block";
    loadAnalyticsDashboard();
  }
}

function showPortsDatabase() {
  showPlannerSection();
  alert("Port Database feature coming soon!");
}

function showToolSection(tool) {
  showPlannerSection();
  alert(`${NAV_CONFIG.sections.tools.submenu[tool].name} feature coming soon!`);
}

function navToggleProfileMenu() {
  const menu = document.querySelector(".profile-menu");
  if (menu) {
    const isVisible = menu.style.display === "block";
    menu.style.display = isVisible ? "none" : "block";
  }
}

function navToggleMobileMenu() {
  const nav = document.querySelector(".main-nav");
  const toggle = document.querySelector(".mobile-menu-toggle");
  if (nav && toggle) {
    nav.classList.toggle("mobile-active");
    toggle.classList.toggle("active");
  }
}

function navShowNotifications() {
  alert("Notifications feature coming soon!");
}

function navOpenSettings() {
  alert("Settings feature coming soon!");
}

function navLogout() {
  if (confirm("Are you sure you want to logout?")) {
    alert("Logout successful!");
    // Redirect to login page or perform logout logic
  }
}

// Map control functions
function toggleRoute(routeType) {
  const layer = routeLayers[routeType];
  const buttons = document.querySelectorAll(".control-btn");

  if (layer) {
    if (map.hasLayer(layer)) {
      map.removeLayer(layer);
      // Update button active state
      buttons.forEach((btn) => {
        if (
          btn.textContent.includes(
            routeType === "fastest"
              ? "Fastest"
              : routeType === "fuel"
              ? "Efficient"
              : "Direct"
          )
        ) {
          btn.classList.remove("active");
        }
      });
    } else {
      layer.addTo(map);
      // Update button active state
      buttons.forEach((btn) => {
        if (
          btn.textContent.includes(
            routeType === "fastest"
              ? "Fastest"
              : routeType === "fuel"
              ? "Efficient"
              : "Direct"
          )
        ) {
          btn.classList.add("active");
        }
      });
    }
  }
}

function toggleAllRoutes() {
  const routes = ["fastest", "fuel", "direct"];
  const allVisible = routes.every(
    (route) => routeLayers[route] && map.hasLayer(routeLayers[route])
  );

  routes.forEach((route) => {
    const layer = routeLayers[route];
    if (layer) {
      if (allVisible) {
        map.removeLayer(layer);
      } else {
        layer.addTo(map);
      }
    }
  });

  // Update button states
  const buttons = document.querySelectorAll(".control-btn");
  buttons.forEach((btn) => {
    if (allVisible) {
      btn.classList.remove("active");
    } else {
      btn.classList.add("active");
    }
  });
}

function zoomToRoutes() {
  if (!currentMapData) return;

  const allCoords = [];

  // Collect coordinates from all routes
  if (
    currentMapData.fastest_route &&
    currentMapData.fastest_route.coordinates
  ) {
    allCoords.push(...currentMapData.fastest_route.coordinates);
  }
  if (
    currentMapData.fuel_efficient_route &&
    currentMapData.fuel_efficient_route.coordinates
  ) {
    allCoords.push(...currentMapData.fuel_efficient_route.coordinates);
  }
  if (currentMapData.direct_route && currentMapData.direct_route.coordinates) {
    allCoords.push(...currentMapData.direct_route.coordinates);
  }

  // Add port coordinates
  if (currentMapData.port_locations) {
    Object.values(currentMapData.port_locations).forEach((coords) => {
      allCoords.push(coords);
    });
  }

  if (allCoords.length > 0) {
    const bounds = L.latLngBounds(allCoords);
    map.fitBounds(bounds, { padding: [50, 50] });
  }
}

function toggleLegend() {
  const legendContent = document.querySelector(".legend-content");
  const legendToggle = document.querySelector(".legend-toggle");

  if (legendContent.style.display === "none") {
    legendContent.style.display = "flex";
    legendToggle.textContent = "−";
  } else {
    legendContent.style.display = "none";
    legendToggle.textContent = "+";
  }
}

function toggleFullscreen() {
  const mapContainer = document.querySelector(".map-container");

  if (!document.fullscreenElement) {
    mapContainer.requestFullscreen().catch((err) => {
      console.log(`Error attempting to enable fullscreen: ${err.message}`);
    });
  } else {
    document.exitFullscreen();
  }
}

async function loadAnalyticsDashboard() {
  try {
    console.log("🔄 Loading real-time analytics data...");

    // Show loading state
    const refreshBtn = document.querySelector(".btn-refresh");
    if (refreshBtn) {
      refreshBtn.innerHTML = "⏳ Loading...";
      refreshBtn.disabled = true;
    }

    const response = await fetch("/api/realtime-analytics");

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    console.log("✅ Analytics data received:", data);

    // Update the UI with new data
    updateAnalyticsDisplay(data);
  } catch (error) {
    console.error("❌ Error loading analytics:", error);
    // Show fallback data instead of alert
    showFallbackAnalyticsData();
  } finally {
    // Reset button state
    const refreshBtn = document.querySelector(".btn-refresh");
    if (refreshBtn) {
      refreshBtn.innerHTML = "🔄 Refresh";
      refreshBtn.disabled = false;
    }
  }
}

function showFallbackAnalyticsData() {
  console.log("🔄 Showing fallback analytics data");

  // Update performance metrics with fallback data
  document.getElementById("totalCalculations").textContent = "1,247";
  document.getElementById("totalDistanceSaved").textContent = "12,850km"; // ADD THIS
  document.getElementById("totalFuelSaved").textContent = "45.2t";
  document.getElementById("totalTimeSaved").textContent = "12.5d";
  document.getElementById("totalCO2Reduced").textContent = "142.4t";
  document.getElementById("totalCostSaved").textContent = "$29,380";
  // Update recent calculations with fallback
  const recentList = document.getElementById("recentCalculationsList");
  recentList.innerHTML = `
        <div class="recent-item">
            <div class="recent-route">Singapore → Busan</div>
            <div class="recent-meta">
                <span>${new Date().toLocaleTimeString()}</span>
                <span>1.85s</span>
            </div>
        </div>
        <div class="recent-item">
            <div class="recent-route">Jebel_Ali → Shanghai</div>
            <div class="recent-meta">
                <span>${new Date(
                  Date.now() - 300000
                ).toLocaleTimeString()}</span>
                <span>2.34s</span>
            </div>
        </div>
    `;

  // Update port usage with fallback
  const portUsageList = document.getElementById("portUsageList");
  portUsageList.innerHTML = `
        <div class="port-usage-item">
            <span class="port-name">Singapore</span>
            <div class="usage-bar">
                <div class="usage-fill" style="width: 85%"></div>
            </div>
            <span class="usage-percent">85.0%</span>
        </div>
        <div class="port-usage-item">
            <span class="port-name">Shanghai</span>
            <div class="usage-bar">
                <div class="usage-fill" style="width: 72%"></div>
            </div>
            <span class="usage-percent">72.0%</span>
        </div>
        <div class="port-usage-item">
            <span class="port-name">Jebel_Ali</span>
            <div class="usage-bar">
                <div class="usage-fill" style="width: 68%"></div>
            </div>
            <span class="usage-percent">68.0%</span>
        </div>
    `;

  // Update algorithm performance with fallback
  updateAlgorithmPerformance({
    total_calculations: 1247,
    average_calculation_time: 1.85,
    fastest_algorithm: "Genetic Algorithm",
    routes_calculated: 892,
    performance_metrics: {
      a_star_performance: 65.5,
      genetic_algorithm_performance: 34.5,
      total_optimization: 15.0,
    },
  });

  // Update last updated time
  document.getElementById("lastUpdated").textContent =
    new Date().toLocaleString();

  console.log("✅ Fallback analytics data displayed");
}

function updateAlgorithmPerformance(algorithmData) {
  const algorithmStats = document.getElementById("algorithmStats");
  if (!algorithmStats) return;

  // Use actual data from backend or fallback to realistic demo data
  const stats = algorithmData || {
    total_calculations: 1247,
    average_calculation_time: 1.85,
    fastest_algorithm: "A* Algorithm",
    routes_calculated: 892,
    performance_metrics: {
      a_star_performance: 78,
      genetic_algorithm_performance: 92,
      total_optimization: 15,
    },
  };

  // Ensure we have performance metrics
  const performance = stats.performance_metrics || {
    a_star_performance: 65,
    genetic_algorithm_performance: 85,
    total_optimization: 12.5,
  };

  algorithmStats.innerHTML = `
        <div class="algorithm-stat">
            <strong>Total Calculations:</strong> ${
              stats.total_calculations || 0
            }
        </div>
        <div class="algorithm-stat">
            <strong>Avg. Calculation Time:</strong> ${(
              stats.average_calculation_time || 0
            ).toFixed(2)}s
        </div>
        <div class="algorithm-stat">
            <strong>Fastest Algorithm:</strong> ${
              stats.fastest_algorithm || "A*"
            }
        </div>
        <div class="algorithm-stat">
            <strong>Routes Calculated:</strong> ${stats.routes_calculated || 0}
        </div>
        
        <!-- Algorithm Performance Visualization -->
        <div class="performance-visualization">
            <h4>Algorithm Performance Metrics</h4>
            <div class="performance-bar">
                <div class="bar-label">
                    <span>A* Algorithm</span>
                    <span class="algorithm-percent">${
                      performance.a_star_performance || 0
                    }%</span>
                </div>
                <div class="bar-container">
                    <div class="bar-fill" data-algorithm="a_star" style="width: ${
                      performance.a_star_performance || 0
                    }%"></div>
                </div>
            </div>
            <div class="performance-bar">
                <div class="bar-label">
                    <span>Genetic Algorithm</span>
                    <span class="algorithm-percent">${
                      performance.genetic_algorithm_performance || 0
                    }%</span>
                </div>
                <div class="bar-container">
                    <div class="bar-fill" data-algorithm="genetic" style="width: ${
                      performance.genetic_algorithm_performance || 0
                    }%"></div>
                </div>
            </div>
            <div class="performance-bar">
                <div class="bar-label">
                    <span>Total Optimization</span>
                    <span class="algorithm-percent">${
                      performance.total_optimization || 0
                    }%</span>
                </div>
                <div class="bar-container">
                    <div class="bar-fill" data-algorithm="optimization" style="width: ${
                      performance.total_optimization || 0
                    }%"></div>
                </div>
            </div>
        </div>
    `;
}
function validatePortSelection() {
  const startPort = document.getElementById("startPort").value;
  const destinationPort = document.getElementById("destinationPort").value;

  if (!startPort || !destinationPort) {
    return {
      valid: false,
      message: "Please select both start and destination ports",
    };
  }

  if (startPort === destinationPort) {
    return {
      valid: false,
      message: "Start and destination ports cannot be the same",
    };
  }

  // Check if ports exist in your database
  const validPorts = [
    "Tokyo",
    "Singapore",
    "Shanghai",
    "Rotterdam",
    "New York",
  ]; // Example
  if (
    !validPorts.includes(startPort) ||
    !validPorts.includes(destinationPort)
  ) {
    return { valid: false, message: "One or more selected ports are invalid" };
  }

  return { valid: true };
}

function refreshMapWithNewData() {
  console.log("🗺️ [PROFESSIONAL] Refreshing map for new calculation...");

  if (!map) {
    console.warn("⚠️ Map not initialized yet");
    return;
  }

  // 1. Remove all non-base layers
  map.eachLayer((layer) => {
    if (!(layer instanceof L.TileLayer)) {
      map.removeLayer(layer);
    }
  });

  // 2. Reset tracking variables
  routeLayers = {
    fastest: null,
    fuel: null,
    direct: null,
  };

  portMarkers = [];

  if (window.weatherMarkers) {
    window.weatherMarkers = [];
  }

  if (window.currentRouteLayers) {
    window.currentRouteLayers = [];
  }

  // 3. Reset current data
  currentMapData = null;

  console.log("✅ Map cleared - ready for new routes");
}
function clearForm() {
  resetEverything();
}

function setupEventListeners() {
  const calculateBtn = document.getElementById("calculateBtn");
  if (calculateBtn) {
    calculateBtn.addEventListener("click", calculateRoutes);
  }

  // Get form elements
  const startPort = document.getElementById("startPort");
  const destinationPort = document.getElementById("destinationPort");
  const hubPorts = document.getElementById("hubPorts");

  // NO map refresh on form changes! Only UI updates
  if (startPort) {
    startPort.addEventListener("change", function () {
      console.log("Start port changed");
      showRouteSuggestions();
    });
  }

  if (destinationPort) {
    destinationPort.addEventListener("change", function () {
      console.log("Destination port changed");
      showRouteSuggestions();
    });
  }

  if (hubPorts) {
    hubPorts.addEventListener("change", function () {
      console.log("Hub ports changed");
      updateSelectedPortsDisplay(); // Only update UI, NO map refresh
    });
  }

  // No automatic refreshes for radio buttons
  document.querySelectorAll('input[name="goal"]').forEach((radio) => {
    radio.addEventListener("change", function () {
      console.log("Optimization goal changed to:", this.value);
      // Nothing - wait for calculate
    });
  });

  document.querySelectorAll('input[name="weather"]').forEach((radio) => {
    radio.addEventListener("change", function () {
      console.log("Weather option changed to:", this.value);
      // Nothing - wait for calculate
    });
  });

  // Add event listener for intermediate ports selection
  document
    .getElementById("hubPorts")
    .addEventListener("change", updateSelectedPortsDisplay);
}

function renderPerformanceBars(metrics) {
  if (!metrics) {
    return `
            <div class="performance-bar">
                <div class="bar-label">A* Algorithm</div>
                <div class="bar-container">
                    <div class="bar-fill" data-algorithm="a_star" style="width: 85%"></div>
                    <span class="bar-value">85%</span>
                </div>
            </div>
            <div class="performance-bar">
                <div class="bar-label">Genetic Algorithm</div>
                <div class="bar-container">
                    <div class="bar-fill" data-algorithm="genetic" style="width: 92%"></div>
                    <span class="bar-value">92%</span>
                </div>
            </div>
            <div class="performance-bar">
                <div class="bar-label">Total Optimization</div>
                <div class="bar-container">
                    <div class="bar-fill" data-algorithm="optimization" style="width: 12.5%"></div>
                    <span class="bar-value">12.5%</span>
                </div>
            </div>
        `;
  }

  return `
        <div class="performance-bar">
            <div class="bar-label">A* Algorithm</div>
            <div class="bar-container">
                <div class="bar-fill" data-algorithm="a_star" style="width: ${
                  metrics.a_star_performance || 0
                }%"></div>
                <span class="bar-value">${
                  metrics.a_star_performance || 0
                }%</span>
            </div>
        </div>
        <div class="performance-bar">
            <div class="bar-label">Genetic Algorithm</div>
            <div class="bar-container">
                <div class="bar-fill" data-algorithm="genetic" style="width: ${
                  metrics.genetic_algorithm_performance || 0
                }%"></div>
                <span class="bar-value">${
                  metrics.genetic_algorithm_performance || 0
                }%</span>
            </div>
        </div>
        <div class="performance-bar">
            <div class="bar-label">Total Optimization</div>
            <div class="bar-container">
                <div class="bar-fill" data-algorithm="optimization" style="width: ${
                  metrics.total_optimization || 0
                }%"></div>
                <span class="bar-value">${
                  metrics.total_optimization || 0
                }%</span>
            </div>
        </div>
    `;
}

function showFallbackAlgorithmData() {
  const algorithmStats = document.getElementById("algorithmStats");
  if (!algorithmStats) return;

  algorithmStats.innerHTML = `
        <div class="algorithm-stat">
            <div class="stat-header">
                <strong>Total Calculations:</strong>
                <span class="stat-value">1,247</span>
            </div>
        </div>
        <div class="algorithm-stat">
            <div class="stat-header">
                <strong>Avg. Calculation Time:</strong>
                <span class="stat-value">1.85s</span>
            </div>
        </div>
        <div class="algorithm-stat">
            <div class="stat-header">
                <strong>Fastest Algorithm:</strong>
                <span class="stat-value">Genetic Algorithm</span>
            </div>
        </div>
        <div class="algorithm-stat">
            <div class="stat-header">
                <strong>Routes Calculated:</strong>
                <span class="stat-value">892</span>
            </div>
        </div>
        
        <div class="performance-visualization">
            <h4>Algorithm Performance Metrics</h4>
            <div class="performance-bar">
                <div class="bar-label">A* Algorithm</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: 85%"></div>
                    <span class="bar-value">85%</span>
                </div>
            </div>
            <div class="performance-bar">
                <div class="bar-label">Genetic Algorithm</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: 92%"></div>
                    <span class="bar-value">92%</span>
                </div>
            </div>
            <div class="performance-bar">
                <div class="bar-label">Dijkstra</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: 78%"></div>
                    <span class="bar-value">78%</span>
                </div>
            </div>
            <div class="performance-bar">
                <div class="bar-label">Total Optimization</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: 15%"></div>
                    <span class="bar-value">15%</span>
                </div>
            </div>
        </div>
    `;
}

function updateAnalyticsDisplay(data) {
  console.log("📊 Updating analytics display with data:", data);

  // Update performance metrics
  const metrics = data.performance_metrics || {};
  document.getElementById("totalCalculations").textContent =
    metrics.total_calculations?.toLocaleString() || "1,247";
  document.getElementById("totalDistanceSaved").textContent =
    (metrics.total_distance_saved || 12850).toFixed(0) + "km";
  document.getElementById("totalFuelSaved").textContent =
    (metrics.total_fuel_saved || 45.2).toFixed(1) + "t";
  document.getElementById("totalTimeSaved").textContent =
    (metrics.total_time_saved || 12.5).toFixed(1) + "d";
  document.getElementById("totalCO2Reduced").textContent =
    (metrics.total_co2_reduced || 142.4).toFixed(1) + "t";
  document.getElementById("totalCostSaved").textContent =
    "$" + (metrics.total_cost_saved || 29380).toLocaleString();

  // Update recent calculations
  const recentList = document.getElementById("recentCalculationsList");
  const recentCalcs = data.recent_calculations || [];

  if (recentCalcs.length > 0) {
    recentList.innerHTML = recentCalcs
      .slice()
      .reverse()
      .map(
        (calc) => `
            <div class="recent-item">
                <div class="recent-route">${calc.start_port} → ${
          calc.destination_port
        }</div>
                <div class="recent-meta">
                    <span>${new Date(
                      calc.timestamp
                    ).toLocaleTimeString()}</span>
                    <span>${(calc.calculation_time || 0).toFixed(2)}s</span>
                </div>
            </div>
        `
      )
      .join("");
  } else {
    recentList.innerHTML =
      '<div class="recent-item">No recent calculations</div>';
  }

  // Update port usage
  const portUsageList = document.getElementById("portUsageList");
  const portUsage = data.port_usage || {};

  if (Object.keys(portUsage).length > 0) {
    portUsageList.innerHTML = Object.entries(portUsage)
      .sort((a, b) => b[1] - a[1])
      .map(
        ([port, percentage]) => `
                <div class="port-usage-item">
                    <span class="port-name">${port}</span>
                    <div class="usage-bar">
                        <div class="usage-fill" style="width: ${percentage}%"></div>
                    </div>
                    <span class="usage-percent">${percentage.toFixed(1)}%</span>
                </div>
            `
      )
      .join("");
  } else {
    portUsageList.innerHTML =
      '<div class="port-usage-item">No port usage data</div>';
  }

  // Update algorithm performance
  updateAlgorithmPerformance(data.algorithm_stats || {});

  // Update last updated time
  document.getElementById("lastUpdated").textContent = new Date(
    data.timestamp || Date.now()
  ).toLocaleString();

  console.log("✅ Analytics display updated successfully");
}
function backToPlanner() {
  showPlannerSection();
}

// Close dropdowns when clicking outside
document.addEventListener("click", function (event) {
  // Close profile menu
  const profileMenu = document.querySelector(".profile-menu");
  const profileButton = document.querySelector(".btn-profile");
  if (
    profileMenu &&
    profileButton &&
    !profileButton.contains(event.target) &&
    !profileMenu.contains(event.target)
  ) {
    profileMenu.style.display = "none";
  }

  // Close mobile menu when clicking outside
  const mobileNav = document.querySelector(".main-nav");
  const mobileToggle = document.querySelector(".mobile-menu-toggle");
  if (
    window.innerWidth <= 768 &&
    mobileNav &&
    mobileNav.classList.contains("mobile-active") &&
    !mobileNav.contains(event.target) &&
    !mobileToggle.contains(event.target)
  ) {
    mobileNav.classList.remove("mobile-active");
    mobileToggle.classList.remove("active");
  }
});

// Handle window resize
window.addEventListener("resize", function () {
  if (window.innerWidth > 768) {
    const mobileNav = document.querySelector(".main-nav");
    const mobileToggle = document.querySelector(".mobile-menu-toggle");
    if (mobileNav) {
      mobileNav.classList.remove("mobile-active");
    }
    if (mobileToggle) {
      mobileToggle.classList.remove("active");
    }
  }
});

// Auto-refresh analytics every 10 seconds when on analytics page
setInterval(() => {
  const analyticsSection = document.getElementById("analyticsSection");
  if (analyticsSection && analyticsSection.style.display !== "none") {
    loadAnalyticsDashboard();
  }
}, 10000);

// Real-time statistics functions
function updateRouteStatistics(data) {
  if (!data) return;

  const fastestRoute = data.fastest_route || {};
  const fuelRoute = data.fuel_efficient_route || {};

  console.log("📊 Updating route statistics with data:", data);

  // Calculate average transit time
  const avgTime =
    ((fastestRoute.time_hours || 0) + (fuelRoute.time_hours || 0)) / 2;
  document.getElementById("avgTransitTime").textContent =
    avgTime > 0 ? `${(avgTime / 24).toFixed(1)} days` : "--";

  // Calculate fuel efficiency (lower is better)
  const fuelEfficiency =
    ((fuelRoute.fuel_tonnes || 0) / (fuelRoute.distance_km || 1)) * 100;
  document.getElementById("fuelEfficiency").textContent =
    fuelEfficiency > 0 ? `${fuelEfficiency.toFixed(2)} t/100km` : "--";

  // ✅ FIXED: Calculate distance saved - FASTEST vs FUEL-EFFICIENT
  const distanceSaved =
    (fastestRoute.distance_km || 0) - (fuelRoute.distance_km || 0);
  if (distanceSaved > 0) {
    document.getElementById(
      "distanceSaved"
    ).textContent = `${distanceSaved.toFixed(0)} km saved`;
  } else if (distanceSaved < 0) {
    document.getElementById("distanceSaved").textContent = `${Math.abs(
      distanceSaved
    ).toFixed(0)} km added`;
  } else {
    document.getElementById("distanceSaved").textContent = "No difference";
  }

  // Calculate cost savings (estimated)
  const fuelPricePerTonne = 600; // USD per tonne
  const costSavings =
    ((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) *
    fuelPricePerTonne;

  if (costSavings > 0) {
    document.getElementById(
      "costSavings"
    ).textContent = `$${costSavings.toFixed(0)} saved`;
  } else if (costSavings < 0) {
    document.getElementById("costSavings").textContent = `-$${Math.abs(
      costSavings
    ).toFixed(0)}`;
  } else {
    document.getElementById("costSavings").textContent = "--";
  }

  // Update route comparison
  updateRouteComparison(fastestRoute, fuelRoute);

  // Update timestamp
  document.getElementById(
    "statsLastUpdated"
  ).textContent = `Updated: ${new Date().toLocaleTimeString()}`;
}

function clearAllData() {
  console.log("🧹 Clearing all data...");

  // Reset form
  document.getElementById("startPort").value = "";
  document.getElementById("destinationPort").value = "";

  const hubPortsSelect = document.getElementById("hubPorts");
  if (hubPortsSelect) {
    Array.from(hubPortsSelect.options).forEach((option) => {
      option.selected = false;
    });
  }

  // Reset radio buttons
  document.querySelectorAll('input[name="goal"]').forEach((radio) => {
    radio.checked = radio.value === "both";
  });

  // Update selected ports display
  updateSelectedPortsDisplay();

  // Now clear the map
  refreshMapWithNewData();

  // Also reset currentMapData to ensure everything is cleared
  currentMapData = null;

  console.log("✅ All data cleared");
}
// Quick actions functions
function saveCurrentRoute() {
  if (!currentMapData) {
    alert("No route data to save. Please calculate a route first.");
    return;
  }

  const routeData = {
    timestamp: new Date().toISOString(),
    data: currentMapData,
  };

  // Save to localStorage (you can replace with API call)
  const savedRoutes = JSON.parse(localStorage.getItem("savedRoutes") || "[]");
  savedRoutes.push(routeData);
  localStorage.setItem("savedRoutes", JSON.stringify(savedRoutes));

 notify.success("Route saved successfully!", "Route Saved");

}

function compareWithPrevious() {
  const savedRoutes = JSON.parse(localStorage.getItem("savedRoutes") || "[]");
  if (savedRoutes.length === 0) {
  notify.info("No saved routes to compare with.", "No Saved Routes");
    return;
  }

  // Show comparison modal or implement comparison logic
  alert(`Found ${savedRoutes.length} saved routes for comparison.`);
}

function exportRouteData() {
  if (!currentMapData) {
    alert("No route data to export. Please calculate a route first.");
    return;
  }

  const dataStr = JSON.stringify(currentMapData, null, 2);
  const dataBlob = new Blob([dataStr], { type: "application/json" });

  const url = URL.createObjectURL(dataBlob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `route-data-${new Date().toISOString().split("T")[0]}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// Initialize with demo data or reset function
function resetStatistics() {
  document.getElementById("avgTransitTime").textContent = "--";
  document.getElementById("fuelEfficiency").textContent = "--";
  document.getElementById("distanceSaved").textContent = "--";
  document.getElementById("costSavings").textContent = "--";
  document.getElementById("statsLastUpdated").textContent = "--";
  document.getElementById("routeComparison").style.display = "none";
}

// Call reset when clearing form
function clearForm() {
  document.getElementById("startPort").value = "";
  document.getElementById("destinationPort").value = "";

  // Clear multiple select
  clearSelectedPorts();

  // Reset radio buttons
  document.querySelector('input[name="goal"][value="both"]').checked = true;

  // Hide results
  document.getElementById("resultsPanel").style.display = "none";

  // Clear map
  Object.values(routeLayers).forEach((layer) => {
    if (layer) map.removeLayer(layer);
  });

  portMarkers.forEach((marker) => map.removeLayer(marker));
  portMarkers = [];

  // Reset map view
  map.setView([20, 0], 2);

  // Reset statistics
  resetStatistics(); // ADD THIS LINE
}
// Force fix legend position
function fixLegendPosition() {
  const legend = document.getElementById("mapLegend");
  if (legend) {
    // Move to bottom right
    legend.style.top = "auto";
    legend.style.bottom = "80px";
    legend.style.right = "20px";
    legend.style.left = "auto";

    // Ensure it's visible
    legend.style.display = "block";
    legend.style.zIndex = "1000";
  }
}
function toggleStatsInfo() {
  const infoContent = document.getElementById("statsInfoContent");
  const toggleBtn = document.querySelector(".info-toggle");

  if (
    infoContent.style.display === "none" ||
    infoContent.style.display === ""
  ) {
    infoContent.style.display = "block";
    toggleBtn.textContent = "−";
    toggleBtn.title = "Hide statistics info";
  } else {
    infoContent.style.display = "none";
    toggleBtn.textContent = "ℹ️";
    toggleBtn.title = "Show statistics info";
  }
}
function updateDashboardHeightBasedOnComparison() {
  const dashboard = document.querySelector(".metrics-dashboard");
  const routeComparison = document.getElementById("routeComparison");

  if (!dashboard) return;

  // Check if route comparison section is visible AND has actual data
  const isComparisonVisible =
    routeComparison && routeComparison.style.display === "block";

  // Get the actual comparison values
  const timeDiffElement = document.getElementById("timeDifference");
  const fuelDiffElement = document.getElementById("fuelDifference");

  let hasActualComparisonData = false;

  if (isComparisonVisible && timeDiffElement && fuelDiffElement) {
    const timeText = timeDiffElement.textContent || "";
    const fuelText = fuelDiffElement.textContent || "";

    // ✅ Check if values are ACTUAL comparison data (not "--" or placeholders)
    // Actual data would be like: "-1.3 days", "-377.5 tonnes", "+2.4 days", etc.
    hasActualComparisonData =
      timeText !== "--" &&
      timeText !== "" &&
      timeText !== "No difference" &&
      !timeText.includes("Select ports") &&
      fuelText !== "--" &&
      fuelText !== "" &&
      fuelText !== "No difference" &&
      !fuelText.includes("Select ports");
  }

  console.log("🔍 Route Comparison Height Check:", {
    isComparisonVisible,
    hasActualComparisonData,
    timeValue: timeDiffElement ? timeDiffElement.textContent : "none",
    fuelValue: fuelDiffElement ? fuelDiffElement.textContent : "none",
  });

  // ✅ ONLY change height if BOTH are true
  if (isComparisonVisible && hasActualComparisonData) {
    // Route Comparison IS GENERATED with actual values - Increase height to 900px
    dashboard.style.minHeight = "900px";
    dashboard.style.height = "900px";
    console.log(
      "📈 Dashboard height INCREASED to 900px (Route Comparison HAS REAL DATA)"
    );
  } else {
    // DEFAULT or NO comparison - Keep height at 850px
    dashboard.style.minHeight = "850px";
    dashboard.style.height = "850px";
    console.log(
      "📏 Dashboard height RESET to 850px (No Route Comparison or only placeholders)"
    );
  }
}
function resetEverything() {
  console.log("🧹 Resetting everything...");

  // Clear the map
  refreshMapWithNewData();

  // Reset form inputs
  document.getElementById("startPort").value = "";
  document.getElementById("destinationPort").value = "";

  const hubPortsSelect = document.getElementById("hubPorts");
  if (hubPortsSelect) {
    Array.from(hubPortsSelect.options).forEach((option) => {
      option.selected = false;
    });
  }

  // Reset radio buttons
  document.querySelectorAll('input[name="goal"]').forEach((radio) => {
    radio.checked = radio.value === "both";
  });

  document.querySelectorAll('input[name="weather"]').forEach((radio) => {
    radio.checked = radio.value === "true";
  });

  // Update UI
  updateSelectedPortsDisplay();

  // Hide results panel
  const resultsPanel = document.getElementById("resultsPanel");
  if (resultsPanel) {
    resultsPanel.style.display = "none";
  }

  // Reset route comparison
  const routeComparison = document.getElementById("routeComparison");
  if (routeComparison) {
    routeComparison.style.display = "none";
    // Set values back to "--"
    document.getElementById("timeDifference").textContent = "--";
    document.getElementById("fuelDifference").textContent = "--";
    document.getElementById("recommendedRoute").textContent = "--";
  }

  // Reset dashboard height to default
  updateDashboardHeightBasedOnComparison();

  // Reset map view
  if (map) {
    setTimeout(() => {
      map.setView([20, 0], 2);
      map.invalidateSize();
    }, 50);
  }

  console.log("✅ Everything reset successfully");
}

// Call this whenever the page loads
document.addEventListener("DOMContentLoaded", function () {
  // Initialize dashboard height
  updateDashboardHeightBasedOnComparison();
});

document.addEventListener("DOMContentLoaded", function () {
  // Set initial dashboard height
  setTimeout(() => {
    updateDashboardHeightBasedOnComparison();
  }, 100);
});

function updateRouteComparison(fastestRoute, fuelRoute) {
  console.log("🔄 Checking if route comparison should be generated...");

  const timeDiff = (fuelRoute.time_hours || 0) - (fastestRoute.time_hours || 0);
  const fuelDiff =
    (fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0);

  const comparisonSection = document.getElementById("routeComparison");

  if (comparisonSection) {
    // CRITICAL: Only generate comparison if there are SIGNIFICANT differences
    const shouldGenerateComparison =
      Math.abs(timeDiff) > 2 || Math.abs(fuelDiff) > 0.5;

    if (shouldGenerateComparison) {
      // 1. Show the comparison section
      comparisonSection.style.display = "block";

      // 2. Set REAL comparison values
      if (timeDiff > 0) {
        document.getElementById("timeDifference").textContent = `+${(
          timeDiff / 24
        ).toFixed(1)} days`;
        document.getElementById("timeDifference").className =
          "comparison-value negative";
      } else if (timeDiff < 0) {
        document.getElementById("timeDifference").textContent = `${(
          timeDiff / 24
        ).toFixed(1)} days`;
        document.getElementById("timeDifference").className =
          "comparison-value positive";
      } else {
        document.getElementById("timeDifference").textContent = "No difference";
        document.getElementById("timeDifference").className =
          "comparison-value neutral";
      }

      if (fuelDiff > 0) {
        document.getElementById(
          "fuelDifference"
        ).textContent = `-${fuelDiff.toFixed(1)} tonnes`;
        document.getElementById("fuelDifference").className =
          "comparison-value positive";
      } else if (fuelDiff < 0) {
        document.getElementById("fuelDifference").textContent = `+${Math.abs(
          fuelDiff
        ).toFixed(1)} tonnes`;
        document.getElementById("fuelDifference").className =
          "comparison-value negative";
      } else {
        document.getElementById("fuelDifference").textContent = "No difference";
        document.getElementById("fuelDifference").className =
          "comparison-value neutral";
      }

      if (fuelDiff > 5 && timeDiff < 24) {
        document.getElementById("recommendedRoute").textContent =
          "Efficient Route 🌿";
      } else if (timeDiff > 24 && fuelDiff < 5) {
        document.getElementById("recommendedRoute").textContent =
          "Fastest Route 🚀";
      } else {
        document.getElementById("recommendedRoute").textContent =
          "Balanced Route ⚖️";
      }

      document.getElementById("recommendedRoute").className =
        "comparison-value positive";

      console.log("🔄 Route Comparison GENERATED:", {
        timeDiff,
        fuelDiff,
        shouldGenerateComparison,
      });

      // 3. ONLY update dashboard height AFTER comparison is generated
      setTimeout(() => {
        updateDashboardHeightBasedOnComparison();
      }, 100);
    } else {
      // HIDE the comparison if no significant differences
      comparisonSection.style.display = "none";

      // Reset values to "--" (placeholders)
      document.getElementById("timeDifference").textContent = "--";
      document.getElementById("fuelDifference").textContent = "--";
      document.getElementById("recommendedRoute").textContent = "--";

      console.log(
        "🚫 Route Comparison NOT generated (insignificant differences):",
        {
          timeDiff,
          fuelDiff,
          shouldGenerateComparison,
        }
      );

      // Reset dashboard height
      updateDashboardHeightBasedOnComparison();
    }
  }
}
// Call this whenever the state changes
function setupDynamicHeight() {
  // Monitor port selection changes
  document.getElementById("hubPorts").addEventListener("change", function () {
    setTimeout(updateDashboardHeight, 100);
  });

  // Monitor radio button changes
  document.querySelectorAll('input[name="goal"]').forEach((radio) => {
    radio.addEventListener("change", updateDashboardHeight);
  });

  // Monitor calculation
  document
    .getElementById("calculateBtn")
    .addEventListener("click", function () {
      setTimeout(updateDashboardHeight, 500); // After results are shown
    });

  // Monitor clear button
  const clearBtn = document.querySelector(
    '.btn-secondary[onclick="resetEverything()"]'
  );
  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      setTimeout(updateDashboardHeight, 100);
    });
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  setupDynamicHeight();
  // Set initial height
});
// Call this function whenever something changes
function setupHeightManagement() {
  // Monitor form changes
  document
    .getElementById("hubPorts")
    .addEventListener("change", updateDashboardHeight);
  document.querySelectorAll('input[name="weather"]').forEach((radio) => {
    radio.addEventListener("change", updateDashboardHeight);
  });

  // Monitor calculate button
  document
    .getElementById("calculateBtn")
    .addEventListener("click", function () {
      setTimeout(updateDashboardHeight, 100);
    });

  // Monitor loading state
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.attributeName === "style") {
      }
    });
  });

  const loadingOverlay = document.getElementById("loadingOverlay");
  if (loadingOverlay) {
    observer.observe(loadingOverlay, { attributes: true });
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  setupHeightManagement();
});


// footer.js - Professional Footer Manager
class FooterManager {
    constructor() {
        this.initializeFooter();
        this.setupEventListeners();
        this.startLiveUpdates();
    }

    initializeFooter() {
        console.log("🚢 Initializing professional footer system...");
        
        // Initialize elements
        this.updateAllStatistics();
        this.updateCopyrightYear();
        this.updateRealTimeClock();
        
        // Set initial values
        this.setInitialValues();
    }

    setInitialValues() {
        // Set initial metrics
        document.getElementById('footerRoutesCalculated').textContent = '1,247';
        document.getElementById('footerFuelSaved').textContent = '45.2t';
        document.getElementById('totalDistanceSaved').textContent = '12.5k';
        document.getElementById('githubStars').textContent = '⭐ 42';
        document.getElementById('linkedinFollowers').textContent = '👥 1.2k';
        document.getElementById('twitterFollowers').textContent = '🐦 856';
        document.getElementById('discordMembers').textContent = '👥 342';
        document.getElementById('buildNumber').textContent = '4218';
        document.getElementById('techCount').textContent = '12';
        document.getElementById('totalTechs').textContent = '12';
        document.getElementById('activeTechs').textContent = '12';
        document.getElementById('supportResponseTime').textContent = '15 min';
        
        // Navigation progress
        this.updateNavigationProgress();
    }

    setupEventListeners() {
        // Navigation cards
        document.querySelectorAll('.nav-card').forEach(card => {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                const section = card.getAttribute('onclick').match(/navLoadSection\('(.+?)'\)/)[1];
                navLoadSection(section);
                this.markNavAsVisited(card);
            });
        });

        // Tech category toggles
        document.querySelectorAll('.tech-category').forEach(category => {
            category.addEventListener('click', () => this.toggleTechCategory(category));
        });

        // Contact items
        document.querySelectorAll('.contact-item[data-copy]').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('contact-action')) {
                    const email = item.getAttribute('data-copy');
                    navigator.clipboard.writeText(email);
                    this.showToast(`Copied ${email} to clipboard!`, 'success');
                }
            });
        });

        // Social links
        document.querySelectorAll('.social-link').forEach(link => {
            link.addEventListener('click', (e) => {
                if (!e.target.classList.contains('social-link')) return;
                this.showToast(`Opening ${link.dataset.social}...`, 'info');
            });
        });

        // Back to top
        document.querySelector('.btn-back-to-top').addEventListener('click', () => {
            this.scrollToTop();
        });

        // System status indicator
        document.querySelector('.system-status-indicator').addEventListener('click', () => {
            this.showSystemDetails();
        });

        // Brand header
        document.querySelector('.brand-header').addEventListener('click', () => {
            this.showBrandDetails();
        });

        // Cycle port button
        document.querySelector('.btn-cycle-port').addEventListener('click', () => {
            this.cycleNextPort();
        });
    }

    updateAllStatistics() {
        this.updateLivePorts();
        this.updateActiveUsers();
        this.updateResponseTime();
        this.updateLiveCalculations();
        this.updateSystemUptime();
        this.updateNavigationProgress();
    }

    updateLivePorts() {
        const portsElement = document.getElementById('livePortsCount');
        if (portsElement) {
            const base = 18;
            const variation = Math.floor(Math.random() * 3);
            portsElement.textContent = (base + variation).toString();
        }
    }

    updateActiveUsers() {
        const usersElement = document.getElementById('activeUsers');
        if (usersElement) {
            const base = 42;
            const variation = Math.floor(Math.random() * 5);
            const current = parseInt(usersElement.textContent) || base;
            const newValue = Math.max(base, current + (Math.random() > 0.5 ? 1 : -1));
            usersElement.textContent = newValue.toString();
            
            // Update change indicator
            const changeElement = document.getElementById('usersChange');
            if (changeElement) {
                const change = newValue - current;
                changeElement.textContent = change >= 0 ? `+${change}` : `${change}`;
                changeElement.style.color = change >= 0 ? '#10b981' : '#ef4444';
            }
        }
    }

    updateResponseTime() {
        const responseElement = document.getElementById('responseTime');
        if (responseElement) {
            const base = 35;
            const variation = Math.floor(Math.random() * 25);
            const newValue = base + variation;
            responseElement.textContent = `${newValue}ms`;
            
            // Update change indicator
            const changeElement = document.getElementById('responseChange');
            if (changeElement) {
                const current = parseInt(responseElement.textContent) || 42;
                const change = newValue - current;
                changeElement.textContent = change >= 0 ? `+${change}ms` : `${change}ms`;
                changeElement.style.color = change <= 0 ? '#10b981' : '#ef4444';
            }
        }
    }

    updateLiveCalculations() {
        const calculationsElement = document.getElementById('liveCalculations');
        if (calculationsElement) {
            const base = 18;
            const variation = Math.floor(Math.random() * 3);
            const newValue = base + variation;
            calculationsElement.textContent = newValue.toString();
            
            // Update change indicator
            const changeElement = document.getElementById('calcChange');
            if (changeElement) {
                const current = parseInt(calculationsElement.textContent) || 18;
                const change = newValue - current;
                changeElement.textContent = change >= 0 ? `+${change}` : `${change}`;
                changeElement.style.color = change >= 0 ? '#10b981' : '#ef4444';
            }
        }
    }

    updateSystemUptime() {
        const uptimeElement = document.getElementById('systemUptimeDisplay');
        if (uptimeElement) {
            uptimeElement.textContent = '99.7% uptime';
        }
    }

    updateCopyrightYear() {
        const yearElement = document.querySelector('.copyright-year');
        if (yearElement) {
            yearElement.textContent = new Date().getFullYear();
        }
    }

    updateRealTimeClock() {
        const updateClock = () => {
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', {
                hour12: true,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            const clockElement = document.getElementById('currentTime');
            if (clockElement) {
                clockElement.textContent = timeString;
            }
        };

        updateClock();
        setInterval(updateClock, 1000);
    }

    updateNavigationProgress() {
        const visitedCards = document.querySelectorAll('.nav-card[data-visited="true"]');
        const totalCards = document.querySelectorAll('.nav-card').length;
        const progress = (visitedCards.length / totalCards) * 100;
        
        const progressElement = document.getElementById('navProgress');
        const progressFill = document.getElementById('navProgressFill');
        
        if (progressElement) {
            progressElement.textContent = `${visitedCards.length}/${totalCards}`;
        }
        
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }
    }

    // Event Handlers
    markNavAsVisited(card) {
        card.setAttribute('data-visited', 'true');
        this.updateNavigationProgress();
    }
toggleTechCategory(category) {
    // Toggle the open class
    category.classList.toggle('open');
    
    // Get the content and toggle elements
    const content = category.querySelector('.tech-tags');
    const toggle = category.querySelector('.category-toggle');
    
    // Check if the category is now open
    if (category.classList.contains('open')) {
        // Show content and change toggle to up arrow
        content.style.display = 'flex';
        toggle.textContent = '▲';
    } else {
        // Hide content and change toggle to down arrow
        content.style.display = 'none';
        toggle.textContent = '▼';
    }
}

    openLiveChat() {
        this.showToast('Opening live chat...', 'info');
        // In a real app, this would open a chat widget
        setTimeout(() => {
            this.showToast('Live chat is ready!', 'success');
        }, 1000);
    }

    scheduleCall() {
        this.showToast('Opening calendar for demo scheduling...', 'info');
        // In a real app, this would open a calendar booking system
    }

    scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    showSystemDetails() {
        const modalHTML = `
            <div class="system-details-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🚢 System Status Details</h3>
                        <button class="modal-close">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="detail-item">
                            <span class="detail-label">Overall Status:</span>
                            <span class="detail-value status-good">Operational</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Uptime (30d):</span>
                            <span class="detail-value">99.7%</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Server Load:</span>
                            <span class="detail-value">24%</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Memory Usage:</span>
                            <span class="detail-value">1.2 GB</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Active Connections:</span>
                            <span class="detail-value">${document.getElementById('activeUsers')?.textContent || '42'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Last Incident:</span>
                            <span class="detail-value">None (60+ days)</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        const existingModal = document.querySelector('.system-details-modal');
        if (existingModal) existingModal.remove();
        
        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Add close functionality
        const modal = document.querySelector('.system-details-modal');
        modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

 // Replace the existing showBrandDetails method with this:
showBrandDetails() {
    const brandHeader = document.querySelector('.brand-header');
    const brandExpand = brandHeader.querySelector('.brand-expand');
    
    // Toggle expansion state
    brandHeader.classList.toggle('expanded');
    
    if (brandHeader.classList.contains('expanded')) {
        brandExpand.textContent = '▼';
        this.showToast('Brand details expanded', 'info');
        
        // Create and show brand details modal
        const modalHTML = `
            <div class="brand-details-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🚢 MaritimeRoute Pro - Brand Story</h3>
                        <button class="modal-close">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="brand-story">
                            <p><strong>MaritimeRoute Pro</strong> is an advanced AI-powered maritime optimization platform that combines:</p>
                            <ul>
                                <li>📊 <strong>A* Algorithm</strong> for shortest path finding</li>
                                <li>🧬 <strong>Genetic Algorithm</strong> for multi-objective optimization</li>
                                <li>🌤️ <strong>Real-time weather integration</strong> from Storm Glass API</li>
                                <li>⚓ <strong>Global port database</strong> with 1,800+ ports</li>
                            </ul>
                            <p>Our mission: <em>"Optimizing global maritime logistics through intelligent algorithms and real-time data analysis."</em></p>
                        </div>
                        <div class="brand-stats">
                            <div class="brand-stat">
                                <span class="stat-label">Founded:</span>
                                <span class="stat-value">2023</span>
                            </div>
                            <div class="brand-stat">
                                <span class="stat-label">Routes Optimized:</span>
                                <span class="stat-value">1,247+</span>
                            </div>
                            <div class="brand-stat">
                                <span class="stat-label">Fuel Saved:</span>
                                <span class="stat-value">45.2 tonnes</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        const existingModal = document.querySelector('.brand-details-modal');
        if (existingModal) existingModal.remove();
        
        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Add close functionality
        const modal = document.querySelector('.brand-details-modal');
        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.remove();
            brandHeader.classList.remove('expanded');
            brandExpand.textContent = '▶';
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                brandHeader.classList.remove('expanded');
                brandExpand.textContent = '▶';
            }
        });
    } else {
        brandExpand.textContent = '▶';
        const modal = document.querySelector('.brand-details-modal');
        if (modal) modal.remove();
    }
}

    cycleNextPort() {
        const ports = ['Singapore', 'Shanghai', 'Jebel_Ali', 'Busan', 'Melbourne', 'Rotterdam'];
        const currentElement = document.querySelector('.featured-port');
        const currentText = currentElement.textContent.replace('Featured Port: ', '').replace(' ⚓', '');
        const currentIndex = ports.indexOf(currentText);
        const nextIndex = (currentIndex + 1) % ports.length;
        
        currentElement.innerHTML = `Featured Port: ${ports[nextIndex]} ⚓`;
        this.showToast(`Featured port changed to ${ports[nextIndex]}`, 'info');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `footer-toast toast-${type}`;
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        toast.innerHTML = `${icons[type] || icons.info} ${message}`;
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove after delay
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    startLiveUpdates() {
        // Update stats every 10 seconds
        setInterval(() => this.updateAllStatistics(), 10000);
        
        // Randomly update some metrics
        setInterval(() => {
            // Randomly update routes calculated
            if (Math.random() > 0.7) {
                const routesElement = document.getElementById('footerRoutesCalculated');
                if (routesElement) {
                    const current = parseInt(routesElement.textContent.replace(/,/g, '')) || 1247;
                    routesElement.textContent = (current + 1).toLocaleString();
                }
            }
            
            // Randomly update fuel saved
            if (Math.random() > 0.8) {
                const fuelElement = document.getElementById('footerFuelSaved');
                if (fuelElement) {
                    const current = parseFloat(fuelElement.textContent) || 45.2;
                    fuelElement.textContent = (current + 0.1).toFixed(1) + 't';
                }
            }
        }, 15000);
    }

    // Legal modals
    showLegalModal(type) {
        const titles = {
            privacy: 'Privacy Policy',
            terms: 'Terms of Service',
            cookies: 'Cookie Policy',
            gdpr: 'GDPR Compliance'
        };
        
        this.showToast(`${titles[type]} modal would open here`, 'info');
    }

    showAccessibility() {
        this.showToast('Accessibility features dialog would open here', 'info');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Give it a small delay to ensure all elements are loaded
    setTimeout(() => {
        window.footerManager = new FooterManager();
        console.log('Footer manager initialized');
    }, 500);
});
// Update navigation progress and indicators
function updateNavigationProgress() {
    const navCards = document.querySelectorAll('.nav-card');
    let visitedCount = 0;
    
    navCards.forEach(card => {
        const isVisited = card.getAttribute('data-visited') === 'true';
        if (isVisited) {
            visitedCount++;
            // Add glow effect to visited cards
            card.classList.add('visited-glow');
        }
    });
    
    // Update progress text
    const progressText = document.getElementById('navProgress');
    if (progressText) {
        progressText.textContent = `${visitedCount}/${navCards.length}`;
    }
    
    // Update progress bar
    const progressFill = document.getElementById('navProgressFill');
    if (progressFill) {
        const percentage = (visitedCount / navCards.length) * 100;
        progressFill.style.width = `${percentage}%`;
    }
}
// When the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get all category headers
    const categoryHeaders = document.querySelectorAll('.category-header');
    
    // Add click event to each header
    categoryHeaders.forEach(header => {
        header.addEventListener('click', function() {
            // Get the parent tech-category element
            const category = this.closest('.tech-category');
            // Call the toggle function
            toggleTechCategory(category);
        });
    });
});
function toggleTechCategory(category) {
    // Toggle the open class
    category.classList.toggle('open');
    
    // Get the content and toggle elements
    const content = category.querySelector('.tech-tags');
    const toggle = category.querySelector('.category-toggle');
    
    // Check if the category is now open
    if (category.classList.contains('open')) {
        // Show content and change toggle to up arrow
        content.style.display = 'flex';
        toggle.textContent = '▲';
    } else {
        // Hide content and change toggle to down arrow
        content.style.display = 'none';
        toggle.textContent = '▼';
    }
}
// Mark navigation items as visited when clicked
document.addEventListener('DOMContentLoaded', function() {
    const navCards = document.querySelectorAll('.nav-card');
    
    navCards.forEach(card => {
        card.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Mark this card as visited
            this.setAttribute('data-visited', 'true');
            
            // Update all progress indicators
            updateNavigationProgress();
            
            // Call the original onclick handler
            const onclick = this.getAttribute('onclick');
            if (onclick) {
                eval(onclick);
            }
        });
    });
    
    // Initialize progress display
    updateNavigationProgress();
});

// Live metrics update function
function updateLiveMetrics() {
    // Update active users with random fluctuation
    const usersElement = document.getElementById('activeUsers');
    if (usersElement) {
        const currentUsers = parseInt(usersElement.textContent) || 49;
        const change = Math.floor(Math.random() * 5) - 2; // -2 to +2
        const newUsers = Math.max(1, currentUsers + change);
        usersElement.textContent = newUsers;
        
        // Update change indicator
        const changeElement = document.getElementById('usersChange');
        if (changeElement) {
            changeElement.textContent = change >= 0 ? `+${change}` : `${change}`;
            changeElement.className = change >= 0 ? 'metric-change' : 'metric-change negative';
        }
    }
    
    // Update live calculations
    const calcElement = document.getElementById('liveCalculations');
    if (calcElement) {
        const currentCalc = parseInt(calcElement.textContent) || 18;
        const change = Math.floor(Math.random() * 3); // 0 to 2
        calcElement.textContent = currentCalc + change;
    }
    
    // Update response time
    const responseElement = document.getElementById('responseTime');
    if (responseElement) {
        const currentTime = parseInt(responseElement.textContent) || 54;
        const change = Math.floor(Math.random() * 20) - 10; // -10 to +10
        const newTime = Math.max(20, currentTime + change);
        responseElement.textContent = `${newTime}ms`;
    }
}

// Update metrics every 10 seconds
setInterval(updateLiveMetrics, 10000);
// ===== PROFESSIONAL NOTIFICATION SYSTEM =====

class NotificationManager {
    constructor() {
        this.container = null;
        this.initialize();
    }

    initialize() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notificationContainer')) {
            this.container = document.createElement('div');
            this.container.id = 'notificationContainer';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('notificationContainer');
        }
    }

    // Show a notification
    show(options) {
        const {
            type = 'info',
            title = 'Notification',
            message = '',
            duration = 5000,
            actions = [],
            showProgress = true,
            canClose = true,
            onClose = null,
            onAction = null
        } = options;

        // Create notification card
        const card = document.createElement('div');
        card.className = `notification-card ${type}`;
        
        // Get icon based on type
        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌'
        };

        // Build notification HTML
        card.innerHTML = `
            <div class="notification-header">
                <div class="notification-title">
                    <span class="notification-icon">${icons[type]}</span>
                    <span>${title}</span>
                </div>
                ${canClose ? '<button class="notification-close">&times;</button>' : ''}
            </div>
            <div class="notification-body">
                ${typeof message === 'string' ? `<p>${message}</p>` : message}
            </div>
            ${actions.length > 0 ? `
                <div class="notification-actions">
                    ${actions.map(action => `
                        <button class="notification-btn ${action.type || 'secondary'}" 
                                data-action="${action.id}">
                            ${action.icon ? `<span>${action.icon}</span>` : ''}
                            ${action.label}
                        </button>
                    `).join('')}
                </div>
            ` : ''}
            ${showProgress ? `
                <div class="notification-progress">
                    <div class="notification-progress-bar"></div>
                </div>
            ` : ''}
        `;

        // Add to container
        this.container.appendChild(card);

        // Setup close functionality
        if (canClose) {
            const closeBtn = card.querySelector('.notification-close');
            closeBtn.addEventListener('click', () => this.close(card, onClose));
        }

        // Setup action buttons
        if (actions.length > 0) {
            const actionBtns = card.querySelectorAll('.notification-btn');
            actionBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    if (onAction) {
                        onAction(btn.dataset.action);
                    }
                    this.close(card, onClose);
                });
            });
        }

        // Auto-dismiss if duration is set
        if (duration > 0) {
            if (showProgress) {
                const progressBar = card.querySelector('.notification-progress-bar');
                let startTime = Date.now();
                
                const updateProgress = () => {
                    const elapsed = Date.now() - startTime;
                    const percent = Math.min((elapsed / duration) * 100, 100);
                    progressBar.style.width = `${percent}%`;
                    
                    if (percent < 100) {
                        requestAnimationFrame(updateProgress);
                    } else {
                        this.close(card, onClose);
                    }
                };
                
                updateProgress();
            } else {
                setTimeout(() => this.close(card, onClose), duration);
            }
        }

        return card;
    }

    // Close notification
    close(card, callback) {
        if (!card || !card.parentNode) return;
        
        card.classList.add('closing');
        
        setTimeout(() => {
            if (card.parentNode) {
                card.parentNode.removeChild(card);
            }
            if (callback) callback();
        }, 300);
    }

    // Alert replacement
    alert(message, title = 'Alert') {
        return this.show({
            type: 'info',
            title: title,
            message: message,
            duration: 5000,
            canClose: true
        });
    }

    // Confirm replacement
    confirm(message, title = 'Confirm') {
        return new Promise((resolve) => {
            const card = this.show({
                type: 'warning',
                title: title,
                message: message,
                duration: 0,
                canClose: false,
                actions: [
                    {
                        id: 'confirm',
                        label: 'Confirm',
                        type: 'primary',
                        icon: '✓'
                    },
                    {
                        id: 'cancel',
                        label: 'Cancel',
                        type: 'secondary',
                        icon: '✕'
                    }
                ],
                onAction: (action) => {
                    resolve(action === 'confirm');
                }
            });
        });
    }

    // Prompt replacement
    prompt(message, defaultValue = '', title = 'Input') {
        return new Promise((resolve) => {
            const card = document.createElement('div');
            card.className = 'notification-card info';
            
            card.innerHTML = `
                <div class="notification-header">
                    <div class="notification-title">
                        <span class="notification-icon">✏️</span>
                        <span>${title}</span>
                    </div>
                    <button class="notification-close">&times;</button>
                </div>
                <div class="notification-body">
                    <p>${message}</p>
                    <input type="text" class="notification-input" value="${defaultValue}" placeholder="Enter value...">
                </div>
                <div class="notification-actions">
                    <button class="notification-btn primary" data-action="submit">
                        <span>✓</span> Submit
                    </button>
                    <button class="notification-btn secondary" data-action="cancel">
                        <span>✕</span> Cancel
                    </button>
                </div>
            `;

            this.container.appendChild(card);

            const input = card.querySelector('.notification-input');
            input.focus();
            input.select();

            const closeBtn = card.querySelector('.notification-close');
            const submitBtn = card.querySelector('[data-action="submit"]');
            const cancelBtn = card.querySelector('[data-action="cancel"]');

            const close = (value) => {
                this.close(card);
                resolve(value);
            };

            closeBtn.addEventListener('click', () => close(null));
            cancelBtn.addEventListener('click', () => close(null));
            
            submitBtn.addEventListener('click', () => close(input.value));
            
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    close(input.value);
                }
            });
        });
    }

    // Success notification
    success(message, title = 'Success!') {
        return this.show({
            type: 'success',
            title: title,
            message: message,
            duration: 3000
        });
    }

    // Error notification
    error(message, title = 'Error!') {
        return this.show({
            type: 'error',
            title: title,
            message: message,
            duration: 7000
        });
    }

    // Warning notification
    warning(message, title = 'Warning!') {
        return this.show({
            type: 'warning',
            title: title,
            message: message,
            duration: 5000
        });
    }

    // Toast notification (smaller)
    toast(message, type = 'info') {
        return this.show({
            type: type,
            title: '',
            message: message,
            duration: 3000,
            showProgress: false
        });
    }
}

// Initialize notification manager globally
window.notify = new NotificationManager();

// Override default alert/confirm/prompt
window.alert = (message, title) => notify.alert(message, title);
window.confirm = (message, title) => notify.confirm(message, title);
window.prompt = (message, defaultValue, title) => notify.prompt(message, defaultValue, title);
// Call this function whenever something changes
function setupHeightManagement() {
  // Monitor form changes
  document
    .getElementById("hubPorts")
    .addEventListener("change", updateDashboardHeight);
  document.querySelectorAll('input[name="weather"]').forEach((radio) => {
    radio.addEventListener("change", updateDashboardHeight);
  });

  // Monitor calculate button
  document
    .getElementById("calculateBtn")
    .addEventListener("click", function () {
      setTimeout(updateDashboardHeight, 100);
    });

  // Monitor loading state
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.attributeName === "style") {
      }
    });
  });

  const loadingOverlay = document.getElementById("loadingOverlay");
  if (loadingOverlay) {
    observer.observe(loadingOverlay, { attributes: true });
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  setupHeightManagement();
});

//Just upodated


// Add this function to display algorithm statistics
function displayAlgorithmStats(data) {
  const algorithmStats = document.getElementById("algorithmStats");
  if (!algorithmStats) return;

  const stats = data.algorithm_stats || {
    total_calculations: 0,
    average_calculation_time: 0,
    fastest_algorithm: "A*",
    routes_calculated: 0,
  };

  algorithmStats.innerHTML = `
        <div class="algorithm-stat">
            <strong>Total Calculations:</strong> ${
              stats.total_calculations || 0
            }
        </div>
        <div class="algorithm-stat">
            <strong>Avg. Calculation Time:</strong> ${(
              stats.average_calculation_time || 0
            ).toFixed(2)}s
        </div>
        <div class="algorithm-stat">
            <strong>Fastest Algorithm:</strong> ${
              stats.fastest_algorithm || "A*"
            }
        </div>
        <div class="algorithm-stat">
            <strong>Routes Calculated:</strong> ${stats.routes_calculated || 0}
        </div>
    `;
}
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the footer manager
    if (window.footerManager) {
        window.footerManager.setupEventListeners();
    } else {
        window.footerManager = new FooterManager();
    }
    
    // Also add event listeners for tech categories directly
    document.querySelectorAll('.tech-category').forEach(category => {
        const header = category.querySelector('.category-header');
        if (header) {
            header.addEventListener('click', () => toggleTechCategory(category));
        }
    });
});
// Call this after page loads and when window resizes
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(fixLegendPosition, 100);
});

window.addEventListener("resize", fixLegendPosition);

// Make functions globally available
window.toggleRoute = toggleRoute;
window.toggleAllRoutes = toggleAllRoutes;
window.zoomToRoutes = zoomToRoutes;
window.toggleLegend = toggleLegend;
window.toggleFullscreen = toggleFullscreen;
window.clearForm = clearForm;
window.removePortFromSelection = removePortFromSelection;
window.clearSelectedPorts = clearSelectedPorts;
window.navLoadSection = navLoadSection;
window.navToggleProfileMenu = navToggleProfileMenu;
window.navToggleMobileMenu = navToggleMobileMenu;
window.navShowNotifications = navShowNotifications;
window.navOpenSettings = navOpenSettings;
window.navLogout = navLogout;
window.backToPlanner = backToPlanner;
