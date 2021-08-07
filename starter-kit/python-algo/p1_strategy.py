import gamelib
import random
import math
import warnings
from sys import maxsize
import json

from strategies import *
from algo_strategy_Joseph import *
from algo_strategy_Viral import *

if __name__ == "__main__":
    algo = AttackDebugStrategy()
    algo.start()
