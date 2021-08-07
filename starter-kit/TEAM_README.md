# Team Documentation

### How to run

* Move run_match.py in the scripts dir
* Move everything else to the python-algo dir
* Import and initialize the algos to run in p1_strategy.py and p2_strategy.py
* run the command scripts/run_match_2.py - running so will output the number of turns taken, scores, and save the replay in the replays dir

### Changes

None of the original scripts were modified, but new scripts were added to make running matches between different algos and recording the results easier. These are the key additions...
* All strategies are in the python-algo/strategies.py file for convenience.
* The particular actions they take are in the python-algo/actions.py file so that an action can easily be plugged in and out of multiple strategies. (Because of this, some actions from the default strategies were modified so they accept what were originally class vars as params.)
* Instead of a single python-algo/run.sh, two additional files python-algo/run_p1.sh and python-algo/run_p2.sh and corresponding python-algo/p1_strategy.py and python-algo/p2_strategy.py were created so different custom strategies can be played against each other.
* The new run_match.py ... doesn't take any params and saves the replay in the replays dir and outputs logs in the logs.txt file.