import os
from tqdm import tqdm
import subprocess
import time

for i in tqdm(range(100)):
    time.sleep(0.1)
    print(i)
