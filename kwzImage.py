from sys import argv
from kwz import KWZParser, PALETTE
from PIL import Image
import numpy as np

def get_image(parser, index):
  frame = parser.get_frame_image(index)
  colors = parser.get_frame_palette(index)
  img = Image.fromarray(frame, "P")
  img.putpalette([
    *PALETTE[colors[0]], 
    *PALETTE[colors[1]], 
    *PALETTE[colors[2]], 
    *PALETTE[colors[3]], 
    *PALETTE[colors[4]], 
    *PALETTE[colors[5]], 
    *PALETTE[colors[6]], 
  ])
  return img

with open(argv[1], "rb") as kwz:
  parser = KWZParser(kwz)

  if argv[2] == "gif":
    frame_duration = (1 / parser.framerate) * 1000
    frames = [get_image(parser, i) for i in range(parser.frame_count)]
    frames[0].save(argv[3], format="gif", save_all=True, append_images=frames[1:], duration=frame_duration, loop=False)

  else:
    index = int(argv[2])
    img = get_image(parser, index)
    img.save(argv[3])