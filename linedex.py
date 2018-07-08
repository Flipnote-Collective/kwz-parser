import numpy as np

with open("linedefs.bin", "rb") as f:
  linedefs = np.frombuffer(f.read(), dtype=np.uint8)
  linedefs = linedefs.reshape((-1, 2))
  linedefs = np.flip(linedefs, 1)
  with open("linedefs.new.bin", "wb") as f:
    f.write(linedefs.tobytes())