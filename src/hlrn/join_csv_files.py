import pandas as pd
import sys
import os

assert len(sys.argv) >= 4
assert os.path.exists(sys.argv[1])
assert os.path.exists(sys.argv[2])

a = pd.read_csv(sys.argv[1])
b = pd.read_csv(sys.argv[2])
c = a.append(b).drop_duplicates()
c.to_csv(sys.argv[3], index=False)

print("Merged %d from %s with %d from %s to %d in %s" % (len(a), sys.argv[1], len(b), sys.argv[2], len(c), sys.argv[3]))