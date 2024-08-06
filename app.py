from flask import Flask, request, render_template, jsonify
import pandas as pd
import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import googlemaps
import time

app = Flask(__name__)

# Google Maps API Key
gmaps = googlemaps.Client(key='AIzaSyCZl9iLwCzdDxjHPIuMX0MdzZQIfHglgfA')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/solve', methods=['GET', 'POST'])
def solve_page():
    if request.method == 'GET':
        return render_template('solve.html')
    else:
        data = request.get_json()
        locations = data['locations']
        demands = data['demands']
        vehicle_count = 1
        vehicle_type = data['vehicle_type']
        depot = 0  # Starting point index

        # Ensure demands are within limits based on vehicle type
        max_demand = 10 if vehicle_type in [58.5, 62] else 15
        if any(d > max_demand for d in demands):
            return jsonify({'error': 'Demand exceeds vehicle capacity.'}), 400

        # Convert locations to a DataFrame
        df = pd.DataFrame(locations, columns=['latitude', 'longitude'])

        # Determine avoid parameter based on vehicle type
        avoid = None
        if vehicle_type in [58.5, 62]:  # Motor types
            avoid = "tolls"

        # Compute the distance and time matrices using Google Maps API
        distance_matrix, time_matrix = compute_distance_matrix(df, avoid)

        # Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(len(distance_matrix), vehicle_count, depot)

        # Create Routing Model
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node])

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)

        # Define cost of each arc
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add Capacity constraint
        def demand_callback(from_index):
            """Returns the demand of the node."""
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [max_demand] * vehicle_count,  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity')

        # Setting first solution heuristic
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

        # Solve the problem
        solution = routing.SolveWithParameters(search_parameters)

        # Get routes and details
        routes, route_details = get_routes_and_details(manager, routing, solution, vehicle_count, distance_matrix, time_matrix, vehicle_type)

        return jsonify({'route_details': route_details, 'routes': routes, 'vehicle_type': vehicle_type})

def compute_distance_matrix(df, avoid):
    distance_matrix = np.zeros((len(df), len(df)))
    time_matrix = np.zeros((len(df), len(df)))
    current_time = int(time.time())
    for i, (lat1, lon1) in enumerate(df.values):
        for j, (lat2, lon2) in enumerate(df.values):
            if i != j:
                directions = gmaps.directions(
                    (lat1, lon1), (lat2, lon2),
                    mode="driving",
                    departure_time=current_time,
                    avoid=avoid
                )
                distance_matrix[i][j] = directions[0]['legs'][0]['distance']['value']
                time_matrix[i][j] = directions[0]['legs'][0]['duration_in_traffic']['value']
    return distance_matrix, time_matrix

def index_to_label(index):
    return chr(ord('A') + index)

def get_routes_and_details(manager, routing, solution, vehicle_count, distance_matrix, time_matrix, vehicle_type):
    routes = []
    route_details = []
    for vehicle_id in range(vehicle_count):
        index = routing.Start(vehicle_id)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        # Ensure the vehicle returns to the depot
        if route[-1] != route[0]:
            route.append(manager.IndexToNode(routing.Start(vehicle_id)))
        if len(route) > 1:
            routes.append(route)

        # Collect route details
        for i in range(len(route) - 1):  # Include return to depot
            from_node = route[i]
            to_node = route[i + 1]
            distance = distance_matrix[from_node][to_node] / 1000  # Convert to km
            duration = time_matrix[from_node][to_node] / 60  # Convert to minutes
            fuel_consumption = distance / vehicle_type  # Fuel consumption in liters
            # Skip the last entry if it's the return to depot with zero values
            if distance > 0 or duration > 0:
                route_details.append({
                    'from': index_to_label(from_node),
                    'to': index_to_label(to_node),
                    'distance': distance,
                    'duration': duration,
                    'fuel_consumption': fuel_consumption
                })
    return routes, route_details

if __name__ == '__main__':
    app.run(debug=True)
