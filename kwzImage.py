# =========================
# kwzImage.py version 1.0.0
# =========================
# 
# Exports a Flipnote audio track and converts it to WAV
# 
# Usage:
# python kwzImage.py <input path> <frame index> <output path>

import glob
from sys import argv
import os
from kwz import KWZParser, PALETTE
from PIL import Image

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

parser = KWZParser()
filelist = glob.glob(argv[1], recursive=True)

for (index, path) in enumerate(filelist):
  with open(path, "rb") as kwz:
    basename = os.path.basename(path)
    dirname = os.path.dirname(path)
    filestem, ext = os.path.splitext(basename)
    outpath = argv[3].format(name=filestem, dirname=dirname, index=index, ext=ext)

    print("Converting", path, "->", outpath)
    parser.load(kwz)

    if argv[2] == "gif":
      frame_duration = (1 / parser.framerate) * 1000
      frames = [get_image(parser, i) for i in range(parser.frame_count)]
      frames[0].save(outpath, format="gif", save_all=True, append_images=frames[1:], duration=frame_duration, loop=False)

    elif argv[2] == "thumb":
      img = get_image(parser, parser.thumb_index)
      img.save(outpath)

    else:
      index = int(argv[2])
      img = get_image(parser, index)
      img.save(outpath)

    parser.unload()