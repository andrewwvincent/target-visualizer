let map;
let markers = [];
let polygons = [];
let allColleges = null;  // Changed to null to indicate not loaded
let allBoundaries = null;  // Changed to null to indicate not loaded
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
        data: data || [],  // Use empty array if no data
        columns: [
            { 
                data: 'NAME',
                defaultContent: ''
            },
            { 
                data: 'ADDRESS',
                defaultContent: ''
            },
            { 
                data: 'CITY',
                defaultContent: ''
            },
            { 
                data: 'STATE',
                defaultContent: ''
            },
            { 
                data: 'ZIP',
                defaultContent: ''
            },
            { 
                data: 'TELEPHONE',
                defaultContent: ''
            },
            { 
                data: 'POPULATION',
                defaultContent: ''
            },
            { 
                data: 'COUNTY',
                defaultContent: ''
            },
            { 
                data: 'COUNTYFIPS',
                defaultContent: ''
            },
            { 
                data: 'WEBSITE',
                defaultContent: '',
                render: function(data) {
                    return data ? `<a href="${data}" target="_blank">${data}</a>` : '';
                }
            },
            { 
                data: 'income_bucket',
                defaultContent: ''
            },
            { 
                data: 'population_bucket',
                defaultContent: ''
            }
        ],
        pageLength: 25,
        order: [[0, 'asc']], // Sort by name by default
        scrollX: true
    });
}

// Fetch data based on current filters
async function fetchFilteredData() {
    const selectedIncome = Array.from(document.querySelectorAll('input[data-filter-type="income"]:checked'))
        .map(cb => cb.value);
    const selectedPopulation = Array.from(document.querySelectorAll('input[data-filter-type="population"]:checked'))
        .map(cb => cb.value);
    const showColleges = document.querySelector('input[data-filter-type="business"][value="colleges"]').checked;

    try {
        // Only fetch colleges if they haven't been fetched and are needed
        if (showColleges && allColleges === null && (selectedIncome.length > 0 && selectedPopulation.length > 0)) {
            console.log('Fetching colleges...');
            const response = await fetch('/get_colleges');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            allColleges = await response.json();
            console.log(`Received ${allColleges.length} colleges from server`);
        }

        // Only fetch boundaries if they haven't been fetched and filters are selected
        if (allBoundaries === null && (selectedIncome.length > 0 && selectedPopulation.length > 0)) {
            console.log('Fetching boundaries...');
            const response = await fetch('/get_boundaries');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            allBoundaries = await response.json();
            console.log(`Received ${allBoundaries.length} boundaries from server`);
        }

        updateMap();
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Clear all map layers
function clearMapLayers() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    polygons.forEach(polygon => map.removeLayer(polygon));
    polygons = [];
}

// Update markers and polygons based on current filters
function updateMap() {
    console.log('Updating map...');
    try {
        clearMapLayers();

        const selectedIncome = Array.from(document.querySelectorAll('input[data-filter-type="income"]:checked'))
            .map(cb => cb.value);
        const selectedPopulation = Array.from(document.querySelectorAll('input[data-filter-type="population"]:checked'))
            .map(cb => cb.value);
        const showColleges = document.querySelector('input[data-filter-type="business"][value="colleges"]').checked;

        // Only process data if we have selections
        if (selectedIncome.length === 0 || selectedPopulation.length === 0) {
            initDataTable([]); // Clear the table
            return; // Exit early if no filters selected
        }

        // Filter colleges if we have them
        const filteredColleges = allColleges ? allColleges.filter(college => 
            selectedIncome.includes(college.income_bucket) &&
            selectedPopulation.includes(college.population_bucket)
        ) : [];

        // Filter boundaries if we have them
        const filteredBoundaries = allBoundaries ? allBoundaries.filter(boundary => 
            selectedIncome.includes(boundary.income_bucket) &&
            selectedPopulation.includes(boundary.population_bucket)
        ) : [];

        console.log(`Displaying ${filteredColleges.length} colleges and ${filteredBoundaries.length} boundaries after filtering`);

        // Update table with filtered college data
        initDataTable(filteredColleges);

        // Add ZIP code polygons
        if (filteredBoundaries.length > 0) {
            filteredBoundaries.forEach(boundary => {
                if (boundary.geometry) {
                    try {
                        const geojson = JSON.parse(boundary.geometry);
                        const polygon = L.geoJSON(geojson, {
                            style: {
                                fillColor: '#4a0080',
                                fillOpacity: 0.35,
                                color: '#4a0080',
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
        }

        // Add college markers if needed
        if (showColleges && filteredColleges.length > 0) {
            filteredColleges.forEach(college => {
                if (college.latitude && college.longitude) {
                    const marker = L.marker([college.latitude, college.longitude])
                        .bindPopup(`
                            <strong>${college.NAME}</strong><br>
                            ${college.ADDRESS || ''}<br>
                            ${college.CITY || ''}, ${college.STATE || ''} ${college.ZIP || ''}<br>
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
    initDataTable([]); // Initialize with empty data

    // Add event listeners to checkboxes
    document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', fetchFilteredData);
    });
});
