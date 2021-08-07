import gamelib
import random
import math
import warnings
from sys import maxsize
import json

from strategies import *
import algo_strategy_Joseph
import algo_strategy_Viral

if __name__ == "__main__":
    algo = DefendDebugStrategy()
    algo.start()
