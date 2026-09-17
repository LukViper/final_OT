// Configuration
const CONFIG = {
  AVERAGE_SPEED_KMH: 37.0,
  FUEL_CONSUMPTION_PER_KM: 0.04,
  WEATHER_FACTOR: 1.25,
  EMISSION_FACTOR: 3.114,
};

// Navigation Configuration
const NAV_CONFIG = {
  sections: {
    planner: { name: "Route Planner", icon: "🗺️", visible: true },
    analytics: { name: "Analytics", icon: "📊", visible: true },
    ports: { name: "Port Database", icon: "⚓", visible: true },
    tools: { name: "Tools", icon: "🔧", visible: true, submenu: {
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
let routeLayers = { fastest: null, fuel: null, direct: null };
let portMarkers = [];
let currentMapData = null;

// ========== INITIALIZATION ==========
document.addEventListener("DOMContentLoaded", function () {
  console.log("📱 Initializing MaritimeRoute Pro...");

  currentMapData = null;
  routeLayers = { fastest: null, fuel: null, direct: null };
  portMarkers = [];

  initializeMap();
  setupEventListeners();

  const legend = document.getElementById("mapLegend");
  if (legend) legend.style.display = "block";

  resetStatistics();

  // Set default datetime to now
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  
  const departureTimeInput = document.getElementById("departureTime");
  if (departureTimeInput) {
    departureTimeInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
  }

  // Initialize advanced params as hidden
  document.querySelectorAll('.advanced-param').forEach(param => {
    param.style.display = 'none';
  });

  setTimeout(() => {
    refreshMapWithNewData();
    map.setView([20, 0], 2);
  }, 100);
  
  setTimeout(() => {
    updateDashboardHeight();
  }, 100);
});

// ========== MAP FUNCTIONS ==========
function initializeMap() {
  console.log("🗺️ Initializing fresh map...");

  const mapContainer = document.getElementById("map");
  if (mapContainer && mapContainer._leaflet_id) {
    mapContainer._leaflet_id = null;
  }

  map = L.map("map", {
    zoomControl: true,
    attributionControl: true,
    preferCanvas: true,
  }).setView([20, 0], 2);

  map.eachLayer((layer) => {
    if (!(layer instanceof L.TileLayer)) {
      map.removeLayer(layer);
    }
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(map);

  L.tileLayer("https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png", {
    attribution: "© OpenSeaMap contributors",
    maxZoom: 18,
    opacity: 0.7,
  }).addTo(map);

  setTimeout(() => {
    L.popup()
      .setLatLng([20, 0])
      .setContent(`
        <div style="text-align: center; padding: 10px;">
            <h3>🚢 MaritimeRoute Pro</h3>
            <p>Select ports and click "Calculate" to see routes.</p>
            <p><strong>Holtrop-Mennen, 4D Weather, Biofouling, Ocean Currents</strong></p>
        </div>
      `)
      .openOn(map);
  }, 500);

  console.log("✅ Map initialized");
}

function refreshMapWithNewData() {
  if (!map) return;

  map.eachLayer((layer) => {
    if (!(layer instanceof L.TileLayer)) {
      map.removeLayer(layer);
    }
  });

  routeLayers = { fastest: null, fuel: null, direct: null };
  portMarkers = [];

  if (window.weatherMarkers) window.weatherMarkers = [];
  if (window.currentRouteLayers) window.currentRouteLayers = [];

  currentMapData = null;
  console.log("✅ Map cleared");
}

function displayRoutesOnMap(data) {
  console.log("🗺️ Displaying routes on map...");

  // Clear existing layers
  if (window.currentRouteLayers) {
    window.currentRouteLayers.forEach((layer) => {
      if (layer && map && map.hasLayer(layer)) map.removeLayer(layer);
    });
    window.currentRouteLayers = [];
  }

  Object.keys(routeLayers).forEach((key) => {
    if (routeLayers[key]) {
      if (Array.isArray(routeLayers[key])) {
        routeLayers[key].forEach((layer) => {
          if (layer && map && map.hasLayer(layer)) map.removeLayer(layer);
        });
      } else if (routeLayers[key] instanceof L.LayerGroup) {
        routeLayers[key].clearLayers();
        if (map && map.hasLayer(routeLayers[key])) map.removeLayer(routeLayers[key]);
      } else if (routeLayers[key] && map && map.hasLayer(routeLayers[key])) {
        map.removeLayer(routeLayers[key]);
      }
      routeLayers[key] = null;
    }
  });

  portMarkers.forEach((marker) => {
    if (marker && marker.remove && map) map.removeLayer(marker);
  });
  portMarkers = [];

  if (window.weatherMarkers) {
    window.weatherMarkers.forEach((marker) => {
      if (marker && marker.remove && map) map.removeLayer(marker);
    });
    window.weatherMarkers = [];
  }

  if (!window.currentRouteLayers) window.currentRouteLayers = [];

  if (!data) {
    console.warn("⚠️ No data provided");
    return;
  }

  const fastestRoute = data.fastest_route || {};
  const fuelRoute = data.fuel_efficient_route || {};
  const directRoute = data.direct_route || {};

  const fastestPorts = fastestRoute.ports || [];
  const fuelPorts = fuelRoute.ports || [];

  if (!fastestRoute.coordinates && !fuelRoute.coordinates) {
    console.warn("⚠️ No route coordinates");
    return;
  }

  // Draw fastest route
  if (fastestRoute.coordinates && fastestRoute.coordinates.length > 1) {
    const polyline = L.polyline(fastestRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.fastest.color,
      weight: 5,
      opacity: 0.8,
      lineCap: "round",
      lineJoin: "round",
    }).addTo(map);

    const glowLine = L.polyline(fastestRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.fastest.color,
      weight: 8,
      opacity: 0.2,
      lineCap: "round",
      lineJoin: "round",
    }).addTo(map);

    routeLayers.fastest = L.layerGroup([glowLine, polyline]);
    window.currentRouteLayers.push(routeLayers.fastest);

    polyline.bindPopup(`
      <div style="text-align: center; min-width: 200px;">
        <h4 style="color: ${NAV_CONFIG.routeTypes.fastest.color}; margin: 0 0 10px 0; font-size: 16px;">🚀 Fastest Route (A*)</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div><strong>Distance:</strong><br>${safeNumberFormat(fastestRoute.distance_km)} km</div>
          <div><strong>Time:</strong><br>${safeNumberFormat(fastestRoute.time_hours / 24, 1)} days</div>
          <div><strong>Fuel:</strong><br>${safeNumberFormat(fastestRoute.fuel_tonnes, 1)} t</div>
          <div><strong>Cost:</strong><br>$${((fastestRoute.fuel_tonnes || 0) * 650).toLocaleString()}</div>
        </div>
      </div>
    `);
  }

  // Draw fuel-efficient route
  if (fuelRoute.coordinates && fuelRoute.coordinates.length > 1) {
    const polyline = L.polyline(fuelRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.efficient.color,
      weight: 5,
      opacity: 0.8,
      lineCap: "round",
      lineJoin: "round",
    }).addTo(map);

    const glowLine = L.polyline(fuelRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.efficient.color,
      weight: 8,
      opacity: 0.2,
      lineCap: "round",
      lineJoin: "round",
    }).addTo(map);

    routeLayers.fuel = L.layerGroup([glowLine, polyline]);
    window.currentRouteLayers.push(routeLayers.fuel);

    polyline.bindPopup(`
      <div style="text-align: center; min-width: 200px;">
        <h4 style="color: ${NAV_CONFIG.routeTypes.efficient.color}; margin: 0 0 10px 0; font-size: 16px;">🌿 Fuel-Efficient Route (Genetic)</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div><strong>Distance:</strong><br>${safeNumberFormat(fuelRoute.distance_km)} km</div>
          <div><strong>Time:</strong><br>${safeNumberFormat(fuelRoute.time_hours / 24, 1)} days</div>
          <div><strong>Fuel:</strong><br>${safeNumberFormat(fuelRoute.fuel_tonnes, 1)} t</div>
          <div><strong>Cost:</strong><br>$${((fuelRoute.fuel_tonnes || 0) * 650).toLocaleString()}</div>
        </div>
      </div>
    `);
  }

  // Draw direct route
  if (directRoute.coordinates && directRoute.coordinates.length > 1) {
    const polyline = L.polyline(directRoute.coordinates, {
      color: NAV_CONFIG.routeTypes.direct.color,
      weight: 2,
      opacity: 0.4,
      dashArray: "8, 8",
    }).addTo(map);

    routeLayers.direct = polyline;
    window.currentRouteLayers.push(polyline);

    polyline.bindPopup(`
      <div style="text-align: center;">
        <h4 style="color: ${NAV_CONFIG.routeTypes.direct.color};">📐 Great Circle Reference</h4>
      </div>
    `);
  }

  // Add port markers
  if (data.port_locations) {
    addPortMarkers(data.port_locations, fastestPorts, fuelPorts);
  }

  // Add weather markers
  addWeatherMarkers(data);

  zoomToRoutes();
  updateLegend(fastestPorts, fuelPorts);
}

function addPortMarkers(portLocations, fastestPorts, fuelPorts) {
  Object.entries(portLocations).forEach(([port, coords]) => {
    let color = "#94a3b8";
    let iconHtml = "⚓";
    let size = 28;

    if (port === fastestPorts[0]) {
      color = "#27ae60";
      iconHtml = "🟢";
      size = 32;
    } else if (port === fastestPorts[fastestPorts.length - 1]) {
      color = "#e74c3c";
      iconHtml = "🔴";
      size = 32;
    } else if (fastestPorts.includes(port) && fuelPorts.includes(port)) {
      color = "#9b59b6";
      iconHtml = "🟣";
    } else if (fastestPorts.includes(port)) {
      color = "#ff6b35";
      iconHtml = "🟠";
    } else if (fuelPorts.includes(port)) {
      color = "#2ecc71";
      iconHtml = "🟢";
    }

    const customIcon = L.divIcon({
      html: `<div style="background-color: ${color}; width: ${size}px; height: ${size}px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: ${size-8}px; border: 3px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">${iconHtml}</div>`,
      className: "custom-port-icon",
      iconSize: [size, size],
      iconAnchor: [size/2, size/2],
    });

    const marker = L.marker(coords, { icon: customIcon })
      .bindPopup(`
        <div style="text-align: center;">
          <h4 style="margin: 0 0 5px 0; color: ${color};">${port}</h4>
          <p style="margin: 2px 0;">Lat: ${coords[0].toFixed(4)}°</p>
          <p style="margin: 2px 0;">Lon: ${coords[1].toFixed(4)}°</p>
        </div>
      `)
      .addTo(map);

    portMarkers.push(marker);
  });
}

function updateLegend(fastestPorts, fuelPorts) {
  const legendContent = document.querySelector(".legend-content");
  if (!legendContent) return;

  const hubPortsSelect = document.getElementById("hubPorts");
  const selectedHubs = Array.from(hubPortsSelect.selectedOptions)
    .map((opt) => opt.value)
    .filter((port) => port !== "");

  legendContent.innerHTML = `
    <div class="legend-item"><span class="color-swatch" style="background-color: #27ae60;"></span><span>Start Port</span></div>
    <div class="legend-item"><span class="color-swatch" style="background-color: #e74c3c;"></span><span>Destination Port</span></div>
    <div class="legend-item"><span class="color-swatch" style="background-color: ${NAV_CONFIG.routeTypes.fastest.color};"></span><span>Fastest Route (A*)</span></div>
    <div class="legend-item"><span class="color-swatch" style="background-color: ${NAV_CONFIG.routeTypes.efficient.color};"></span><span>Fuel-Efficient Route (Genetic)</span></div>
    <div class="legend-item"><span class="color-swatch" style="background-color: ${NAV_CONFIG.routeTypes.direct.color}; opacity: 0.4;"></span><span>Great Circle Reference</span></div>
    ${selectedHubs.length > 0 ? `<div class="legend-item"><span class="color-swatch" style="background-color: #9b59b6;"></span><span>Intermediate Ports</span></div>` : ""}
  `;
}

function zoomToRoutes() {
  if (!currentMapData) return;

  const allCoords = [];

  if (currentMapData.fastest_route?.coordinates) allCoords.push(...currentMapData.fastest_route.coordinates);
  if (currentMapData.fuel_efficient_route?.coordinates) allCoords.push(...currentMapData.fuel_efficient_route.coordinates);
  if (currentMapData.direct_route?.coordinates) allCoords.push(...currentMapData.direct_route.coordinates);
  if (currentMapData.port_locations) Object.values(currentMapData.port_locations).forEach(coords => allCoords.push(coords));

  if (allCoords.length > 0) {
    map.fitBounds(L.latLngBounds(allCoords), { padding: [50, 50] });
  }
}

function toggleRoute(routeType) {
  const layer = routeLayers[routeType];
  if (layer) {
    if (map.hasLayer(layer)) map.removeLayer(layer);
    else layer.addTo(map);
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
    mapContainer.requestFullscreen().catch(err => console.log(err));
  } else {
    document.exitFullscreen();
  }
}
function toggleAdvancedParams() {
    const advancedParams = document.querySelectorAll('.advanced-param');
    const btn = document.querySelector('.btn-advanced');
    
    if (!btn) return;
    
    advancedParams.forEach(param => {
        if (param.style.display === 'none' || param.style.display === '') {
            param.style.display = 'block';
            btn.innerHTML = '<span>🔬 Basic</span>';
        } else {
            param.style.display = 'none';
            btn.innerHTML = '<span>🔬 Advanced</span>';
        }
    });
}

// Make sure the button exists and has the correct event listener
document.addEventListener('DOMContentLoaded', function() {
    const advancedBtn = document.querySelector('.btn-advanced');
    if (advancedBtn) {
        // Remove any existing listeners and add new one
        advancedBtn.replaceWith(advancedBtn.cloneNode(true));
        document.querySelector('.btn-advanced').addEventListener('click', toggleAdvancedParams);
    }
});


function updateSelectedPortsDisplay() {
  const hubPortsSelect = document.getElementById("hubPorts");
  const selectedPortsContainer = document.getElementById("selectedPorts");
  const selectedPortsList = document.getElementById("selectedPortsList");

  const selectedOptions = Array.from(hubPortsSelect.selectedOptions);
  const selectedPorts = selectedOptions.map(opt => opt.value).filter(port => port !== "");

  if (selectedPorts.length > 0) {
    selectedPortsContainer.style.display = "block";
    selectedPortsList.innerHTML = "";
    selectedPorts.forEach((port) => {
      const portTag = document.createElement("div");
      portTag.className = "port-tag selected";
      portTag.innerHTML = `${port} <button type="button" class="port-tag-remove" onclick="removePortFromSelection('${port}')">×</button>`;
      selectedPortsList.appendChild(portTag);
    });
  } else {
    selectedPortsContainer.style.display = "none";
  }
}

function removePortFromSelection(port) {
  const hubPortsSelect = document.getElementById("hubPorts");
  const option = Array.from(hubPortsSelect.options).find(opt => opt.value === port);
  if (option) {
    option.selected = false;
    updateSelectedPortsDisplay();
  }
}

function clearSelectedPorts() {
  const hubPortsSelect = document.getElementById("hubPorts");
  Array.from(hubPortsSelect.options).forEach(option => option.selected = false);
  updateSelectedPortsDisplay();
}

// Update vessel parameters when vessel type changes
document.addEventListener('DOMContentLoaded', function() {
  const vesselTypeSelect = document.getElementById('vesselType');
  if (vesselTypeSelect) {
    vesselTypeSelect.addEventListener('change', function() {
      const selected = this.options[this.selectedIndex];
      const lwl = selected.dataset.lwl || '280';
      const cb = selected.dataset.cb || '0.65';
      
      const vesselLWLEl = document.getElementById('vesselLWL');
      const vesselCbEl = document.getElementById('vesselCb');
      const vesselDispEl = document.getElementById('vesselDisp');
      
      if (vesselLWLEl) vesselLWLEl.textContent = lwl + ' m';
      if (vesselCbEl) vesselCbEl.textContent = cb;
      
      let disp = '80,000';
      if (this.value === 'ULCC_Tanker') disp = '520,000';
      else if (this.value === 'Bulker') disp = '45,000';
      if (vesselDispEl) vesselDispEl.textContent = disp + ' m³';
    });
  }

  const ensembleSize = document.getElementById('ensembleSize');
  const ensembleValue = document.getElementById('ensembleValue');
  if (ensembleSize && ensembleValue) {
    ensembleSize.addEventListener('input', function() {
      ensembleValue.textContent = this.value;
    });
  }
});

// In script.js - Replace the calculateRoutes function with this fixed version
async function calculateRoutes() {
  // Get all form values
  const startPort = document.getElementById("startPort").value;
  const destinationPort = document.getElementById("destinationPort").value;
  const hubPortsSelect = document.getElementById("hubPorts");
  const hubPorts = Array.from(hubPortsSelect.selectedOptions)
    .map(opt => opt.value)
    .filter(port => port !== "");
  
  // DEFINE optimizationGoal HERE - make it available in this scope
  const goalRadio = document.querySelector('input[name="goal"]:checked');
  const optimizationGoal = goalRadio ? goalRadio.value : "both";
  
  const weatherRadio = document.querySelector('input[name="weather"]:checked');
  const includeWeather = weatherRadio ? weatherRadio.value === "true" : true;
  
  // Get vessel parameters
  const vesselType = document.getElementById("vesselType")?.value || "Container_Ship";
  const cargoTonnes = parseFloat(document.getElementById("cargoTonnes")?.value) || 32500;
  const speedKnots = parseFloat(document.getElementById("speedKnots")?.value) || 20;
  const hullDays = parseInt(document.getElementById("hullDays")?.value) || 90;
  
  // Get departure time
  const departureTimeInput = document.getElementById("departureTime")?.value;
  const departureTime = departureTimeInput ? new Date(departureTimeInput) : new Date();
  
  // Get constraints
  const avoidECA = document.getElementById("avoidECA")?.checked || false;
  const optimizeTides = document.getElementById("optimizeTides")?.checked || false;
  const useCurrents = document.getElementById("useCurrents")?.checked || true;

  // Get physics model toggles
  const useHoltrop = document.getElementById("useHoltrop")?.checked || true;
  const useFouling = document.getElementById("useFouling")?.checked || true;
  const useWeather = document.getElementById("useWeather")?.checked || true;
  const useTides = document.getElementById("useTides")?.checked || true;
  const useECA = document.getElementById("useECA")?.checked || true;
  
  const ensembleSize = parseInt(document.getElementById("ensembleSize")?.value) || 10;

  // Validate inputs
  if (!startPort || !destinationPort) {
    alert("Please select both start and destination ports");
    return;
  }

  if (startPort === destinationPort) {
    alert("Start and destination ports cannot be the same");
    return;
  }

  // Clear map before loading
  refreshMapWithNewData();
  document.getElementById("loadingOverlay").style.display = "flex";
  document.getElementById("calculateBtn").disabled = true;

  // Update loading progress
  let progress = 0;
  const progressFill = document.getElementById("progressFill");
  const progressInterval = setInterval(() => {
    progress = Math.min(progress + 5, 90);
    if (progressFill) progressFill.style.width = progress + '%';
  }, 200);

  // Reset results panel
  const resultsPanel = document.getElementById("resultsPanel");
  if (resultsPanel) resultsPanel.style.display = "none";

  try {
    const response = await fetch("/calculate-routes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start_port: startPort,
        destination_port: destinationPort,
        hub_ports: hubPorts,
        goal: optimizationGoal,  // Use the defined variable
        include_weather: includeWeather && useWeather,
        vessel_type: vesselType,
        cargo_tonnes: cargoTonnes,
        speed_knots: speedKnots,
        hull_days: hullDays,
        departure_time: departureTime.toISOString(),
        use_holtrop: useHoltrop,
        use_fouling: useFouling,
        use_currents: useCurrents,
        use_tides: useTides,
        use_weather: useWeather,
        use_eca: useECA,
        ensemble_size: ensembleSize,
        constraints: {
          avoid_eca: avoidECA,
          optimize_tides: optimizeTides && useTides,
          use_currents: useCurrents
        }
      }),
    });

    clearInterval(progressInterval);
    if (progressFill) progressFill.style.width = '100%';

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server error ${response.status}: ${errorText}`);
    }

    const data = await response.json();

    if (!data || typeof data !== "object") {
      throw new Error("Invalid response format");
    }

    if (!data || (!data.fastest_route && !data.fuel_efficient_route)) {
      alert("No routes could be calculated. Please try different ports.");
      return;
    }

    currentMapData = data;
    // PASS optimizationGoal to displayResults
    displayResults(data, optimizationGoal);
    displayRoutesOnMap(data);

    setTimeout(() => { updateDashboardHeight(); }, 300);
    alert(`Route calculated in ${data.calculation_time || 0.1}s`);
    
  } catch (error) {
    console.error("❌ Error:", error);
    alert("Error calculating routes: " + error.message);
  } finally {
    clearInterval(progressInterval);
    document.getElementById("loadingOverlay").style.display = "none";
    document.getElementById("calculateBtn").disabled = false;
  }
}

// Update the function signature and usage of optimizationGoal
function displayResults(data, optimizationGoal = 'both') {
  console.log("📊 Displaying results with goal:", optimizationGoal);
  
  const resultsPanel = document.getElementById("resultsPanel");
  const resultsContent = document.getElementById("resultsContent");
  
  if (!resultsContent) return;

  resultsPanel.style.display = "block";

  const fastestRoute = data.fastest_route || {};
  const fuelRoute = data.fuel_efficient_route || {};
  
  const fastestPhysics = fastestRoute.physics || {};
  const fuelPhysics = fuelRoute.physics || {};

  const fastestPorts = fastestRoute.ports || [];
  const fuelPorts = fuelRoute.ports || [];

  const vesselInfo = data.vessel_info || { type: 'Container_Ship', cargo_tonnes: 32500 };
  
  const formatRoutePath = (ports) => {
    if (!ports || ports.length === 0) return "No route available";
    return ports.map((p, i) => {
      if (i === 0) return `<span class="port-start">${p}</span>`;
      if (i === ports.length - 1) return `<span class="port-end">${p}</span>`;
      return `<span class="port-hub">${p}</span>`;
    }).join(' <span class="route-arrow">→</span> ');
  };

  // Calculate comparison metrics
  const fuelDiff = (fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0);
  const timeDiff = ((fastestRoute.time_hours || 0) - (fuelRoute.time_hours || 0)) / 24;
  const costDiff = fuelDiff * 650;
  const co2Diff = fuelDiff * 3.114;
  
  // Determine winner for each metric
  const winner = {
    fuel: fuelDiff > 0 ? 'efficient' : (fuelDiff < 0 ? 'fastest' : 'tie'),
    time: timeDiff < 0 ? 'fastest' : (timeDiff > 0 ? 'efficient' : 'tie'),
    cost: costDiff > 0 ? 'efficient' : (costDiff < 0 ? 'fastest' : 'tie'),
    co2: co2Diff > 0 ? 'efficient' : (co2Diff < 0 ? 'fastest' : 'tie')
  };

  // Calculate percentages for visual bars
  const maxFuel = Math.max(fastestRoute.fuel_tonnes || 0, fuelRoute.fuel_tonnes || 0);
  const fastestFuelPercent = maxFuel > 0 ? (fastestRoute.fuel_tonnes / maxFuel) * 100 : 0;
  const fuelFuelPercent = maxFuel > 0 ? (fuelRoute.fuel_tonnes / maxFuel) * 100 : 0;

  const maxTime = Math.max(fastestRoute.time_hours || 0, fuelRoute.time_hours || 0);
  const fastestTimePercent = maxTime > 0 ? (fastestRoute.time_hours / maxTime) * 100 : 0;
  const fuelTimePercent = maxTime > 0 ? (fuelRoute.time_hours / maxTime) * 100 : 0;

  let html = '<div class="route-cards">';
  
  // Head-to-Head Comparison
  html += `
    <div class="comparison-header-card">
      <h3>⚔️ HEAD-TO-HEAD COMPARISON</h3>
      <div class="comparison-badges">
        <span class="comparison-badge fastest-badge">🚀 Fastest Route</span>
        <span class="comparison-badge efficient-badge">🌿 Efficient Route</span>
      </div>
    </div>
  `;

  // Visual Comparison Bars
  html += `
    <div class="visual-comparison">
      <div class="comparison-metric-group">
        <div class="metric-label-large">⛽ FUEL CONSUMPTION</div>
        <div class="comparison-bars">
          <div class="bar-container">
            <div class="bar-label">Fastest</div>
            <div class="bar-wrapper">
              <div class="bar-fill fastest-bar" style="width: ${fastestFuelPercent}%;"></div>
            </div>
            <div class="bar-value ${winner.fuel === 'fastest' ? 'winner' : ''}">${(fastestRoute.fuel_tonnes || 0).toFixed(1)} t</div>
          </div>
          <div class="bar-container">
            <div class="bar-label">Efficient</div>
            <div class="bar-wrapper">
              <div class="bar-fill efficient-bar" style="width: ${fuelFuelPercent}%;"></div>
            </div>
            <div class="bar-value ${winner.fuel === 'efficient' ? 'winner' : ''}">${(fuelRoute.fuel_tonnes || 0).toFixed(1)} t</div>
          </div>
        </div>
        <div class="comparison-difference ${fuelDiff > 0 ? 'positive' : (fuelDiff < 0 ? 'negative' : 'neutral')}">
          ${fuelDiff > 0 ? `✅ Efficient saves ${fuelDiff.toFixed(1)} tonnes (${((fuelDiff / fastestRoute.fuel_tonnes) * 100).toFixed(1)}%)` : 
            fuelDiff < 0 ? `⚠️ Fastest uses ${Math.abs(fuelDiff).toFixed(1)} tonnes less` : 
            '⚖️ Equal fuel consumption'}
        </div>
      </div>

      <div class="comparison-metric-group">
        <div class="metric-label-large">⏱️ TRANSIT TIME</div>
        <div class="comparison-bars">
          <div class="bar-container">
            <div class="bar-label">Fastest</div>
            <div class="bar-wrapper">
              <div class="bar-fill fastest-bar" style="width: ${fastestTimePercent}%;"></div>
            </div>
            <div class="bar-value ${winner.time === 'fastest' ? 'winner' : ''}">${((fastestRoute.time_hours || 0)/24).toFixed(1)} days</div>
          </div>
          <div class="bar-container">
            <div class="bar-label">Efficient</div>
            <div class="bar-wrapper">
              <div class="bar-fill efficient-bar" style="width: ${fuelTimePercent}%;"></div>
            </div>
            <div class="bar-value ${winner.time === 'efficient' ? 'winner' : ''}">${((fuelRoute.time_hours || 0)/24).toFixed(1)} days</div>
          </div>
        </div>
        <div class="comparison-difference ${timeDiff < 0 ? 'positive' : (timeDiff > 0 ? 'negative' : 'neutral')}">
          ${timeDiff < 0 ? `✅ Fastest saves ${Math.abs(timeDiff).toFixed(1)} days` : 
            timeDiff > 0 ? `⚠️ Efficient takes ${timeDiff.toFixed(1)} days longer` : 
            '⚖️ Equal transit time'}
        </div>
      </div>
    </div>
  `;

  // Winner Summary
  const fastestWins = [winner.time === 'fastest', winner.cost === 'fastest', winner.co2 === 'fastest'].filter(Boolean).length;
  const efficientWins = [winner.fuel === 'efficient', winner.cost === 'efficient', winner.co2 === 'efficient'].filter(Boolean).length;

  html += `
    <div class="winner-summary">
      <div class="winner-card ${fastestWins >= efficientWins ? 'highlight' : ''}">
        <div class="winner-icon">🚀</div>
        <div class="winner-stats">
          <div class="winner-title">Fastest Route</div>
          <div class="winner-metrics">
            <span class="winner-metric ${winner.time === 'fastest' ? 'win' : ''}">⏱️ ${((fastestRoute.time_hours || 0)/24).toFixed(1)}d</span>
            <span class="winner-metric ${winner.cost === 'fastest' ? 'win' : ''}">💰 $${((fastestRoute.fuel_tonnes || 0) * 650).toLocaleString()}</span>
            <span class="winner-metric ${winner.co2 === 'fastest' ? 'win' : ''}">🌍 ${((fastestRoute.fuel_tonnes || 0) * 3.114).toFixed(1)}t CO₂</span>
          </div>
        </div>
        <div class="winner-score">${fastestWins} wins</div>
      </div>
      
      <div class="winner-card ${efficientWins >= fastestWins ? 'highlight' : ''}">
        <div class="winner-icon">🌿</div>
        <div class="winner-stats">
          <div class="winner-title">Fuel-Efficient Route</div>
          <div class="winner-metrics">
            <span class="winner-metric ${winner.fuel === 'efficient' ? 'win' : ''}">⛽ ${(fuelRoute.fuel_tonnes || 0).toFixed(1)}t</span>
            <span class="winner-metric ${winner.cost === 'efficient' ? 'win' : ''}">💰 $${((fuelRoute.fuel_tonnes || 0) * 650).toLocaleString()}</span>
            <span class="winner-metric ${winner.co2 === 'efficient' ? 'win' : ''}">🌍 ${((fuelRoute.fuel_tonnes || 0) * 3.114).toFixed(1)}t CO₂</span>
          </div>
        </div>
        <div class="winner-score">${efficientWins} wins</div>
      </div>
    </div>
  `;

  // Detailed Route Cards
  html += `
    <div class="route-cards-grid">
      <!-- Fastest Route Card -->
      <div class="route-card fastest">
        <div class="route-card-header">
          <span class="route-icon">🚀</span>
          <span class="route-title">Fastest Route (A* Algorithm)</span>
          <span class="route-badge ${winner.time === 'fastest' ? 'winner-badge' : ''}">${((fastestRoute.time_hours || 0)/24).toFixed(1)} days</span>
        </div>
        <div class="route-path">
          <strong>Path:</strong> ${formatRoutePath(fastestPorts)}
        </div>
        <div class="route-stats-grid">
          <div class="stat-card ${winner.time === 'fastest' ? 'winner-stat' : ''}">
            <div class="stat-value">${((fastestRoute.time_hours || 0)/24).toFixed(1)} d</div>
            <div class="stat-label">⏱️ Transit Time</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${(fastestRoute.distance_km || 0).toFixed(0)} km</div>
            <div class="stat-label">📏 Distance</div>
          </div>
          <div class="stat-card ${winner.fuel === 'fastest' ? 'winner-stat' : ''}">
            <div class="stat-value">${(fastestRoute.fuel_tonnes || 0).toFixed(1)} t</div>
            <div class="stat-label">⛽ Fuel</div>
          </div>
          <div class="stat-card ${winner.cost === 'fastest' ? 'winner-stat' : ''}">
            <div class="stat-value">$${((fastestRoute.fuel_tonnes || 0) * 650).toLocaleString()}</div>
            <div class="stat-label">💰 Cost</div>
          </div>
          <div class="stat-card ${winner.co2 === 'fastest' ? 'winner-stat' : ''}">
            <div class="stat-value">${((fastestRoute.fuel_tonnes || 0) * 3.114).toFixed(1)} t</div>
            <div class="stat-label">🌍 CO₂</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${fastestRoute.ports?.length || 0}</div>
            <div class="stat-label">⚓ Ports</div>
          </div>
        </div>
  `;

  // Holtrop-Mennen Resistance
  if (fastestPhysics.components) {
    html += `
      <div class="physics-section">
        <div class="section-header" onclick="toggleSection('fastest-holtrop')">
          <span>🔬 Holtrop-Mennen (1982) Resistance</span>
          <span class="toggle-icon">▼</span>
        </div>
        <div class="section-content" id="fastest-holtrop" style="display: none;">
          <div class="resistance-grid">
            <div class="resistance-item"><span class="resistance-label">Viscous:</span><span class="resistance-value">${(fastestPhysics.components.viscous || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item"><span class="resistance-label">Wave-making:</span><span class="resistance-value">${(fastestPhysics.components.wave_making || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item"><span class="resistance-label">Bulbous bow:</span><span class="resistance-value">${(fastestPhysics.components.bulbous_bow || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item"><span class="resistance-label">Appendage:</span><span class="resistance-value">${(fastestPhysics.components.appendage || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item total"><span class="resistance-label">Total:</span><span class="resistance-value">${(fastestPhysics.total_resistance_kN || 0).toFixed(1)} kN</span></div>
          </div>
        </div>
      </div>
    `;
  }

  // Biofouling
  if (fastestPhysics.fouling_breakdown) {
    html += `
      <div class="physics-section">
        <div class="section-header" onclick="toggleSection('fastest-fouling')">
          <span>🦪 Biofouling Analysis</span>
          <span class="toggle-icon">▼</span>
        </div>
        <div class="section-content" id="fastest-fouling" style="display: none;">
          <div class="fouling-grid">
            <div class="fouling-item"><span class="fouling-organism">Slime:</span><span class="fouling-value">${fastestPhysics.fouling_breakdown.slime?.penalty || 0}%</span></div>
            <div class="fouling-item"><span class="fouling-organism">Barnacles:</span><span class="fouling-value">${fastestPhysics.fouling_breakdown.barnacles?.penalty || 0}%</span></div>
            <div class="fouling-item"><span class="fouling-organism">Tubeworms:</span><span class="fouling-value">${fastestPhysics.fouling_breakdown.tubeworms?.penalty || 0}%</span></div>
            <div class="fouling-item"><span class="fouling-organism">Algae:</span><span class="fouling-value">${fastestPhysics.fouling_breakdown.algae?.penalty || 0}%</span></div>
            <div class="fouling-item total"><span class="fouling-organism">Total Penalty:</span><span class="fouling-value fouling-penalty">+${fastestPhysics.fouling_penalty || 0}%</span></div>
          </div>
        </div>
      </div>
    `;
  }

  // Ocean Current
  if (fastestPhysics.ocean_current_benefit !== undefined) {
    html += `
      <div class="physics-section">
        <div class="section-header" onclick="toggleSection('fastest-current')">
          <span>🌊 Ocean Current Analysis</span>
          <span class="toggle-icon">▼</span>
        </div>
        <div class="section-content" id="fastest-current" style="display: none;">
          <div class="current-metrics">
            <div class="current-item">
              <span class="current-label">Current Benefit:</span>
              <span class="current-value ${fastestPhysics.ocean_current_benefit > 0 ? 'positive' : 'negative'}">
                ${fastestPhysics.ocean_current_benefit > 0 ? '+' : ''}${fastestPhysics.ocean_current_benefit || 0}%
              </span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  html += `<div class="arrival-info"><span class="arrival-label">Estimated Arrival:</span><span class="arrival-value">${new Date(Date.now() + (fastestRoute.time_hours || 0)*3600000).toLocaleString()}</span></div></div>`;

  // Fuel-Efficient Route Card
  html += `
    <div class="route-card fuel-efficient">
      <div class="route-card-header">
        <span class="route-icon">🌿</span>
        <span class="route-title">Fuel-Efficient Route (Genetic Algorithm)</span>
        <span class="route-badge ${winner.fuel === 'efficient' ? 'winner-badge' : ''}">${((fuelRoute.time_hours || 0)/24).toFixed(1)} days</span>
      </div>
      <div class="route-path">
        <strong>Path:</strong> ${formatRoutePath(fuelPorts)}
      </div>
      <div class="route-stats-grid">
        <div class="stat-card">
          <div class="stat-value">${((fuelRoute.time_hours || 0)/24).toFixed(1)} d</div>
          <div class="stat-label">⏱️ Transit Time</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${(fuelRoute.distance_km || 0).toFixed(0)} km</div>
          <div class="stat-label">📏 Distance</div>
        </div>
        <div class="stat-card ${winner.fuel === 'efficient' ? 'winner-stat' : ''}">
          <div class="stat-value">${(fuelRoute.fuel_tonnes || 0).toFixed(1)} t</div>
          <div class="stat-label">⛽ Fuel</div>
        </div>
        <div class="stat-card ${winner.cost === 'efficient' ? 'winner-stat' : ''}">
          <div class="stat-value">$${((fuelRoute.fuel_tonnes || 0) * 650).toLocaleString()}</div>
          <div class="stat-label">💰 Cost</div>
        </div>
        <div class="stat-card ${winner.co2 === 'efficient' ? 'winner-stat' : ''}">
          <div class="stat-value">${((fuelRoute.fuel_tonnes || 0) * 3.114).toFixed(1)} t</div>
          <div class="stat-label">🌍 CO₂</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${fuelRoute.ports?.length || 0}</div>
          <div class="stat-label">⚓ Ports</div>
        </div>
      </div>
  `;

  if (fuelPhysics.components) {
    html += `
      <div class="physics-section">
        <div class="section-header" onclick="toggleSection('fuel-holtrop')">
          <span>🔬 Holtrop-Mennen (1982) Resistance</span>
          <span class="toggle-icon">▼</span>
        </div>
        <div class="section-content" id="fuel-holtrop" style="display: none;">
          <div class="resistance-grid">
            <div class="resistance-item"><span class="resistance-label">Viscous:</span><span class="resistance-value">${(fuelPhysics.components.viscous || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item"><span class="resistance-label">Wave-making:</span><span class="resistance-value">${(fuelPhysics.components.wave_making || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item"><span class="resistance-label">Bulbous bow:</span><span class="resistance-value">${(fuelPhysics.components.bulbous_bow || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item"><span class="resistance-label">Appendage:</span><span class="resistance-value">${(fuelPhysics.components.appendage || 0).toFixed(1)} kN</span></div>
            <div class="resistance-item total"><span class="resistance-label">Total:</span><span class="resistance-value">${(fuelPhysics.total_resistance_kN || 0).toFixed(1)} kN</span></div>
          </div>
        </div>
      </div>
    `;
  }

  if (fuelPhysics.fouling_breakdown) {
    html += `
      <div class="physics-section">
        <div class="section-header" onclick="toggleSection('fuel-fouling')">
          <span>🦪 Biofouling Analysis</span>
          <span class="toggle-icon">▼</span>
        </div>
        <div class="section-content" id="fuel-fouling" style="display: none;">
          <div class="fouling-grid">
            <div class="fouling-item"><span class="fouling-organism">Slime:</span><span class="fouling-value">${fuelPhysics.fouling_breakdown.slime?.penalty || 0}%</span></div>
            <div class="fouling-item"><span class="fouling-organism">Barnacles:</span><span class="fouling-value">${fuelPhysics.fouling_breakdown.barnacles?.penalty || 0}%</span></div>
            <div class="fouling-item"><span class="fouling-organism">Tubeworms:</span><span class="fouling-value">${fuelPhysics.fouling_breakdown.tubeworms?.penalty || 0}%</span></div>
            <div class="fouling-item"><span class="fouling-organism">Algae:</span><span class="fouling-value">${fuelPhysics.fouling_breakdown.algae?.penalty || 0}%</span></div>
            <div class="fouling-item total"><span class="fouling-organism">Total Penalty:</span><span class="fouling-value fouling-penalty">+${fuelPhysics.fouling_penalty || 0}%</span></div>
          </div>
        </div>
      </div>
    `;
  }

  html += `<div class="arrival-info"><span class="arrival-label">Estimated Arrival:</span><span class="arrival-value">${new Date(Date.now() + (fuelRoute.time_hours || 0)*3600000).toLocaleString()}</span></div></div>`;

  html += '</div>'; // Close route-cards-grid

  // Detailed Comparison Table
  html += `
    <div class="comparison-table-detailed">
      <h4>📊 Detailed Metric Comparison</h4>
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Fastest Route</th>
            <th>Efficient Route</th>
            <th>Difference</th>
            <th>% Change</th>
            <th>Winner</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Distance (km)</td>
            <td class="fastest">${(fastestRoute.distance_km || 0).toFixed(0)}</td>
            <td class="efficient">${(fuelRoute.distance_km || 0).toFixed(0)}</td>
            <td class="${(fastestRoute.distance_km || 0) > (fuelRoute.distance_km || 0) ? 'negative' : 'positive'}">
              ${Math.abs((fastestRoute.distance_km || 0) - (fuelRoute.distance_km || 0)).toFixed(0)}
            </td>
            <td class="${(fastestRoute.distance_km || 0) > (fuelRoute.distance_km || 0) ? 'negative' : 'positive'}">
              ${(((fastestRoute.distance_km || 0) - (fuelRoute.distance_km || 0)) / (fuelRoute.distance_km || 1) * 100).toFixed(1)}%
            </td>
            <td class="winner-cell">${(fastestRoute.distance_km || 0) < (fuelRoute.distance_km || 0) ? '🚀 Fastest' : ((fastestRoute.distance_km || 0) > (fuelRoute.distance_km || 0) ? '🌿 Efficient' : '⚖️ Tie')}</td>
          </tr>
          <tr>
            <td>Time (days)</td>
            <td class="fastest">${((fastestRoute.time_hours || 0)/24).toFixed(1)}</td>
            <td class="efficient">${((fuelRoute.time_hours || 0)/24).toFixed(1)}</td>
            <td class="${((fastestRoute.time_hours || 0) - (fuelRoute.time_hours || 0)) < 0 ? 'positive' : 'negative'}">
              ${Math.abs(((fastestRoute.time_hours || 0) - (fuelRoute.time_hours || 0))/24).toFixed(1)}
            </td>
            <td class="${((fastestRoute.time_hours || 0) - (fuelRoute.time_hours || 0)) < 0 ? 'positive' : 'negative'}">
              ${(((fastestRoute.time_hours || 0) - (fuelRoute.time_hours || 0)) / (fuelRoute.time_hours || 1) * 100).toFixed(1)}%
            </td>
            <td class="winner-cell">${((fastestRoute.time_hours || 0) < (fuelRoute.time_hours || 0)) ? '🚀 Fastest' : (((fastestRoute.time_hours || 0) > (fuelRoute.time_hours || 0)) ? '🌿 Efficient' : '⚖️ Tie')}</td>
          </tr>
          <tr>
            <td>Fuel (tonnes)</td>
            <td class="fastest">${(fastestRoute.fuel_tonnes || 0).toFixed(1)}</td>
            <td class="efficient">${(fuelRoute.fuel_tonnes || 0).toFixed(1)}</td>
            <td class="${((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) > 0 ? 'positive' : 'negative'}">
              ${Math.abs((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)).toFixed(1)}
            </td>
            <td class="${((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) > 0 ? 'positive' : 'negative'}">
              ${(((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) / (fuelRoute.fuel_tonnes || 1) * 100).toFixed(1)}%
            </td>
            <td class="winner-cell">${((fastestRoute.fuel_tonnes || 0) < (fuelRoute.fuel_tonnes || 0)) ? '🚀 Fastest' : (((fastestRoute.fuel_tonnes || 0) > (fuelRoute.fuel_tonnes || 0)) ? '🌿 Efficient' : '⚖️ Tie')}</td>
          </tr>
          <tr>
            <td>CO₂ (tonnes)</td>
            <td class="fastest">${((fastestRoute.fuel_tonnes || 0) * 3.114).toFixed(1)}</td>
            <td class="efficient">${((fuelRoute.fuel_tonnes || 0) * 3.114).toFixed(1)}</td>
            <td class="${((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) > 0 ? 'positive' : 'negative'}">
              ${(Math.abs((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) * 3.114).toFixed(1)}
            </td>
            <td class="${((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) > 0 ? 'positive' : 'negative'}">
              ${((((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) * 3.114) / ((fuelRoute.fuel_tonnes || 1) * 3.114) * 100).toFixed(1)}%
            </td>
            <td class="winner-cell">${((fastestRoute.fuel_tonnes || 0) < (fuelRoute.fuel_tonnes || 0)) ? '🚀 Fastest' : (((fastestRoute.fuel_tonnes || 0) > (fuelRoute.fuel_tonnes || 0)) ? '🌿 Efficient' : '⚖️ Tie')}</td>
          </tr>
          <tr>
            <td>Cost (USD)</td>
            <td class="fastest">$${((fastestRoute.fuel_tonnes || 0) * 650).toLocaleString()}</td>
            <td class="efficient">$${((fuelRoute.fuel_tonnes || 0) * 650).toLocaleString()}</td>
            <td class="${((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) > 0 ? 'positive' : 'negative'}">
              $${(Math.abs((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) * 650).toLocaleString()}
            </td>
            <td class="${((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) > 0 ? 'positive' : 'negative'}">
              ${((((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) * 650) / ((fuelRoute.fuel_tonnes || 1) * 650) * 100).toFixed(1)}%
            </td>
            <td class="winner-cell">${((fastestRoute.fuel_tonnes || 0) < (fuelRoute.fuel_tonnes || 0)) ? '🚀 Fastest' : (((fastestRoute.fuel_tonnes || 0) > (fuelRoute.fuel_tonnes || 0)) ? '🌿 Efficient' : '⚖️ Tie')}</td>
          </tr>
        </tbody>
      </table>
    </div>
  `;

  // Final Recommendation - using optimizationGoal from the calculateRoutes function
  let recommendation = "";
  let recommendationClass = "";
  let recommendationIcon = "";

  if (fuelDiff > 50 && Math.abs(timeDiff) < 2) {
    recommendation = "Fuel-Efficient Route is STRONGLY RECOMMENDED";
    recommendationClass = "strong-efficient";
    recommendationIcon = "🌿✅";
  } else if (timeDiff < -2 && Math.abs(fuelDiff) < 30) {
    recommendation = "Fastest Route is STRONGLY RECOMMENDED";
    recommendationClass = "strong-fastest";
    recommendationIcon = "🚀✅";
  } else if (fuelDiff > 30) {
    recommendation = "Fuel-Efficient Route is Recommended";
    recommendationClass = "recommend-efficient";
    recommendationIcon = "🌿";
  } else if (timeDiff < -1) {
    recommendation = "Fastest Route is Recommended";
    recommendationClass = "recommend-fastest";
    recommendationIcon = "🚀";
  } else {
    recommendation = "Balanced Choice - Either Route Works Well";
    recommendationClass = "recommend-balanced";
    recommendationIcon = "⚖️";
  }

  // Get the optimization goal for display
  const goalDisplay = optimizationGoal === 'both' ? 'Balanced' : 
                     (optimizationGoal === 'fastest' ? 'Time Priority' : 'Fuel Priority');

  html += `
    <div class="final-recommendation ${recommendationClass}">
      <div class="recommendation-icon">${recommendationIcon}</div>
      <div class="recommendation-content">
        <h4>${recommendation}</h4>
        <p>Based on your optimization criteria (${goalDisplay})</p>
        <div class="recommendation-details">
          ${fuelDiff > 0 ? `<span class="detail">⛽ Fuel savings: ${fuelDiff.toFixed(1)} tonnes</span>` : ''}
          ${timeDiff < 0 ? `<span class="detail">⏱️ Time savings: ${Math.abs(timeDiff).toFixed(1)} days</span>` : ''}
          ${costDiff > 0 ? `<span class="detail">💰 Cost savings: $${costDiff.toLocaleString()}</span>` : ''}
        </div>
        <div class="confidence-meter">
          <div class="confidence-label">Confidence: ${(data.ensemble_confidence * 100 || 85).toFixed(0)}%</div>
          <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${(data.ensemble_confidence * 100 || 85)}%"></div>
          </div>
        </div>
      </div>
    </div>
  `;

  resultsContent.innerHTML = html;

  updateResultsMeta(fastestPorts, fuelPorts, vesselInfo);
  updateDashboardMetrics(fastestRoute, fuelRoute);
  updateRouteComparison(fastestRoute, fuelRoute);
  updateConfidenceMetrics(data);
}
// Add this to your script.js
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    
    const header = section.previousElementSibling;
    const icon = header ? header.querySelector('.toggle-icon') : null;
    
    if (section.style.display === 'none' || section.style.display === '') {
        section.style.display = 'block';
        if (icon) icon.textContent = '▲';
        section.classList.add('active');
    } else {
        section.style.display = 'none';
        if (icon) icon.textContent = '▼';
        section.classList.remove('active');
    }
}

// Initialize physics sections to be hidden by default
document.addEventListener('DOMContentLoaded', function() {
    // Hide all physics sections initially
    document.querySelectorAll('.section-content').forEach(section => {
        section.style.display = 'none';
    });
    
    // Set toggle icons to down arrows
    document.querySelectorAll('.toggle-icon').forEach(icon => {
        icon.textContent = '▼';
    });
});
function updateResultsMeta(fastestPorts, fuelPorts, vesselInfo) {
  const meta = document.getElementById('resultsMeta');
  if (meta) {
    const totalPorts = new Set([...fastestPorts, ...fuelPorts]).size;
    meta.innerHTML = `<span>⚓ ${totalPorts} ports</span><span>🚢 ${vesselInfo.type.replace('_', ' ')}</span>`;
  }
}

function updateDashboardMetrics(fastestRoute, fuelRoute) {
  const avgTimeEl = document.getElementById('avgTransitTime');
  if (avgTimeEl) {
    avgTimeEl.textContent = `${(((fastestRoute.time_hours || 0) + (fuelRoute.time_hours || 0)) / 2 / 24).toFixed(1)} days`;
  }
  
  const fuelEfficiencyEl = document.getElementById('fuelEfficiency');
  if (fuelEfficiencyEl) {
    fuelEfficiencyEl.textContent = `${(((fastestRoute.fuel_tonnes || 0) + (fuelRoute.fuel_tonnes || 0)) / 2 / ((fastestRoute.distance_km || 1) + (fuelRoute.distance_km || 1)) * 200).toFixed(2)} t/100km`;
  }
  
  const distanceDiff = (fastestRoute.distance_km || 0) - (fuelRoute.distance_km || 0);
  const distanceSavedEl = document.getElementById('distanceSaved');
  if (distanceSavedEl) {
    distanceSavedEl.textContent = distanceDiff > 0 ? `${distanceDiff.toFixed(0)} km longer` : `${Math.abs(distanceDiff).toFixed(0)} km shorter`;
  }
  
  const costDiff = ((fastestRoute.fuel_tonnes || 0) - (fuelRoute.fuel_tonnes || 0)) * 650;
  const costSavingsEl = document.getElementById('costSavings');
  if (costSavingsEl) {
    costSavingsEl.textContent = costDiff > 0 ? `$${costDiff.toFixed(0)} cheaper` : `$${Math.abs(costDiff).toFixed(0)} more`;
  }
  
  const lastUpdatedEl = document.getElementById('statsLastUpdated');
  if (lastUpdatedEl) {
    lastUpdatedEl.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
  }
}
function toggleWeatherLayer() {
  if (window.weatherMarkers) {
    const allVisible = window.weatherMarkers.every(marker => map.hasLayer(marker));
    const toggleBtn = document.getElementById("weatherToggle");
    
    window.weatherMarkers.forEach(marker => {
      if (allVisible) {
        map.removeLayer(marker);
        if (toggleBtn) toggleBtn.classList.remove('active');
      } else {
        marker.addTo(map);
        if (toggleBtn) toggleBtn.classList.add('active');
      }
    });
  }
}
function exportMap() {
  if (!map) {
    alert("Map not initialized");
    return;
  }
  
  // Use leaflet-image or similar plugin, or just provide info
  alert("Map export functionality requires leaflet-image plugin.\nYou can take a screenshot manually.");
}

function exportResults() {
  if (!currentMapData) {
    alert("No results to export");
    return;
  }
  
  const dataStr = JSON.stringify(currentMapData, null, 2);
  const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
  
  const exportFileDefaultName = `route_export_${new Date().toISOString()}.json`;
  
  const linkElement = document.createElement('a');
  linkElement.setAttribute('href', dataUri);
  linkElement.setAttribute('download', exportFileDefaultName);
  linkElement.click();
}

function generateReport() {
  if (!currentMapData) {
    alert("No results to generate report");
    return;
  }
  
  // Simple HTML report generation
  const fastest = currentMapData.fastest_route || {};
  const efficient = currentMapData.fuel_efficient_route || {};
  
  const reportHTML = `
    <html>
      <head><title>Maritime Route Report</title></head>
      <body>
        <h1>Route Optimization Report</h1>
        <p>Generated: ${new Date().toLocaleString()}</p>
        <h2>Fastest Route</h2>
        <p>Distance: ${(fastest.distance_km || 0).toFixed(0)} km</p>
        <p>Fuel: ${(fastest.fuel_tonnes || 0).toFixed(1)} tonnes</p>
        <p>Time: ${((fastest.time_hours || 0)/24).toFixed(1)} days</p>
        <h2>Fuel-Efficient Route</h2>
        <p>Distance: ${(efficient.distance_km || 0).toFixed(0)} km</p>
        <p>Fuel: ${(efficient.fuel_tonnes || 0).toFixed(1)} tonnes</p>
        <p>Time: ${((efficient.time_hours || 0)/24).toFixed(1)} days</p>
      </body>
    </html>
  `;
  
  const blob = new Blob([reportHTML], {type: 'text/html'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `route_report_${new Date().toISOString()}.html`;
  a.click();
}
function navLoadSection(section) {
  console.log(`Navigating to ${section}`);
  // Update active state
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
  });
  
  const activeItem = document.querySelector(`[onclick*="${section}"]`);
  if (activeItem) activeItem.classList.add('active');
  
  // Show/hide appropriate sections
  const mainContent = document.querySelector('.main-content');
  const analyticsSection = document.getElementById('analyticsSection');
  
  if (section === 'analytics') {
    if (mainContent) mainContent.style.display = 'none';
    if (analyticsSection) analyticsSection.style.display = 'block';
    loadAnalyticsData();
  } else {
    if (mainContent) mainContent.style.display = 'grid';
    if (analyticsSection) analyticsSection.style.display = 'none';
  }
}

function loadAnalyticsData() {
  fetch('/api/realtime-analytics')
    .then(response => response.json())
    .then(data => {
      console.log('Analytics data loaded:', data);
      // Update analytics UI here
    })
    .catch(error => console.error('Error loading analytics:', error));
}

function switchDashboardTab(tabName) {
  // Hide all tabs
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // Deactivate all tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Show selected tab
  const selectedTab = document.getElementById(tabName + 'Tab');
  if (selectedTab) selectedTab.classList.add('active');
  
  // Activate button
  const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(
    btn => btn.textContent.toLowerCase().includes(tabName)
  );
  if (activeBtn) activeBtn.classList.add('active');
}
function updateRouteComparison(fastestRoute, fuelRoute) {
  const comparisonSection = document.getElementById("routeComparison");
  if (!fastestRoute.distance_km || !fuelRoute.distance_km) {
    if (comparisonSection) comparisonSection.style.display = 'none';
    return;
  }
  if (comparisonSection) comparisonSection.style.display = 'block';

  const fastestDistEl = document.getElementById("fastestDist");
  const efficientDistEl = document.getElementById("efficientDist");
  const distDeltaEl = document.getElementById("distDelta");
  
  if (fastestDistEl) fastestDistEl.textContent = (fastestRoute.distance_km || 0).toFixed(0);
  if (efficientDistEl) efficientDistEl.textContent = (fuelRoute.distance_km || 0).toFixed(0);
  const distDelta = (fastestRoute.distance_km || 0) - (fuelRoute.distance_km || 0);
  if (distDeltaEl) distDeltaEl.textContent = Math.abs(distDelta).toFixed(0);

  const fastestTime = (fastestRoute.time_hours || 0) / 24;
  const fuelTime = (fuelRoute.time_hours || 0) / 24;
  const fastestTimeEl = document.getElementById("fastestTime");
  const efficientTimeEl = document.getElementById("efficientTime");
  const timeDeltaEl = document.getElementById("timeDelta");
  
  if (fastestTimeEl) fastestTimeEl.textContent = fastestTime.toFixed(1);
  if (efficientTimeEl) efficientTimeEl.textContent = fuelTime.toFixed(1);
  const timeDelta = fastestTime - fuelTime;
  if (timeDeltaEl) timeDeltaEl.textContent = Math.abs(timeDelta).toFixed(1);

  const fastestFuel = fastestRoute.fuel_tonnes || 0;
  const fuelFuel = fuelRoute.fuel_tonnes || 0;
  const fastestFuelEl = document.getElementById("fastestFuel");
  const efficientFuelEl = document.getElementById("efficientFuel");
  const fuelDeltaEl = document.getElementById("fuelDelta");
  
  if (fastestFuelEl) fastestFuelEl.textContent = fastestFuel.toFixed(1);
  if (efficientFuelEl) efficientFuelEl.textContent = fuelFuel.toFixed(1);
  const fuelDelta = fastestFuel - fuelFuel;
  if (fuelDeltaEl) fuelDeltaEl.textContent = Math.abs(fuelDelta).toFixed(1);

  const fastestCO2 = fastestFuel * 3.114;
  const fuelCO2 = fuelFuel * 3.114;
  const fastestCO2El = document.getElementById("fastestCO2");
  const efficientCO2El = document.getElementById("efficientCO2");
  const co2DeltaEl = document.getElementById("co2Delta");
  
  if (fastestCO2El) fastestCO2El.textContent = fastestCO2.toFixed(1);
  if (efficientCO2El) efficientCO2El.textContent = fuelCO2.toFixed(1);
  const co2Delta = fastestCO2 - fuelCO2;
  if (co2DeltaEl) co2DeltaEl.textContent = Math.abs(co2Delta).toFixed(1);

  const fuelPrice = 650;
  const fastestCost = fastestFuel * fuelPrice;
  const fuelCost = fuelFuel * fuelPrice;
  const fastestCostEl = document.getElementById("fastestCost");
  const efficientCostEl = document.getElementById("efficientCost");
  const costDeltaEl = document.getElementById("costDelta");
  
  if (fastestCostEl) fastestCostEl.textContent = '$' + fastestCost.toLocaleString();
  if (efficientCostEl) efficientCostEl.textContent = '$' + fuelCost.toLocaleString();
  const costDelta = fastestCost - fuelCost;
  if (costDeltaEl) costDeltaEl.textContent = '$' + Math.abs(costDelta).toLocaleString();
}

function updateConfidenceMetrics(data) {
  const confidence = data.ensemble_confidence || 0.85;
  const confidenceBar = document.getElementById("confidenceBar");
  const confidenceValue = document.getElementById("confidenceValue");
  const confidenceMetrics = document.getElementById("confidenceMetrics");
  
  if (confidenceBar) confidenceBar.style.width = (confidence * 100) + '%';
  if (confidenceValue) confidenceValue.textContent = (confidence * 100).toFixed(0) + '%';
  if (confidenceMetrics) confidenceMetrics.style.display = 'block';
}

// ========== WEATHER MARKERS ==========
function addWeatherMarkers(data) {
  if (window.weatherMarkers) {
    window.weatherMarkers.forEach((marker) => map.removeLayer(marker));
  }
  window.weatherMarkers = [];

  if (data.fastest_route?.weather_impact?.weather_points) {
    data.fastest_route.weather_impact.weather_points.forEach((point, index) => {
      const marker = L.marker(point.coordinates)
        .bindPopup(`<div><h5>🚀 Point ${index + 1}</h5><p><strong>Wind:</strong> ${(point.weather.wind_speed || 0).toFixed(1)} km/h</p><p><strong>Wave:</strong> ${(point.weather.wave_height || 0).toFixed(1)} m</p><p><strong>Impact:</strong> ${(point.impact_score || 0).toFixed(1)}/10</p></div>`)
        .addTo(map);
      window.weatherMarkers.push(marker);
    });
  }
}

// ========== STATISTICS FUNCTIONS ==========
function resetStatistics() {
  const elements = [
    'avgTransitTime', 'fuelEfficiency', 'distanceSaved', 'costSavings', 'statsLastUpdated',
    'timeDifference', 'fuelDifference', 'recommendedRoute'
  ];
  elements.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '--';
  });

  const comparisonSection = document.getElementById("routeComparison");
  if (comparisonSection) comparisonSection.style.display = "none";
}

function updateDashboardHeight() {
  const dashboard = document.querySelector(".metrics-dashboard");
  const routeComparison = document.getElementById("routeComparison");
  if (!dashboard) return;

  if (routeComparison && routeComparison.style.display === "block") {
    dashboard.style.minHeight = "950px";
    dashboard.style.height = "950px";
  } else {
    dashboard.style.minHeight = "850px";
    dashboard.style.height = "850px";
  }
}

// ========== UTILITY FUNCTIONS ==========
function safeNumberFormat(value, decimals = 2) {
  if (value === undefined || value === null || isNaN(value)) return "N/A";
  return Number(value).toFixed(decimals);
}

function fixLegendPosition() {
  const legend = document.getElementById("mapLegend");
  if (legend) {
    legend.style.top = "auto";
    legend.style.bottom = "80px";
    legend.style.right = "20px";
    legend.style.left = "auto";
    legend.style.display = "block";
    legend.style.zIndex = "1000";
  }
}

// ========== EXPORT FUNCTIONS ==========
function saveCurrentRoute() {
  if (!currentMapData) {
    alert("No route data to save.");
    return;
  }
  const routeData = { timestamp: new Date().toISOString(), data: currentMapData };
  const savedRoutes = JSON.parse(localStorage.getItem("savedRoutes") || "[]");
  savedRoutes.push(routeData);
  localStorage.setItem("savedRoutes", JSON.stringify(savedRoutes));
  alert("Route saved successfully!");
}

function resetEverything() {
  console.log("🧹 Resetting everything...");

  refreshMapWithNewData();

  document.getElementById("startPort").value = "";
  document.getElementById("destinationPort").value = "";

  const hubPortsSelect = document.getElementById("hubPorts");
  if (hubPortsSelect) {
    Array.from(hubPortsSelect.options).forEach(option => option.selected = false);
  }

  document.querySelectorAll('input[name="goal"]').forEach(radio => {
    radio.checked = radio.value === "both";
  });

  document.querySelectorAll('input[name="weather"]').forEach(radio => {
    radio.checked = radio.value === "true";
  });

  updateSelectedPortsDisplay();

  const resultsPanel = document.getElementById("resultsPanel");
  if (resultsPanel) resultsPanel.style.display = "none";

  updateDashboardHeight();

  if (map) {
    setTimeout(() => {
      map.setView([20, 0], 2);
      map.invalidateSize();
    }, 50);
  }

  resetStatistics();
  console.log("✅ Everything reset");
}

// ========== EVENT LISTENERS ==========
function setupEventListeners() {
  const calculateBtn = document.getElementById("calculateBtn");
  if (calculateBtn) calculateBtn.addEventListener("click", calculateRoutes);

  const hubPorts = document.getElementById("hubPorts");
  if (hubPorts) hubPorts.addEventListener("change", updateSelectedPortsDisplay);
}

window.addEventListener("resize", fixLegendPosition);

// Make functions globally available
window.toggleRoute = toggleRoute;
window.zoomToRoutes = zoomToRoutes;
window.toggleLegend = toggleLegend;
window.toggleFullscreen = toggleFullscreen;
window.toggleAdvancedParams = toggleAdvancedParams;
window.toggleSection = toggleSection;
window.saveCurrentRoute = saveCurrentRoute;
window.resetEverything = resetEverything;
window.removePortFromSelection = removePortFromSelection;
window.clearSelectedPorts = clearSelectedPorts;