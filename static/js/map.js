let map;
let markers = [];
let polygons = [];
let allColleges = [];
let allBoundaries = [];
let dataTable;

// Initialize the map
function initMap() {
    console.log('Initializing map...');
    try {
        map = L.map('map').setView([39.8283, -98.5795], 4); // Center of US
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: ' OpenStreetMap contributors'
        }).addTo(map);
        console.log('Map initialized successfully');
    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

// Initialize DataTable
function initDataTable(data) {
    if (dataTable) {
        dataTable.destroy();
    }
    
    dataTable = $('#collegeTable').DataTable({
        data: data,
        columns: [
            { data: 'NAME' },
            { data: 'ADDRESS' },
            { data: 'CITY' },
            { data: 'STATE' },
            { data: 'ZIP' },
            { data: 'TELEPHONE' },
            { data: 'POPULATION' },
            { data: 'COUNTY' },
            { data: 'COUNTYFIPS' },
            { 
                data: 'WEBSITE',
                render: function(data) {
                    return data ? `<a href="${data}" target="_blank">${data}</a>` : '';
                }
            },
            { data: 'income_bucket' },
            { data: 'population_bucket' }
        ],
        pageLength: 25,
        order: [[0, 'asc']], // Sort by name by default
        scrollX: true
    });
}

// Fetch all data and initialize filters
function initializeData() {
    console.log('Fetching data...');
    
    // Fetch colleges
    fetch('/get_colleges')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log(`Received ${data.length} colleges from server`);
            allColleges = data;
            
            // After getting colleges, fetch boundaries
            return fetch('/get_boundaries');
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log(`Received ${data.length} boundaries from server`);
            allBoundaries = data;
            
            // Update map after getting all data
            updateMap();
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

// Clear all map layers
function clearMapLayers() {
    // Clear markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    // Clear polygons
    polygons.forEach(polygon => map.removeLayer(polygon));
    polygons = [];
}

// Update markers and polygons based on current filters
function updateMap() {
    console.log('Updating map...');
    try {
        // Clear existing layers
        clearMapLayers();

        // Get selected filters
        const selectedIncome = Array.from(document.querySelectorAll('input[data-filter-type="income"]:checked'))
            .map(cb => cb.value);
        const selectedPopulation = Array.from(document.querySelectorAll('input[data-filter-type="population"]:checked'))
            .map(cb => cb.value);
        const showColleges = document.querySelector('input[data-filter-type="business"][value="colleges"]').checked;

        // Filter colleges based on selections
        const filteredColleges = allColleges.filter(college => 
            selectedIncome.includes(college.income_bucket) &&
            selectedPopulation.includes(college.population_bucket)
        );

        // Filter boundaries based on selections
        const filteredBoundaries = allBoundaries.filter(boundary => 
            selectedIncome.includes(boundary.income_bucket) &&
            selectedPopulation.includes(boundary.population_bucket)
        );

        console.log(`Displaying ${filteredColleges.length} colleges and ${filteredBoundaries.length} boundaries after filtering`);

        // Update table with filtered college data
        initDataTable(filteredColleges);

        // Add ZIP code polygons first (so they're underneath markers)
        filteredBoundaries.forEach(boundary => {
            if (boundary.geometry) {
                try {
                    const geojson = JSON.parse(boundary.geometry);
                    const polygon = L.geoJSON(geojson, {
                        style: {
                            fillColor: '#4a0080',  // Darker purple
                            fillOpacity: 0.35,     // Slightly increased opacity
                            color: '#4a0080',      // Matching color for consistency
                            weight: 0,
                            stroke: false
                        }
                    });
                    polygons.push(polygon);
                    polygon.addTo(map);
                } catch (e) {
                    console.error('Error adding polygon for ZIP:', boundary.zip_code, e);
                }
            }
        });

        // Add markers on top of polygons only if colleges should be shown
        if (showColleges) {
            filteredColleges.forEach(college => {
                if (college.latitude && college.longitude) {
                    const marker = L.marker([college.latitude, college.longitude])
                        .bindPopup(`
                            <strong>${college.NAME}</strong><br>
                            ${college.ADDRESS}<br>
                            ${college.CITY}, ${college.STATE} ${college.ZIP}<br>
                            Income Bucket: ${college.income_bucket}<br>
                            Population Bucket: ${college.population_bucket}
                        `);
                    markers.push(marker);
                    marker.addTo(map);
                }
            });
        }
    } catch (error) {
        console.error('Error updating map:', error);
    }
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing application...');
    initMap();
    initializeData();

    // Add event listeners to checkboxes
    document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateMap);
    });
});
