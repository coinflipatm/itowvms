from database import get_vehicles_by_status

vehicles = get_vehicles_by_status('New')
print("Vehicles with status 'New':")
for vehicle in vehicles:
    print(vehicle)