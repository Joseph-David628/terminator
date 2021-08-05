import gamelib
import random
import math
import warnings
from sys import maxsize
import json

from constants import *

"""
Build basic defenses using hardcoded locations.
Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
"""
def build_defences(game_state, units):
    # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
    # More community tools available at: https://terminal.c1games.com/rules#Download

    # Place turrets that attack enemy units
    turret_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
    # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
    game_state.attempt_spawn(units["TURRET"], turret_locations)
    
    # Place walls in front of turrets to soak up damage for them
    wall_locations = [[8, 12], [19, 12]]
    game_state.attempt_spawn(units["WALL"], wall_locations)
    # upgrade walls so they soak more damage
    game_state.attempt_upgrade(wall_locations)

"""
This function builds reactive defenses based on where the enemy scored on us from.
We can track where the opponent scored by looking at events in action frames 
as shown in the on_action_frame function
"""
def build_reactive_defense(game_state, units, scored_on_locations):
    for location in scored_on_locations:
        # Build turret one space above so that it doesn't block our own edge spawn locations
        build_location = [location[0], location[1]+1]
        game_state.attempt_spawn(units["TURRET"], build_location)

"""
Send out interceptors at random locations to defend our base from enemy moving units.
"""
def stall_with_interceptors(game_state, units, filter_blocked_locations):
    # We can spawn moving units on our edges so a list of all our edge locations
    friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
    
    # Remove locations that are blocked by our own structures 
    # since we can't deploy units there.
    deploy_locations = filter_blocked_locations(friendly_edges, game_state)
    
    # While we have remaining MP to spend lets send out interceptors randomly.
    while game_state.get_resource(MP) >= game_state.type_cost(units["INTERCEPTOR"])[MP] and len(deploy_locations) > 0:
        # Choose a random deploy location.
        deploy_index = random.randint(0, len(deploy_locations) - 1)
        deploy_location = deploy_locations[deploy_index]
        
        game_state.attempt_spawn(units["INTERCEPTOR"], deploy_location)
        # We don't have to remove the location since multiple mobile units can occupy the same space.

"""
Build a line of the cheapest stationary unit so our demolisher can attack from long range.
"""
def demolisher_line_strategy(game_state, units):
    # First let's figure out the cheapest unit
    # We could just check the game rules, but this demonstrates how to use the GameUnit class
    stationary_units = [units["WALL"], units["TURRET"], units["SUPPORT"]]
    cheapest_unit = units["WALL"]
    for unit in stationary_units:
        unit_class = gamelib.GameUnit(unit, game_state.config)
        if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
            cheapest_unit = unit

    # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
    # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
    for x in range(27, 5, -1):
        game_state.attempt_spawn(cheapest_unit, [x, 11])

    # Now spawn demolishers next to the line
    # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
    game_state.attempt_spawn(units["DEMOLISHER"], [24, 10], 1000)

"""
This function will help us guess which location is the safest to spawn moving units from.
It gets the path the unit will take then checks locations on that path to 
estimate the path's damage risk.
"""
def least_damage_spawn_location(game_state, units, location_options):
    damages = []
    # Get the damage estimate each path will take
    for location in location_options:
        path = game_state.find_path_to_edge(location)
        damage = 0
        for path_location in path:
            # Get number of enemy turrets that can attack each location and multiply by turret damage
            damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(units["TURRET"], game_state.config).damage_i
        damages.append(damage)
    
    # Now just return the location that takes the least damage
    return location_options[damages.index(min(damages))]

def detect_enemy_unit(game_state, unit_type=None, valid_x = None, valid_y = None):
    total_units = 0
    for location in game_state.game_map:
        if game_state.contains_stationary_unit(location):
            for unit in game_state.game_map[location]:
                if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                    total_units += 1
    return total_units
    
def filter_blocked_locations(locations, game_state):
    filtered = []
    for location in locations:
        if not game_state.contains_stationary_unit(location):
            filtered.append(location)
    return filtered