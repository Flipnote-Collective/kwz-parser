# =========================
# kwzAudio.py version 1.0.0
# =========================
# 
# Exports a Flipnote audio track and converts it to WAV
# 
# Usage:
# python kwzAudio.py <input.kwz> <track id> <output.wav>

from sys import argv
from kwz import KWZParser
import wave

with open(argv[1], "rb")as kwz:
  parser = KWZParser(kwz)

  track_index = int(argv[2])

  audio = wave.open(argv[3], "wb")
  audio.setnchannels(1)
  audio.setsampwidth(2)
  audio.setframerate(16364)
  data = parser.get_audio_track(track_index)
  audio.writeframes(data.tobytes())
  audio.close()