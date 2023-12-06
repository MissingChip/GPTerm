
import time

for i in range(10):
    for j in range(10):
        print(i, end='', flush=True)
        time.sleep(0.1)
    print('\r', end='')