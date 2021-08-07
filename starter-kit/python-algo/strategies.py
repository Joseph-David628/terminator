import gamelib
import random
import statistics
import math
import warnings
from sys import maxsize
import json

from constants import *
from actions import *

""" This strategy does nothing and is just to debug """
class EmptyStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        print(game_state)
        print(type(game_state))

        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        return

""" Default strategy provided with starter kit """
class DefaultStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

        # List of locations scored on
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.
        
        # Strategy
        self.starter_strategy(game_state)

        game_state.submit_turn()
    
    # Default starter strategy
    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        build_defences(game_state, self.units)
        # Now build reactive defenses based on where the enemy scored
        build_reactive_defense(game_state, self.units, self.scored_on_locations)

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        if game_state.turn_number < 5:
            stall_with_interceptors(game_state, self.units, filter_blocked_locations)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our demolishers to attack them at long range.
            if detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                demolisher_line_strategy(game_state, self.units)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Scouts there.

                # Only spawn Scouts every other turn
                # Sending more at once is better since attacks can only hit a single scout at a time
                if game_state.turn_number % 2 == 1:
                    # To simplify we will just check sending them from back left and right
                    scout_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = least_damage_spawn_location(game_state, self.units, scout_spawn_location_options)
                    game_state.attempt_spawn(self.units["SCOUT"], best_location, 1000)

                # Lastly, if we have spare SP, let's build some supports
                support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                game_state.attempt_spawn(self.units["SUPPORT"], support_locations)

    def on_action_frame(self, turn_string):
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


""" Strategy using V shaped defense and agents sent accross the edge """
class V1Strategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

        self.scored_on_locations = []
        self.prev_my_health = 0
        self.prev_enemy_health = 0
        self.consecutive_blocked = 0 # Number of consecutive attacks blocked


    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True) # Comment or remove this line to enable warnings.
        
        num_stationary_spawned = 0
        support_upgrade_ready = False

        # Update stats
        my_health_change = 0
        enemy_health_change = 0
        if self.prev_my_health > 0 and self.prev_enemy_health > 0:
            my_health_change = game_state.my_health - self.prev_my_health
            enemy_health_change = game_state.enemy_health - self.prev_enemy_health
        self.prev_my_health = game_state.my_health
        self.prev_enemy_health = game_state.enemy_health

        if enemy_health_change == 0:
            self.consecutive_blocked += 1
        else:
            self.consecutive_blocked = 0

        # Update defense in stages (as long as nothing spawned in earlier stages, keep attempting highr stage spawns)

        # Stage 1
        if num_stationary_spawned == 0:
            turret_locations_1 = [[3, 12], [6, 9], [9, 6], [12, 3], [15, 3], [18, 6], [21, 9], [24, 12]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["TURRET"], turret_locations_1)

        # Stage 2
        if num_stationary_spawned == 0:
            support_locations_1 = [[13, 2], [14, 2], [13, 3], [14, 3]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["SUPPORT"], support_locations_1)

        # Stage 3
        if num_stationary_spawned == 0:
            turret_upgrade_locations_1 = [[3, 12], [24, 12]]
            num_stationary_spawned += game_state.attempt_upgrade(turret_upgrade_locations_1)

        # Stage 4
        if num_stationary_spawned == 0:
            support_upgrade_ready = True
            support_upgrade_locations_1 = [[13, 2], [14, 2]]
            num_stationary_spawned += game_state.attempt_upgrade(support_upgrade_locations_1)
        
        # Stage 5
        # Fill in the v wall gaps

        # Stage 6
        # Extra reinforcements

        # Update offense

        # Launch scouts until n rounds of consecutive attacks are blocked
        if self.consecutive_blocked < 3:
            game_state.attempt_spawn(self.units["SCOUT"], [[14, 0]], 5)
        else:
            game_state.attempt_spawn(self.units["DEMOLISHER"], [[14, 0]], 5)
            # Save to launch batch of demolishers


        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        return



""" Strategy using V shaped defense and agents sent accross the edge """
class V2Strategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

        self.scored_on_locations = []
        self.prev_my_health = 0
        self.prev_enemy_health = 0
        self.consecutive_blocked = 0 # Number of consecutive attacks blocked

        # Side to launch attacks from (left = -1, right = 1)
        self.attack_side = -1


    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True) # Comment or remove this line to enable warnings.
        
        num_stationary_spawned = 0
        support_upgrade_ready = False

        # Update stats
        my_health_change = 0
        enemy_health_change = 0
        if self.prev_my_health > 0 and self.prev_enemy_health > 0:
            my_health_change = game_state.my_health - self.prev_my_health
            enemy_health_change = game_state.enemy_health - self.prev_enemy_health
        self.prev_my_health = game_state.my_health
        self.prev_enemy_health = game_state.enemy_health

        # Update defense in stages (as long as nothing spawned in earlier stages, keep attempting highr stage spawns)

        # Sparse V turrets
        if game_state.get_resource(SP) > 0:
            turret_locations_1 = [[3, 12], [6, 9], [9, 6], [12, 3], [15, 3], [18, 6], [21, 9], [24, 12]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["TURRET"], turret_locations_1)

        # Support in back
        if game_state.get_resource(SP) > 0:
            support_locations_1 = [[13, 2], [14, 2], [13, 3], [14, 3]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["SUPPORT"], support_locations_1)

        # Edge turret upgrade
        if game_state.get_resource(SP) > 0:
            turret_upgrade_locations_1 = [[3, 12], [24, 12]]
            num_stationary_spawned += game_state.attempt_upgrade(turret_upgrade_locations_1)

        # Support upgrade
        if game_state.get_resource(SP) > 0:
            support_upgrade_ready = True
            support_upgrade_locations_1 = [[13, 2], [14, 2], [13, 3], [14, 3]]
            num_stationary_spawned += game_state.attempt_upgrade(support_upgrade_locations_1)
        
        # Add edge turrets
        if game_state.get_resource(SP) > 0:
            turret_locations_2 = [[3, 13], [6, 13], [21, 13], [24, 13]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["TURRET"], turret_locations_2)
            turret_locations_2 = [[3, 13], [6, 13], [21, 13], [24, 13]]
            num_stationary_spawned += game_state.attempt_upgrade(turret_locations_2)
        
        # Full wall
        if False and game_state.get_resource(SP) > 0:
            wall_locations_1 = [[4, 11], [5, 10], [7, 8], [8, 7], [10, 5], [11, 4], [13, 2], [14, 10], [16, 2], [17, 10],  [19, 5], [20, 4], [22, 8], [23, 7], [25, 11], [26, 10]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["WALL"], wall_locations_1)

        # Close side with turrets
        if game_state.get_resource(SP) > 0:
            turret_locations_2 = [[25, 13], [26, 13], [25, 12], [25, 12]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["TURRET"], turret_locations_2)
            num_stationary_spawned += game_state.attempt_upgrade(turret_locations_2)

        # Support on sides
        if game_state.get_resource(SP) > 0:
            support_locations_2 = [[5, 11], [6, 10], [7, 9], [8, 8], [9, 7], [10, 6], [11, 5]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["SUPPORT"], support_locations_2)
            num_stationary_spawned += game_state.attempt_upgrade(support_locations_2)

        # Update offense

        # Launch scouts until n rounds of consecutive attacks are blocked
        launched_attacked = False
        if self.consecutive_blocked < 2:
            launched_attacked = True
            game_state.attempt_spawn(self.units["SCOUT"], [[14, 0]], 5)
        else:
            # Save enough for n demolishers
            if game_state.get_resource(MP) > 3 * gamelib.GameUnit(self.units["DEMOLISHER"], game_state.config).cost[game_state.MP]:
                launched_attacked = True
                game_state.attempt_spawn(self.units["DEMOLISHER"], [[14, 0]], 5)

        # Increment blocked before launching
        if launched_attacked and enemy_health_change == 0:
            self.consecutive_blocked += 1
        else:
            self.consecutive_blocked = 0


        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        return


""" Strategy using V shaped defense and agents sent accross the edge """
class Y1Strategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

        self.scored_on_locations = []
        self.prev_my_health = 0
        self.prev_enemy_health = 0
        self.consecutive_blocked = 0 # Number of consecutive attacks blocked

        # Side to launch attacks from (left = -1, right = 1)
        self.attack_side = -1

    def run_deploy_stage(self, game_state, unit_type, locations):
        game_state.attempt_spawn(unit_type, locations)
        return all(units_deployed_locations(game_state, unit_type, locations))
    
    def run_upgrade_stage(self, game_state, unit_type, locations):
        game_state.attempt_upgrade(locations)
        return all(units_upgraded_locations(game_state, unit_type, locations))
    
    def run_deploy_upgraded_stage(self, game_state, unit_type, locations):
        for location in locations:
            completed = self.run_deploy_stage(game_state, unit_type, [location])
            completed = self.run_upgrade_stage(game_state, unit_type, [location])
            if not completed: return False
        return all(units_deployed_locations(game_state, unit_type, locations)) and all(units_upgraded_locations(game_state, unit_type, locations))

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True) # Comment or remove this line to enable warnings.
        gamelib.debug_write("...")
        # Key locations
        edge_turret_locations_1 = [[2, 13], [25, 13], [3, 13],  [24, 13], [6, 13], [21, 13]]
        edge_turret_locations_2 = [[3, 12], [25, 12], [4, 13], [23, 13]]

        wall_locations_1 = [[15, 12], [9, 12], [24, 12]]
        wall_locations_2 = [[12, 12], [18, 12], [6, 12], [21, 12]]
        wall_locations_3 = [[3, 13], [4, 13], [5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13], [11, 13], [12, 13], [13, 13],
                                [14, 13], [15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13], [23, 13], [24, 13], [25, 13], [26, 13], [27, 13]]
        wall_locations_3.reverse()
        wall_locations_4 = [[12, 12], [18, 12], [6, 12], [21, 12]]

        back_support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        support_line_locations_1 = [[4, 12], [5, 11], [6, 10], [7, 9], [8, 8], [9, 7], [10, 6], [11, 5], [12, 4], [13, 3], [14, 2], [15, 1]]
        support_line_locations_1.reverse()

        # Update defense in stages (as long as nothing spawned in earlier stages, keep attempting highr stage spawns)
        # TODO - break up stages so deploy and upgrade happen togethor, big launch could be a one hit done - avert detection, need to think about smart fire timing strategy
        completed_stage = True

        # Supports in back
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_stage(game_state, self.units["SUPPORT"], back_support_locations)

        # Side turret defense + upgrade
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], edge_turret_locations_1)
        
        # Wall L1
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], wall_locations_1)

        # Support line (block right)
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_stage(game_state, self.units["SUPPORT"], support_line_locations_1)

        # Wall L1
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], wall_locations_2)

        # Upgrade support line
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_upgrade_stage(game_state, self.units["SUPPORT"], back_support_locations)
        
        # Wall L3
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["WALL"], wall_locations_3)

        # Upgrade support line
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_upgrade_stage(game_state, self.units["SUPPORT"], support_line_locations_1)

        """
        # Support in back
        if game_state.get_resource(SP) > 0:
            support_locations_1 = [[13, 2], [14, 2], [13, 3], [14, 3]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["SUPPORT"], support_locations_1)

        # Add edge turrets
        if game_state.get_resource(SP) > 0:
            turret_locations_2 = [[3, 13], [6, 13], [21, 13], [24, 13]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["TURRET"], turret_locations_2)
            turret_locations_2 = [[3, 13], [6, 13], [21, 13], [24, 13]]
            num_stationary_spawned += game_state.attempt_upgrade(turret_locations_2)

        # Support upgrade
        if game_state.get_resource(SP) > 0:
            support_upgrade_ready = True
            support_upgrade_locations_1 = [[13, 2], [14, 2], [13, 3], [14, 3]]
            num_stationary_spawned += game_state.attempt_upgrade(support_upgrade_locations_1)

        # BUILD THE WALL
        if game_state.get_resource(SP) > 0:
            wall_locations_1 = [[6, 13], [9, 13], [12, 13], [15, 13], [18, 13], [21, 13], [24, 13]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["TURRET"], wall_locations_1)
            num_stationary_spawned += game_state.attempt_upgrade(wall_locations_1)

        # Support on sides
        if game_state.get_resource(SP) > 0:
            support_locations_2 = [[4, 12], [5, 11], [6, 10], [7, 9], [8, 8], [9, 7], [10, 6], [11, 5], [12, 4]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["SUPPORT"], support_locations_2)
            #num_stationary_spawned += game_state.attempt_upgrade(support_locations_2)

        if game_state.get_resource(SP) > 0:
            wall_locations_1 = [[7, 12], [8, 12], [10, 12], [11, 12], [13, 12], [14, 12], [16, 12], [17, 12]]
            num_stationary_spawned += game_state.attempt_spawn(self.units["TURRET"], wall_locations_1)
            num_stationary_spawned += game_state.attempt_upgrade(wall_locations_1)
        """
        # Update offense

        # Launch scouts until n rounds of consecutive attacks are blocked
        if game_state.turn_number < 5 or (game_state.turn_number < 10 and game_state.turn_number % 2 == 0) or game_state.turn_number % 5 == 0:        
            if game_state.get_resource(MP) < 2:
                game_state.attempt_spawn(self.units["SCOUT"], [[14, 0]], int(game_state.get_resource(MP)))
            else:
                game_state.attempt_spawn(self.units["SCOUT"], [[14, 0]], int(game_state.get_resource(MP) // 2))
                game_state.attempt_spawn(self.units["SCOUT"], [[12, 1]], int(game_state.get_resource(MP) // 2))


        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        return


""" Attack Debug """
class AttackDebugStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

        self.scored_on_locations = []
        self.prev_my_health = 0
        self.prev_enemy_health = 0
        self.consecutive_blocked = 0 # Number of consecutive attacks blocked

        # Side to launch attacks from (left = -1, right = 1)
        self.attack_side = -1

    def run_deploy_stage(self, game_state, unit_type, locations):
        game_state.attempt_spawn(unit_type, locations)
        return all(units_deployed_locations(game_state, unit_type, locations))
    
    def run_upgrade_stage(self, game_state, unit_type, locations):
        game_state.attempt_upgrade(locations)
        return all(units_upgraded_locations(game_state, unit_type, locations))
    
    def run_deploy_upgraded_stage(self, game_state, unit_type, locations):
        for location in locations:
            completed = self.run_deploy_stage(game_state, unit_type, [location])
            completed = self.run_upgrade_stage(game_state, unit_type, [location])
            if not completed: return False
        return all(units_deployed_locations(game_state, unit_type, locations)) and all(units_upgraded_locations(game_state, unit_type, locations))

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True) # Comment or remove this line to enable warnings.

        # Key locations
        s1 = [[3, 12], [4, 11], [5, 10], [6, 9], [7, 8], [8, 7], [9, 6], [10, 5], [11, 4], [12, 3], [13, 2]]
        s2 = [[24, 12], [23, 11], [22, 10], [21, 9], [20, 8], [19, 7], [18, 6], [17, 5], [16, 4], [15, 3], [14, 2]]
        s3 = [[2, 12], [25, 13]]

        self.run_deploy_upgraded_stage(game_state, self.units["SUPPORT"], s1+s2+s3)
        #self.run_deploy_stage(game_state, self.units["SUPPORT"], s2)
        if game_state.turn_number > 80:
            game_state.attempt_spawn(self.units["SCOUT"], [[18, 4]], 15)
            game_state.attempt_spawn(self.units["SCOUT"], [[8, 5]], 10)
            game_state.attempt_spawn(self.units["SCOUT"], [[3, 10]], 30)

        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        return


""" Defend Debug """
class DefendDebugStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

        self.scored_on_locations = []
        self.prev_my_health = 0
        self.prev_enemy_health = 0
        self.consecutive_blocked = 0 # Number of consecutive attacks blocked

        # Side to launch attacks from (left = -1, right = 1)
        self.attack_side = -1

    def run_deploy_stage(self, game_state, unit_type, locations):
        game_state.attempt_spawn(unit_type, locations)
        return all(units_deployed_locations(game_state, unit_type, locations))
    
    def run_upgrade_stage(self, game_state, unit_type, locations):
        game_state.attempt_upgrade(locations)
        return all(units_upgraded_locations(game_state, unit_type, locations))
    
    def run_deploy_upgraded_stage(self, game_state, unit_type, locations):
        for location in locations:
            completed = self.run_deploy_stage(game_state, unit_type, [location])
            completed = self.run_upgrade_stage(game_state, unit_type, [location])
            if not completed: return False
        return all(units_deployed_locations(game_state, unit_type, locations)) and all(units_upgraded_locations(game_state, unit_type, locations))

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True) # Comment or remove this line to enable warnings.

        # Key locations
        w1 = [[0, 13], [1, 13], [2, 13], [3, 13], [4, 13]]
        t1 = [[1, 12], [2, 12], [3, 12], [4, 12]]
        t2 = [[2, 11], [3, 11], [4, 11]]
        t3 = [[3, 10], [4, 10]]

        w1 = [[2, 13], [3, 13], [4, 13]]
        t1 = [[1, 12], [3, 12]]
        t2 = [[2, 11], [4, 11]]
        t3 = [[3, 10], [4, 10]]

        self.run_deploy_upgraded_stage(game_state, self.units["WALL"], w1)
        self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], t1)

        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        return

""" Build the wall """
class WallStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        # Initial setup
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        self.units = {
            "WALL": config["unitInformation"][0]["shorthand"],
            "SUPPORT": config["unitInformation"][1]["shorthand"],
            "TURRET": config["unitInformation"][2]["shorthand"],
            "SCOUT": config["unitInformation"][3]["shorthand"],
            "DEMOLISHER": config["unitInformation"][4]["shorthand"],
            "INTERCEPTOR": config["unitInformation"][5]["shorthand"],
        }

        self.primary_wall_built = False
        self.weak_locations = []
        self.adapted_defense_locations = []

    def run_deploy_stage(self, game_state, unit_type, locations):
        game_state.attempt_spawn(unit_type, locations)
        return all(units_deployed_locations(game_state, unit_type, locations))
    
    def run_upgrade_stage(self, game_state, unit_type, locations):
        game_state.attempt_upgrade(locations)
        return all(units_upgraded_locations(game_state, unit_type, locations))
    
    def remove_damaged_units(self, game_state, unit_type, locations):
        need_repair = units_repair_locations(game_state, unit_type, locations, critical_health=0.5)
        repair_locations = [l for (l, r) in zip(locations, need_repair) if r]
        self.weak_locations += repair_locations

        if len(repair_locations) > 0: game_state.attempt_remove(repair_locations)
    
    def run_deploy_upgraded_stage(self, game_state, unit_type, locations, repair=True):
        if repair:
            self.remove_damaged_units(game_state, unit_type, locations)

        for location in locations:
            completed = self.run_deploy_stage(game_state, unit_type, [location])
            completed = self.run_upgrade_stage(game_state, unit_type, [location])
            if not completed: return False
        return all(units_deployed_locations(game_state, unit_type, locations)) and all(units_upgraded_locations(game_state, unit_type, locations))

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True) # Comment or remove this line to enable warnings.

        # Key locations
        core_turret_locations_1 = [[3, 12], [24, 12]]
        core_turret_locations_2 = [[8, 12], [19, 12]]
        core_turret_locations_3 = [[12, 12], [15, 12]]

        edge_turret_locations_1 = [[1, 12], [26, 12]]
        edge_turret_locations_2 = [[2, 12], [25, 12]]

        center_turret_locations_1 = [[13, 12], [14, 12]]

        primary_wall_locations_1 = [[0, 13], [27, 13]] + [[1, 13], [26, 13]] + [[2, 13], [25, 13]]
        primary_wall_locations_2 = [[3, 13], [24, 13]] + [[4, 13], [23, 13]] + [[5, 13], [22, 13]]
        primary_wall_locations_3 = [[6, 13], [21, 13]] + [[7, 13], [20, 13]] + [[8, 13], [19, 13]]
        primary_wall_locations_4 = [[9, 13], [18, 13]] + [[10, 13], [17, 13]] + [[11, 13], [16, 13]]
        primary_wall_locations_5 = [[12, 13], [15, 13]]
        primary_wall_locations_6 = [[13, 12], [14, 12]]

        # Update defense in stages (as long as nothing spawned in earlier stages, keep attempting highr stage spawns)
        completed_stage = True

        # Core turret defense + upgrade
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], core_turret_locations_1, repair=False)

        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], core_turret_locations_2, repair=False)

        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], core_turret_locations_3, repair=False)

        # Primary wall + upgrade
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["WALL"], primary_wall_locations_1)

        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["WALL"], primary_wall_locations_2)

        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["WALL"], primary_wall_locations_3)
        
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["WALL"], primary_wall_locations_4)
        
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["WALL"], primary_wall_locations_5)
        
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["WALL"], primary_wall_locations_6)
        
        if completed_stage:
            self.primary_wall_built = True

        # Adaptive shielding
        if self.primary_wall_built and len(self.weak_locations) > 0 and game_state.get_resource(SP) > 0:
            weak_x = [x for x, y in self.weak_locations]
            max_critical_defense_location = [int(statistics.median(weak_x)), 11]
            self.weak_locations = []
            self.adapted_defense_locations.append(max_critical_defense_location)
            
        # Adapted turrets + upgrade
        if len(self.adapted_defense_locations) > 0 and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], self.adapted_defense_locations, repair=False)

        # Edge turret + upgrade
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], edge_turret_locations_1)

        # Edge turret + upgrade
        if completed_stage and game_state.get_resource(SP) > 0:
            completed_stage = self.run_deploy_upgraded_stage(game_state, self.units["TURRET"], edge_turret_locations_2)


        if game_state.my_health < 10:
            game_state.attempt_spawn(self.units["SCOUT"], [[13, 0]], 1000)

        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        return