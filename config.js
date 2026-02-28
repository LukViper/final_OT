// Dynamic Configuration System
const DYNAMIC_CONFIG = {
    // Application Settings
    app: {
        title: "MaritimeRoute Pro",
        tagline: "AI-Powered Shipping Optimization",
        version: "2.1.0",
        defaultLanguage: "en",
        supportedLanguages: ["en", "es", "fr", "de", "zh"],
        theme: "dark",
        units: "metric"
    },

    // Data Sources
    dataSources: {
        ports: {
            url: "/api/ports",
            updateInterval: 3600000,
            fallback: "/static/data/ports.json"
        },
        routes: {
            url: "/api/routes",
            updateInterval: 1800000
        },
        weather: {
            url: "/api/weather",
            updateInterval: 900000
        },
        fuelPrices: {
            url: "/api/fuel-prices",
            updateInterval: 86400000
        }
    },

    // Algorithms Configuration
    algorithms: {
        "A* Search": {
            id: "astar",
            description: "Optimal pathfinding with heuristic search",
            parameters: {
                heuristic: "haversine",
                weight: 1.0
            },
            compatibleWith: ["fastest", "fuel", "balanced"],
            color: "#ff6b35"
        },
        "Genetic Algorithm": {
            id: "genetic",
            description: "Multi-objective optimization with evolutionary computing",
            parameters: {
                populationSize: 100,
                generations: 500,
                mutationRate: 0.01
            },
            compatibleWith: ["balanced", "multi-objective"],
            color: "#9b59b6"
        },
        "Dijkstra's": {
            id: "dijkstra",
            description: "Guaranteed shortest path algorithm",
            parameters: {
                priority: "distance"
            },
            compatibleWith: ["fastest", "fuel"],
            color: "#3498db"
        }
    },

    // Optimization Goals
    optimizationGoals: {
        "fastest": {
            name: "Time Priority",
            description: "Minimum transit time",
            icon: "🚀",
            color: "#ff6b35",
            parameters: ["time", "speed"]
        },
        "fuel": {
            name: "Efficiency Priority",
            description: "Minimum fuel consumption",
            icon: "🌿",
            color: "#2ecc71",
            parameters: ["fuel", "emissions"]
        },
        "balanced": {
            name: "Balanced Analysis",
            description: "Compare fastest vs most efficient",
            icon: "⚖️",
            color: "#3498db",
            parameters: ["time", "fuel", "cost"]
        },
        "cost": {
            name: "Cost Optimization",
            description: "Minimum operational cost",
            icon: "💰",
            color: "#f39c12",
            parameters: ["fuel", "port_fees", "time"]
        },
        "safety": {
            name: "Safety First",
            description: "Prioritize safe navigation routes",
            icon: "🛡️",
            color: "#9b59b6",
            parameters: ["weather", "traffic", "depth"]
        }
    },

    // Map Configuration
    map: {
        defaultView: [20, 0],
        defaultZoom: 2,
        maxZoom: 18,
        minZoom: 1,
        layers: {
            base: [
                {
                    name: "OpenStreetMap",
                    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                    attribution: "© OpenStreetMap contributors",
                    active: true
                },
                {
                    name: "Satellite",
                    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    attribution: "© Esri",
                    active: false
                }
            ],
            overlay: [
                {
                    name: "OpenSeaMap",
                    url: "https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
                    attribution: "© OpenSeaMap contributors",
                    opacity: 0.7,
                    active: true
                }
            ]
        },
        legend: {
            items: [
                {
                    name: "Fastest Route",
                    color: "#ff6b35",
                    pattern: "solid"
                },
                {
                    name: "Efficient Route",
                    color: "#2ecc71",
                    pattern: "solid"
                },
                {
                    name: "Direct Route",
                    color: "#3498db",
                    pattern: "dashed"
                },
                {
                    name: "Departure Port",
                    color: "#27ae60",
                    symbol: "circle"
                },
                {
                    name: "Destination Port",
                    color: "#e74c3c",
                    symbol: "circle"
                },
                {
                    name: "Intermediate Port",
                    color: "#9b59b6",
                    symbol: "circle"
                }
            ]
        }
    },

    // UI Text Configuration (for internationalization)
    uiText: {
        en: {
            appTitle: "MaritimeRoute Pro",
            appTagline: "AI-Powered Shipping Optimization",
            panelTitle: "Route Configuration",
            departureLabel: "Departure Port",
            destinationLabel: "Destination Port",
            intermediateLabel: "Intermediate Ports",
            algorithmLabel: "Optimization Algorithm",
            optimizationLabel: "Optimization Focus",
            constraintsLabel: "Route Constraints",
            calculateText: "Calculate Optimal Routes",
            loadingTitle: "Calculating Optimal Routes",
            loadingMessage: "Analyzing sea lanes and optimizing paths...",
            hintText: "Hold Ctrl/Cmd to select multiple ports",
            selectedPortsLabel: "Selected Ports:",
            legendTitle: "Map Legend",
            mapTitle: "Route Visualization",
            resultsTitle: "Route Analysis"
        }
    },

    // Constraints Configuration
    constraints: {
        maxTime: {
            label: "Maximum Time (days)",
            type: "number",
            min: 1,
            max: 365,
            step: 1,
            unit: "days",
            default: 30
        },
        maxFuel: {
            label: "Maximum Fuel (tonnes)",
            type: "number",
            min: 10,
            max: 10000,
            step: 10,
            unit: "tonnes",
            default: 1000
        },
        avoidAreas: {
            label: "Avoid Areas",
            type: "multiselect",
            options: ["Storm Areas", "High Piracy", "Environmental Zones", "Military Areas"],
            default: []
        },
        vesselType: {
            label: "Vessel Type",
            type: "select",
            options: ["Container Ship", "Tanker", "Bulk Carrier", "LNG Carrier", "General Cargo"],
            default: "Container Ship"
        }
    },

    // Default Settings
    defaults: {
        algorithm: "astar",
        optimization: "balanced",
        language: "en",
        theme: "dark",
        units: "metric"
    }
};

// Sample Dynamic Dataset
const SAMPLE_DATASET = {
    ports: [
        { name: "Shanghai", code: "CNSHA", country: "China", coordinates: [31.23, 121.47], type: "Deep Sea" },
        { name: "Singapore", code: "SGSIN", country: "Singapore", coordinates: [1.26, 103.82], type: "Hub" },
        { name: "Rotterdam", code: "NLRTM", country: "Netherlands", coordinates: [51.92, 4.48], type: "Deep Sea" },
        { name: "Dubai", code: "AEDXB", country: "UAE", coordinates: [25.27, 55.29], type: "Hub" },
        { name: "Los Angeles", code: "USLAX", country: "USA", coordinates: [33.72, -118.27], type: "Deep Sea" },
        { name: "Hamburg", code: "DEHAM", country: "Germany", coordinates: [53.55, 9.99], type: "Deep Sea" },
        { name: "Busan", code: "KRPUS", country: "South Korea", coordinates: [35.11, 129.04], type: "Deep Sea" },
        { name: "Jebel Ali", code: "AEJEA", country: "UAE", coordinates: [25.00, 55.07], type: "Hub" },
        { name: "Colombo", code: "LKCMB", country: "Sri Lanka", coordinates: [6.94, 79.84], type: "Hub" },
        { name: "Mumbai", code: "INBOM", country: "India", coordinates: [18.96, 72.82], type: "Deep Sea" },
        { name: "Shenzhen", code: "CNSNZ", country: "China", coordinates: [22.55, 114.12], type: "Deep Sea" },
        { name: "Antwerp", code: "BEANR", country: "Belgium", coordinates: [51.24, 4.40], type: "Deep Sea" },
        { name: "Hong Kong", code: "HKHKG", country: "Hong Kong", coordinates: [22.30, 114.17], type: "Hub" },
        { name: "New York", code: "USNYC", country: "USA", coordinates: [40.68, -74.03], type: "Deep Sea" },
        { name: "Felixstowe", code: "GBFXT", country: "UK", coordinates: [51.96, 1.35], type: "Deep Sea" },
        { name: "Tokyo", code: "JPTYO", country: "Japan", coordinates: [35.65, 139.76], type: "Deep Sea" },
        { name: "Sydney", code: "AUSYD", country: "Australia", coordinates: [-33.86, 151.21], type: "Deep Sea" },
        { name: "Santos", code: "BRSSZ", country: "Brazil", coordinates: [-23.96, -46.33], type: "Deep Sea" }
    ],

    routes: {
        predefined: [
            {
                name: "Trans-Pacific",
                start: "Shanghai",
                end: "Los Angeles",
                hubs: ["Tokyo", "Honolulu"],
                description: "Major Asia-US West Coast route"
            },
            {
                name: "Suez Route",
                start: "Shanghai",
                end: "Rotterdam",
                hubs: ["Singapore", "Jebel Ali", "Suez"],
                description: "Asia-Europe via Suez Canal"
            },
            {
                name: "Europe-Asia",
                start: "Rotterdam",
                end: "Singapore",
                hubs: ["Jebel Ali", "Colombo"],
                description: "Europe to Southeast Asia"
            }
        ]
    }
};

// Current Application State
let APP_STATE = {
    currentLanguage: DYNAMIC_CONFIG.defaults.language,
    currentTheme: DYNAMIC_CONFIG.defaults.theme,
    currentAlgorithm: DYNAMIC_CONFIG.defaults.algorithm,
    currentOptimization: DYNAMIC_CONFIG.defaults.optimization,
    userPreferences: {},
    loadedData: {},
    mapInstance: null,
    currentRoutes: null,
    selectedConstraints: {}
};

// Export for use in other files
window.DYNAMIC_CONFIG = DYNAMIC_CONFIG;
window.SAMPLE_DATASET = SAMPLE_DATASET;
window.APP_STATE = APP_STATE;