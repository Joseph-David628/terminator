import os
import subprocess
import sys
import json

with open('game-configs.json',) as gc:
    game_config = json.load(gc)

# Runs a single game
def run_single_game(process_command):
    # Clear file
    file = open("logs.txt","r+")
    file.truncate(0)
    file.close()


    logs = open('logs.txt', 'a')
    p = subprocess.Popen(
        process_command,
        shell=True,
        stdout=logs,
        stderr=logs
        )
    # daemon necessary so game shuts down if this script is shut down by user
    p.daemon = 1
    p.wait()
    logs.close()

def prepare_results():
    with open('logs.txt') as logs:
        lines = logs.readlines()
    
    # Flag if algo crahed
    crashed = False
    for l in lines:
        if "Algo Crashed" in l:
            crashed = True
            break

    # Count scores for players
    p1_score = int(game_config["resources"]["startingHP"])
    p2_score = int(game_config["resources"]["startingHP"])
    for l in lines:
        if  "HIT!" in l:
            if "PLAYER 1" in l:
                p1_score -= 1
            if "PLAYER 2" in l:
                p2_score -= 1
    
    # Count number of total turns
    num_turns = 0
    for l in lines:
        if "Performing turn" in l:
            num_turns += 0.5 # Each algo moves once for turn so each turn is half a game turn

    return crashed, p1_score, p2_score, num_turns

if __name__ == "__main__":
    # Get location of this run file
    file_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.join(file_dir, os.pardir)
    parent_dir = os.path.abspath(parent_dir)

    # Get if running in windows OS
    is_windows = sys.platform.startswith('win')

    # Set algos
    algo1 = "\\python-algo\\run_p1.ps1" if is_windows else parent_dir + "/python-algo/run_p1.sh"
    algo2 = "\\python-algo\\run_p2.ps1" if is_windows else parent_dir + "/python-algo/run_p2.sh"
    print(parent_dir)
    # Run match
    print("Running Match...")
    run_single_game("cd {} && java -jar engine.jar work {} {}".format(parent_dir, algo1, algo2))

    # Prepare results
    crashed, p1_score, p2_score, num_turns = prepare_results()

    # Print results
    if crashed:
        print("Crashed. See logs.txt or replay for details.")
    else:
        print("Done.")
        print("Finished in {} turns".format(num_turns))
        print("P1: {} P2: {}".format(p1_score, p2_score))
