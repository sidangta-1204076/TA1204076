let map;
let markers = [];
let directionsService;
let directionsRenderer;

function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: -6.877339723542112, lng: 107.57650073777269 },
        zoom: 13,
    });

    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
        map: map,
    });

    map.addListener("click", function (event) {
        addMarker(event.latLng);
        const latLngStr = event.latLng.lat() + ", " + event.latLng.lng() + "\n";
        document.getElementById("locations").value += latLngStr;
    });
}

function addMarker(location) {
    const marker = new google.maps.Marker({
        position: location,
        label: String.fromCharCode(65 + markers.length),
        map: map,
    });
    markers.push(marker);
}

document.getElementById("vrp-form").addEventListener("submit", function (event) {
    event.preventDefault();
    const form = event.target;
    const locations = form.locations.value.trim().split("\n").map((line) => line.split(",").map(Number));
    const demands = form.demands.value.trim().split("\n").map(Number);
    const vehicle_count = 1;
    const vehicle_type = parseFloat(form.vehicle_type.value);

    // Clear any previous error messages
    document.getElementById("error-message").textContent = "";

    fetch("/solve", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            locations,
            demands,
            vehicle_count,
            vehicle_type,
        }),
    })
    .then((response) => response.json())
    .then((data) => {
        if (data.error) {
            displayError(data.error);
        } else {
            displayRoutes(data.routes, locations);
            displayDetails(data.route_details);
            displayEfficientRoute(data.routes);
        }
    });
});

function displayRoutes(routes, locations) {
    directionsRenderer.setDirections({ routes: [] }); // Clear previous routes

    // Clear existing markers
    markers.forEach(marker => marker.setMap(null));
    markers = [];

    routes.forEach((route) => {
        let waypoints = route.slice(1, -1).map((index) => ({
            location: new google.maps.LatLng(locations[index][0], locations[index][1]),
            stopover: true,
        }));

        let request = {
            origin: new google.maps.LatLng(locations[route[0]][0], locations[route[0]][1]),
            destination: new google.maps.LatLng(locations[route[route.length - 1]][0], locations[route[route.length - 1]][1]),
            waypoints: waypoints,
            travelMode: google.maps.TravelMode.DRIVING,
        };

        // Add markers based on the route
        route.forEach((index, i) => {
            addMarkerWithLabel(locations[index], i);
        });

        directionsService.route(request, function (result, status) {
            if (status == google.maps.DirectionsStatus.OK) {
                directionsRenderer.setDirections(result);
            }
        });
    });
}

function addMarkerWithLabel(location, labelIndex) {
    const marker = new google.maps.Marker({
        position: new google.maps.LatLng(location[0], location[1]),
        label: String.fromCharCode(65 + labelIndex),
        map: map,
    });
    markers.push(marker);
}

function displayDetails(details) {
    const detailsDiv = document.getElementById("details");
    let html = "<h2>Route Details</h2>";
    html += "<table>";
    html += "<tr><th>From</th><th>To</th><th>Distance (km)</th><th>Duration (minutes)</th><th>Fuel Consumption (liters)</th></tr>";
    let totalDuration = 0;
    let totalFuel = 0;
    let totalDistance = 0;
    details.forEach((detail) => {
        html += `<tr>
                 <td>${detail.from}</td>
                 <td>${detail.to}</td>
                 <td>${detail.distance.toFixed(2)}</td>
                 <td>${detail.duration.toFixed(2)}</td>
                 <td>${detail.fuel_consumption.toFixed(2)}</td>
               </tr>`;
        totalDuration += detail.duration;
        totalFuel += detail.fuel_consumption;
        totalDistance += detail.distance;
    });
    html += "</table>";
    html += `<h3><strong>Total Distance (km):</strong> ${totalDistance.toFixed(2)} KM</h3>`;
    html += `<h3><strong>Total Duration (minutes):</strong> ${totalDuration.toFixed(2)}</h3>`;
    html += `<h3><strong>Total Fuel Consumption (liters):</strong> ${totalFuel.toFixed(2)} L</h3>`;
    detailsDiv.innerHTML = html;
}


function displayEfficientRoute(routes) {
    const detailsDiv = document.getElementById("details");
    let html = "<h2>Efficient Route Sequence</h2>";
    routes.forEach((route, index) => {
        let routeStr = route.map(i => String.fromCharCode(65 + i)).join(" -> ");
        html += `<p>Vehicle ${index + 1}: ${routeStr}</p>`;
    });
    detailsDiv.innerHTML = html + detailsDiv.innerHTML;
}

function displayError(error) {
    const errorMessageDiv = document.getElementById("error-message");
    errorMessageDiv.textContent = "Waktu yang diperlukan melebihi jendela waktu yang diizinkan.";
}

// Load the Google Maps API script and initialize the map
document.addEventListener("DOMContentLoaded", initMap);
