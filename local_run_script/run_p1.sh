#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
${PYTHON_CMD:-python3} -u "$DIR/p1_strategy.py"