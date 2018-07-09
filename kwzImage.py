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

  image = parser.get_frame_image(frame_index)
  colors = parser.get_frame_palette(frame_index)

  img = Image.fromarray(image, "P")
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