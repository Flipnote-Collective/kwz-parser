# =========================
# kwzVideo.py version 1.0.0
# =========================
# 
# Convert kwzs to mp4, using ffmpeg
# (no audio for now)
# 
# Usage:
# python kwzVideo.py <input.kwz> <output.mp4>

from sys import argv
from kwz import KWZParser, PALETTE
import subprocess as sp
import numpy as np

# convert palette to bytes
PALETTE = [bytes(color) for color in PALETTE]

infile = argv[1]
outfile = argv[2]

with open(infile, "rb") as kwz:
  parser = KWZParser(kwz)

  process = sp.Popen([
    "ffmpeg",
    # Hide the FFMPEG banner
    "-hide_banner",
    "-loglevel", "info",
    "-y",
    # Set the input frame size
    "-s", "320x240",
    # Set the frame rate
    "-r", str(parser.framerate),
    # Input format is raw, uncompressed frames
    "-f", "rawvideo",
    # Not actually sure what this is
    # The default value is 8, but I was getting a "Thread message queue blocking; consider raising the thread_queue_size option"
    "-thread_queue_size", "600",
    # Input color format is rgb
    "-pix_fmt", "rgb24",
    # Read frame input from stdin
    "-i", "pipe:0",
    # Set output codecs and other settings to the most suitable values for HTML5 video playback
    "-vcodec", "libx264",
    "-pix_fmt", "yuv420p",
    # Rescale each frame, using nearest neighbor interpolation
    "-vf", "scale=%d:%d:flags=neighbor" % (320*2, 240*2),
    # Use all available threads for slight speed boost
    "-threads", "0",
    # Set compression preset
    "-preset", "medium",
    # Tune output for animation
    "-tune", "animation",
    # "-f", "mp4",
    outfile
  ], stdin=sp.PIPE)

  image = np.zeros((240, 320), dtype="V3")

  for frame_index in range(parser.frame_count):
    colors = parser.get_frame_palette(frame_index)
    # fill image with paper color
    image.fill(PALETTE[colors[0]])
    layers = parser.decode_frame(frame_index)
    # merge layers into image using numpy magic (aka -- masks)
    image[layers[2] == 1] = PALETTE[colors[5]]
    image[layers[2] == 2] = PALETTE[colors[6]]
    image[layers[1] == 1] = PALETTE[colors[3]]
    image[layers[1] == 2] = PALETTE[colors[4]]
    image[layers[0] == 1] = PALETTE[colors[1]]
    image[layers[0] == 2] = PALETTE[colors[2]]
    # convert image to bytes
    process.stdin.write(image.tobytes())

  # Close the stdin pipe and wait for completion
  process.stdin.close()
  process.wait()