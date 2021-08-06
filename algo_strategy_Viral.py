import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import math


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips:

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical
  board states. Though, we recommended making a copy of the map to preserve
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        self.att_dir = {}
        self.def_dir = {}
        self.opp_edges = [[0,14], [1,15], [2,16], [3,17], [4,18], [5,19], [6,20], [7,21], [8,22], [9,23], [10,24], [11,25], [12,26], [13,27], [14,27], [15,26], [16,25], [17,24], [18,23], [19,22], [20,21], [21,20], [22,19], [23,18], [24,17], [25,16], [26,15], [27,14]]
        self.my_edges =  [[0,13], [1,12], [2,11], [3,10], [4,9], [5,8], [6,7], [7,6], [8,5], [9,4], [10,3], [11,2], [12,1], [13,0], [14,0], [15,1], [16,2], [17,3], [18,4], [19,5], [20,6], [21,7], [22,8], [23,9], [24,10], [25,11], [26,12], [27,13]]
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.hard_strat(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def hard_strat(self, game_state):
        turret_locs = [[13,9], [22,12], [5,12], [2,13], [25,13]]
        support_locs = [[21,7], [20,7], [19,7], [18,6], [17,6], [16,5],[16,4]]
        turret_locs2 = [[18,9], [9,9]]
        turret_locs3 = [[11,7], [3,11], [24,11]]
        support_locs2 = [[14,0], [13,0], [14,3], [13,3], [12,4], [11,5], [10,6], [9,6], [16,2], [15,1], [14,1], [13,1], [12,1], [11,2], [10,3], [9,4]]

        for l in turret_locs:
            if len(game_state.game_map[l]) == 0:
                if game_state.get_resource(0) >= 9:
                    game_state.attempt_spawn(TURRET, l)
                    game_state.attempt_upgrade(l)
            if game_state.get_resource(0) < 9:
                break

        for l in support_locs:
            if len(game_state.game_map[l]) == 0:
                if game_state.get_resource(0) >= 8:
                    game_state.attempt_spawn(SUPPORT, l)
            if game_state.get_resource(0) < 1:
                break


        for l in turret_locs2:
            if len(game_state.game_map[l]) == 0:
                if game_state.get_resource(0) >= 9:
                    game_state.attempt_spawn(TURRET, l)
                    game_state.attempt_upgrade(l)
            if game_state.get_resource(0) < 9:
                break

        for l in support_locs:
            if len(game_state.game_map[l]) != 0:
                if game_state.get_resource(0) >= 7:
                    game_state.attempt_upgrade(l)
            if game_state.get_resource(0) < 7:
                break

        for l in turret_locs3:
            if len(game_state.game_map[l]) == 0:
                if game_state.get_resource(0) >= 9:
                    game_state.attempt_spawn(TURRET, l)
                    game_state.attempt_upgrade(l)
            if game_state.get_resource(0) < 9:
                break

        for l in support_locs2:
            if len(game_state.game_map[l]) == 0:
                if game_state.get_resource(0) >= 8:
                    game_state.attempt_spawn(SUPPORT, l)
            if game_state.get_resource(0) < 1:
                break

        for l in support_locs2:
            if len(game_state.game_map[l]) != 0:
                if game_state.get_resource(0) >= 7:
                    game_state.attempt_upgrade(l)
            if game_state.get_resource(0) < 7:
                break

        self.att_dir = {}
        damages = [self.netProtect(game_state, edge) for edge in self.my_edges]

        SC_health = 15

        mattack = math.floor(game_state.get_resource(1)) - 1
        netDams = [mattack*(SC_health+a) - b for a,b in damages]
        gamelib.debug_write(netDams)

        if any(n > 0 for n in netDams):
            best_loc = self.my_edges[netDams.index(max(netDams))]
            game_state.attempt_spawn(SCOUT,best_loc,mattack)


    #given path, calculate shielding recieved PER UNIT
    def get_shielders(self, game_state, location_list, player_index = 0):


          if not player_index == 0 and not player_index == 1:
              self._invalid_player_index(player_index)

          attackers = []

          shieldT = 0

          checked_locs = []
          max_range = 0
          for unit in self.config["unitInformation"]:
              if unit.get('shieldRange', 0) >= max_range:
                  max_range = unit.get('shieldRange', 0)

          if location_list == None:
              return -10000
          gamelib.debug_write(len(location_list))
          for location in location_list:
              possible_locations= game_state.game_map.get_locations_in_range(location, max_range)
              for loc in possible_locations:
                  if loc in checked_locs:
                      possible_locations.remove(loc)
              for loc in possible_locations:
                  checked_locs.append(loc)
              for location_unit in possible_locations:
                  for unit in game_state.game_map[location_unit]:
                      if unit.player_index == player_index and game_state.game_map.distance_between_locations(location, location_unit) <= unit.shieldRange:
                          attackers.append(unit)
                          shieldT += unit.shieldPerUnit
          return shieldT

    #given path, estimate damage
    def least_damage_spawn_location(self, game_state, path):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take

        if path == None:
            return 100000

        damage = 0
        for path_location in path:
            # Get number of enemy turrets that can attack each location and multiply by turret damage
            if tuple(path_location) in self.att_dir:
                damage += sum([unit.damage_i for unit in game_state.get_attackers(path_location, 0)])
            else:
                temp = sum([unit.damage_i for unit in game_state.get_attackers(path_location, 0)])
                damage += temp
                self.att_dir[tuple(path_location)] = temp
        damages.append(damage)

        # Now just return the location that takes the least damage
        return damages[0]

    def netProtect(self, game_state, start):
        path = game_state.find_path_to_edge(start)
        defe = self.get_shielders(game_state, path)
        atk = self.least_damage_spawn_location(game_state, path)
        gamelib.debug_write("Calculating Optimal Attack Angle for", game_state.turn_number, start, atk, defe)
        return [defe,atk]

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
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


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
