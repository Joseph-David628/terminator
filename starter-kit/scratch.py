"""
x = 1

for i in range(1, 100):
    x = 0.75 * x
    x += i // 5 + 1
    print(i, x)
"""

import statistics

w = [[12, 4], [23, 54], [12, 54]]
w_x = [x for x, y in w]
print(statistics.median(w_x))