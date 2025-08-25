from datetime import time
import heapq
from pymongo import MongoClient
import pytz
from datetime import datetime

# Configuration for MongoDB and timezone
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "metro_db"
COLLECTION_NAME = "ban_stations"
TIMEZONE = pytz.timezone("Asia/Kolkata")

class Station:
    def __init__(self, name):
        self.name = name
        self.connections = {}  # A dictionary to hold connections to other stations
        self.schedule = {"first_train": time(5, 0), "last_train": time(23, 30)}  # Default schedule
        self.crowd_level = 3  # Default (1-5 scale)
        self.location = {"lat": 0.0, "lng": 0.0}

    def add_connection(self, station, time, cost, line):
        self.connections[station] = (time, cost, line)  # Add connection data (time, cost, and line)

class MetroSystem:
    def __init__(self):
        self.stations = {}  # A dictionary to hold all stations by name

    def add_station(self, name):
        if name not in self.stations:
            self.stations[name] = Station(name)

    def add_connection(self, station1, station2, time, cost, line):
        if station1 in self.stations and station2 in self.stations:
            self.stations[station1].add_connection(station2, time, cost, line)
            self.stations[station2].add_connection(station1, time, cost, line)

    def shortest_path(self, start, end, optimize="time", departure_time=None):
        """Find the shortest path between the start and end stations based on the selected optimization"""
        start=start.strip().title()
        end=end.strip().title()
        if start not in self.stations or end not in self.stations:
            raise ValueError(f"Station not found: {start} or {end}")

        queue = [(0, 0, 0, start, [], None)]  # (total_time, total_cost, total_crowd, current_station, path, current_line)
        visited = set()
        current_dt = departure_time or datetime.now(TIMEZONE)

        while queue:
            if optimize == "time":
                total_time, total_cost, total_crowd, current, path, current_line = heapq.heappop(queue)
            #elif optimize == "cost":
               # total_cost, total_time, total_crowd, current, path, current_line = heapq.heappop(queue)
            else:  # least_crowded
                total_crowd, total_time, total_cost, current, path, current_line = heapq.heappop(queue)

            if current in visited:
                continue

            visited.add(current)
            path = path + [(current, current_line)]

            if current == end:
                return {
                    "path": path,
                    "time": total_time,
                    "cost": total_cost,
                    "crowd_score": total_crowd / len(path),
                    "optimization": optimize
                }

            for neighbor, (time_, cost_, line) in self.stations[current].connections.items():
                if neighbor in visited:
                    continue

                # Check if the station is open at the current time
                station_schedule = self.stations[neighbor].schedule
                if not (station_schedule["first_train"] <= current_dt.time() <= station_schedule["last_train"]):
                    continue

                crowd = self.stations[neighbor].crowd_level
                line_change = line != current_line
                time_penalty = 5 if line_change else 0
                cost_penalty = 10 if line_change else 0

                # Push to queue with the updated values (6 values)
                heapq.heappush(queue, (
                    total_time + time_ + time_penalty, 
                    total_cost + cost_ ,
                    total_crowd + crowd,
                    neighbor,
                    path,
                    line
                ))

        return None  # Return None if no route is found

def load_data_from_mongodb():
    """Load metro station data from MongoDB"""
    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]
    metro = MetroSystem()

    for station_data in collection.find():
        station_name = station_data["name"].strip().title()
        metro.add_station(station_name)

        # Set station schedule, location, and crowd level
        station = metro.stations[station_name]
        if "schedule" in station_data:
            station.schedule = {
                "first_train": time(*map(int, station_data["schedule"]["first_train"].split(":"))),
                "last_train": time(*map(int, station_data["schedule"]["last_train"].split(":")))
            }
        if "location" in station_data:
            station.location = station_data["location"]
        if "crowd_level" in station_data:
            station.crowd_level = station_data["crowd_level"]

        # Add connections between stations
        for conn in station_data["connections"]:
            metro.add_station(conn["station"].strip().title())
            metro.add_connection(
                station_name,
                conn["station"].strip().title(),
                conn["time"],
                conn["cost"],
                conn["line"]
            )

    client.close()
    return metro