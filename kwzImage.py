from sys import argv
from kwz import KWZParser
from PIL import Image
import numpy as np

with open(argv[1], "rb") as kwz:
  with open("comptable1.bin", "rb") as f: table1 = f.read()
  with open("comptable2.bin", "rb") as f: table2 = f.read()
  with open("comptable3.bin", "rb") as f: table3 = f.read()
  with open("comptable4.bin", "rb") as f: table4 = f.read()
  with open("linetable.bin", "rb") as f: linetable = f.read()

  parser = KWZParser(kwz, table1, table2, table3, table4, linetable)

  palette = [
    (0xff, 0xff, 0xff),
    (0x14, 0x14, 0x14),
    (0xff, 0x45, 0x45),
    (0xff, 0xe6, 0x00),
    (0x00, 0x82, 0x32),
    (0x06, 0xAE, 0xff),
    (0xff, 0xff, 0xff),
  ]

  frame_index = int(argv[2])

  colors = parser.get_frame_palette(frame_index)
  frame = parser.decode_frame(frame_index)

  canvas = np.zeros((240, 320), dtype=np.uint8)
  # merge layers into canvas (starting with layer 3, at the back)
  for layer_index in range(2, -1, -1):
    mask = frame[layer_index] != 0
    canvas[mask] = frame[layer_index][mask] + (layer_index * 2)

  img = Image.fromarray(canvas, "P")
  img.putpalette([
    *palette[colors[0]], 
    *palette[colors[1]], 
    *palette[colors[2]], 
    *palette[colors[3]], 
    *palette[colors[4]], 
    *palette[colors[5]], 
    *palette[colors[6]], 
  ])

  img.save(argv[3])