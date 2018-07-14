from sys import argv
from kwz import KWZParser
import wave
import audioop

with open(argv[1], "rb")as kwz:
  parser = KWZParser(kwz)

  track_index = int(argv[2])

  audio = wave.open(argv[3], "wb")
  audio.setnchannels(1)
  audio.setsampwidth(2)
  audio.setframerate(16364)

  data = parser.get_audio_track(track_index)

  with open(argv[4], "wb") as f:
    f.write(data)

  samples, state = audioop.adpcm2lin(data, 2, None)
  audio.writeframes(samples)
  audio.close()