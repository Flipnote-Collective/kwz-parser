# ====================
# kwz.py version 1.0.0
# ====================
# 
# Class for reading frame data and audio from Flipnote Studio 3D's .kwz, .ico, and .kwc formats
# Implementation by James Daniel (github.com/jaames | rakujira.jp)
# 
# Credits:
#   Kinnay - reverse-engineering tile compression
#   Khangaroo - reverse-engineering a large chunk of the audio format
#   Shutterbug - early decompression and frame diffing work
#   MrNbaYoh - identifying the use of a line table
#   Stary, JoshuaDoes and thejsa - debugging/optimisation help
#   Sudofox - audio format help and comment sample files
# 
# Format docs:
#   https://github.com/Flipnote-Collective/flipnote-studio-3d-docs/wiki/kwz-format

import struct
import numpy as np

FRAMERATES = [
  0.2,
  0.5,
  1,
  2,
  4, 
  6,
  8,
  12, 
  20,
  24,
  30
]

PALETTE = [
  (0xff, 0xff, 0xff),
  (0x10, 0x10, 0x10),
  (0xff, 0x10, 0x10),
  (0xff, 0xe7, 0x00),
  (0x00, 0x86, 0x31),
  (0x00, 0x38, 0xce),
  (0xff, 0xff, 0xff),
]

# table1 - commonly occuring line offsets
TABLE_1 = np.array([
  0x0000, 0x0CD0, 0x19A0, 0x02D9, 0x088B, 0x0051, 0x00F3, 0x0009,
  0x001B, 0x0001, 0x0003, 0x05B2, 0x1116, 0x00A2, 0x01E6, 0x0012,
  0x0036, 0x0002, 0x0006, 0x0B64, 0x08DC, 0x0144, 0x00FC, 0x0024,
  0x001C, 0x0004, 0x0334, 0x099C, 0x0668, 0x1338, 0x1004, 0x166C
], dtype=np.uint16)

# table2 - commonly occuring line offsets, but the lines are shifted to the left by one pixel
TABLE_2= np.array([
  0x0000, 0x0CD0, 0x19A0, 0x0003, 0x02D9, 0x088B, 0x0051, 0x00F3, 
  0x0009, 0x001B, 0x0001, 0x0006, 0x05B2, 0x1116, 0x00A2, 0x01E6, 
  0x0012, 0x0036, 0x0002, 0x02DC, 0x0B64, 0x08DC, 0x0144, 0x00FC, 
  0x0024, 0x001C, 0x099C, 0x0334, 0x1338, 0x0668, 0x166C, 0x1004
], dtype=np.uint16)

# table3 - line offsets, but the lines are shifted to the left by one pixel
TABLE_3 = np.zeros((6561), dtype=np.uint16)
values = [0, 3, 7, 1, 4, 8, 2, 5, 6]
index = 0
for a in range(9):
  for b in range(9):
    for c in range(9):
      for d in range(9):
        TABLE_3[index] = ((values[a] * 9 + values[b]) * 9 + values[c]) * 9 + values[d]
        index += 1

# linetable - contains every possible sequence of pixels for each tile line
LINE_TABLE = np.zeros((6561), dtype="V8")
index = 0
for a in range(3):
  for b in range(3):
    for c in range(3):
      for d in range(3):
        for e in range(3):
          for f in range(3):
            for g in range(3):
              for h in range(3):
                LINE_TABLE[index] = bytes([b, a, d, c, f, e, h, g])
                index += 1

ADPCM_STEP_TABLE = np.array([
  7,     8,     9,     10,    11,    12,    13,    14,    16,    17,
  19,    21,    23,    25,    28,    31,    34,    37,    41,    45,
  50,    55,    60,    66,    73,    80,    88,    97,    107,   118,
  130,   143,   157,   173,   190,   209,   230,   253,   279,   307,
  337,   371,   408,   449,   494,   544,   598,   658,   724,   796,
  876,   963,   1060,  1166,  1282,  1411,  1552,  1707,  1878,  2066,
  2272,  2499,  2749,  3024,  3327,  3660,  4026,  4428,  4871,  5358,
  5894,  6484,  7132,  7845,  8630,  9493,  10442, 11487, 12635, 13899,
  15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767, 0
], dtype=np.int16)

# index table for 2-bit samples
ADPCM_INDEX_TABLE_2 = np.array([
  -1,  2,
  -1,  2,
], dtype=np.int8)

# index table for 4-bit samples
ADPCM_INDEX_TABLE_4 = np.array([
  -1, -1, -1, -1, 2, 4, 6, 8,
  -1, -1, -1, -1, 2, 4, 6, 8,
], dtype=np.int8)

# lookup table that maps 2-bit adpcm sample values to pcm samples
ADPCM_SAMPLE_TABLE_2 = np.zeros(90 * 4, dtype=np.int16)
for sample in range (4):
  for step_index in range(90):
    step = ADPCM_STEP_TABLE[step_index]
    diff = step >> 3
    if (sample & 1): diff += step;
    if (sample & 2): diff = -diff;
    ADPCM_SAMPLE_TABLE_2[sample + 4 * step_index] = diff

# lookup table that maps 4-bit adpcm sample values to pcm samples
ADPCM_SAMPLE_TABLE_4 = np.zeros(90 * 16, dtype=np.int16)
for sample in range (16):
  for step_index in range(90):
    step = ADPCM_STEP_TABLE[step_index]
    diff = step >> 3;
    if (sample & 4): diff += step;
    if (sample & 2): diff += step >> 1;
    if (sample & 1): diff += step >> 2;
    if (sample & 8): diff = -diff;
    ADPCM_SAMPLE_TABLE_4[sample + 16 * step_index] = diff

class KWZParser:
  def __init__(self, buffer=None):
    # layer output buffers
    self.layer_pixels = np.zeros((3, 240, 40), dtype="V8")
    # initial values for read_bits()
    self.bit_index = 16
    self.bit_value = 0
    if buffer: self.load(buffer)

  @classmethod
  def open(cls, path):
    with open(path, "rb") as buffer:
      return cls(buffer)

  def load(self, buffer):
    self.buffer = buffer
    # lazy way to get file length - seek to the end (ignore signature), get the position, then seek back to the start
    self.buffer.seek(0, 2)
    self.size = self.buffer.tell() - 256
    self.buffer.seek(0, 0)
    # build list of section offsets + lengths
    self.sections = {}
    offset = 0
    while offset < self.size:
      self.buffer.seek(offset)
      magic, length = struct.unpack("<3sxI", self.buffer.read(8))
      self.sections[str(magic, 'utf-8')] = {"offset": offset, "length": length}
      offset += length + 8

    # read file header -- not present in folder icons
    if "KFH" in self.sections:
      self.decode_meta()
      self.is_folder_icon = False  
    else:
      self.is_folder_icon = True
      self.frame_count = 1

    # read sound data header -- not present in comments or icons
    if "KSN" in self.sections:
      self.buffer.seek(self.sections["KSN"]["offset"] + 8)
      self.track_frame_speed = struct.unpack("<I", self.buffer.read(4))
      self.track_lengths = struct.unpack("<IIIII", self.buffer.read(20))

    # build frame meta list + frame offset list
    self.frame_meta = []
    self.frame_offsets = []
    self.buffer.seek(self.sections["KMI"]["offset"] + 8)
    offset = self.sections["KMC"]["offset"] + 12
    # parse each frame meta entry
    # https://github.com/Flipnote-Collective/flipnote-studio-3d-docs/wiki/kwz-format#kmi-frame-meta 
    for i in range(self.frame_count):
      meta = struct.unpack("<IHHH10xBBBBI", self.buffer.read(28))
      self.frame_meta.append(meta)
      self.frame_offsets.append(offset)
      offset += meta[1] + meta[2] + meta[3]

    self.prev_decoded_frame = -1

  def unload(self):
    self.buffer.close()
    self.size = 0
    self.sections = {}
    self.frame_count = 0
    self.thumb_index = 0
    self.frame_speed = 0
    self.layer_visibility = [False, False, False]
    self.is_folder_icon = False
    self.frame_meta = []
    self.frame_offsets = []
    self.track_frame_speed = 0
    self.track_lengths = [0, 0, 0, 0, 0]
    self.prev_decoded_frame = -1

  def read_bits(self, num):
    if self.bit_index + num > 16:
      next_bits = int.from_bytes(self.buffer.read(2), byteorder="little")
      self.bit_value |= next_bits << (16 - self.bit_index)
      self.bit_index -= 16

    mask = (1 << num) - 1
    result = self.bit_value & mask
    self.bit_value >>= num
    self.bit_index += num
    return result

  def decode_meta(self):
    self.buffer.seek(self.sections["KFH"]["offset"] + 12)
    creation_timestamp, modified_timestamp, app_version = struct.unpack("<III", self.buffer.read(12))
    root_author_id, parent_author_id, current_author_id = struct.unpack("<10s10s10s", self.buffer.read(30)) 
    root_author_name, parent_author_name, current_author_name = struct.unpack("<22s22s22s", self.buffer.read(66))
    root_filename, parent_filename, current_filename = struct.unpack("<28s28s28s", self.buffer.read(84))
    self.frame_count, self.thumb_index, flags, self.frame_speed, layer_flags = struct.unpack("<HHHBB", self.buffer.read(8))
    self.framerate = FRAMERATES[self.frame_speed]
    self.layer_visibility = [
      (layer_flags) & 0x1 == 0,      # Layer A
      (layer_flags >> 1) & 0x1 == 0, # Layer B
      (layer_flags >> 2) & 0x1 == 0, # Layer C
    ]
    self.meta = {
      "lock": flags & 0x1,
      "loop": (flags >> 1) & 0x01,
      "frame_count": self.frame_count,
      "frame_speed": self.frame_speed,
      "thumb_index": self.thumb_index,
      "timestamp": modified_timestamp,
      "creation_timestamp": creation_timestamp,
      "root": {
        "username": root_author_name.decode("utf-16").rstrip("\x00"),
        "fsid": root_author_id.hex(),
        "filename": root_filename.decode("utf-8"),
      },
      "parent": {
        "username": parent_author_name.decode("utf-16").rstrip("\x00"),
        "fsid": parent_author_id.hex(),
        "filename": parent_filename.decode("utf-8"),
      },
      "current": {
        "username": current_author_name.decode("utf-16").rstrip("\x00"),
        "fsid": current_author_id.hex(),
        "filename": current_filename.decode("utf-8"),
      }
    }
    return self.meta

  def get_diffing_flag(self, frame_index):
    # bits are inverted so that if a bit is set, it indicates a layer needs to be decoded
    return ~(self.frame_meta[frame_index][0] >> 4) & 0x07

  def decode_frame(self, frame_index, diffing_flag=0x07, is_prev_frame=False):
    # if this frame is being decoded as a prev frame, then we only want to decode the layers necessary
    if is_prev_frame:
      diffing_flag &= self.get_diffing_flag(frame_index + 1)
    # the self.prev_decoded_frame check is an optimisation for decoding frames in full sequence
    if not self.prev_decoded_frame == frame_index - 1 and diffing_flag:
      self.decode_frame(frame_index - 1, diffing_flag=diffing_flag, is_prev_frame=True)

    meta = self.frame_meta[frame_index]
    offset = self.frame_offsets[frame_index]

    # loop through layers
    for layer_index in range(3):
      layer_length = meta[layer_index + 1]
      self.buffer.seek(offset)
      offset += layer_length

      # if the layer is 38 bytes then it hasn't changed at all since the previous frame, so we can skip it
      if layer_length == 38:
        continue

      if not (diffing_flag >> layer_index) & 0x1:
        continue

      # skip if the layer is invisible
      if not self.layer_visibility[layer_index]:
        continue
      
      pixel_buffer = self.layer_pixels[layer_index]
      self.bit_index = 16
      self.bit_value = 0
      layer_offset = 0
      skip = 0
      # tile work buffer
      tile_buffer = np.zeros((8), dtype="V8")

      # loop through 128 * 128 large tiles
      for tile_offset_y in range(0, 240, 128):
        for tile_offset_x in range(0, 320, 128):
          # each large tile is made of 8 * 8 small tiles
          for sub_tile_offset_y in range(0, 128, 8):
            y = tile_offset_y + sub_tile_offset_y
            # if the tile falls off the bottom of the frame, jump to the next large tile
            if y >= 240: break

            for sub_tile_offset_x in range(0, 128, 8):
              x = tile_offset_x + sub_tile_offset_x
              # if the tile falls off the right of the frame, jump to the next small tile row
              if x >= 320: 
                break

              if skip: 
                skip -= 1
                continue

              type = self.read_bits(3)

              if type == 0:
                line_index = TABLE_1[self.read_bits(5)]
                tile_buffer[0:8] = [LINE_TABLE[line_index]] * 8

              elif type == 1:
                line_index = self.read_bits(13)
                tile_buffer[0:8] = [LINE_TABLE[line_index]] * 8

              elif type == 2:
                line_value = self.read_bits(5)
                a = LINE_TABLE[TABLE_1[line_value]]
                b = LINE_TABLE[TABLE_2[line_value]]
                tile_buffer[0:8] = [a, b, a, b, a, b, a, b]
              
              elif type == 3:
                line_value = self.read_bits(13)
                a = LINE_TABLE[line_value]
                b = LINE_TABLE[TABLE_3[line_value]]
                tile_buffer[0:8] = [a, b, a, b, a, b, a, b]

              elif type == 4:
                mask = self.read_bits(8)
                for i in range(8):
                  if mask & (1 << i):
                    line_index = TABLE_1[self.read_bits(5)]
                  else:
                    line_index = self.read_bits(13)
                  tile_buffer[i] = LINE_TABLE[line_index]

              elif type == 5:
                skip = self.read_bits(5)
                continue
              
              elif type == 6:
                print("Found tile type 6 -- this is not implemented")
              
              elif type == 7:
                pattern = self.read_bits(2)
                use_table = self.read_bits(1)

                if use_table:
                  a_index = TABLE_1[self.read_bits(5)]
                  b_index = TABLE_1[self.read_bits(5)]
                  pattern = (pattern + 1) % 4
                else:
                  a_index = self.read_bits(13)
                  b_index = self.read_bits(13)

                a = LINE_TABLE[a_index]
                b = LINE_TABLE[b_index]

                if pattern == 0: tile_buffer[0:8] = [a, b, a, b, a, b, a, b]
                if pattern == 1: tile_buffer[0:8] = [a, a, b, a, a, b, a, a]
                if pattern == 2: tile_buffer[0:8] = [a, b, a, a, b, a, a, b]
                if pattern == 3: tile_buffer[0:8] = [a, b, b, a, b, b, a, b]

              # copy each line of the tile into the layer's pixel buffer
              for line in range(0, 8):
                pixel_buffer[y + line][x // 8] = tile_buffer[line]

    self.prev_decoded_frame = frame_index
    return self.layer_pixels.view(np.uint8)

  def get_frame_palette(self, frame_index):
    flags = self.frame_meta[frame_index][0]
    return [
      flags & 0xF,         # paper color
      (flags >> 8) & 0xF,  # layer A color 1
      (flags >> 12) & 0xF, # layer A color 2
      (flags >> 16) & 0xF, # layer B color 1
      (flags >> 20) & 0xF, # layer B color 2
      (flags >> 24) & 0xF, # layer C color 1
      (flags >> 28) & 0xF, # layer C color 2
    ]

  def get_frame_image(self, index):
    layers = self.decode_frame(index)
    if self.is_folder_icon:
      width = 24
      height = 24
    else:
      width = 320
      height = 240
    image = np.zeros((height, width), dtype=np.uint8)

    layer_depths = self.frame_meta[index][4:7]
    # get a list of layer indexes (from 0 (layer A) to 2 (layer C)), sorted by layer depth
    # the layer depth closest to 6 should be first, closest to 0 last
    layer_order = np.argsort(layer_depths)[::-1]

    for y in range(height):
      for x in range(width):
        for layer_index in layer_order:
          pixel = layers[layer_index][y][x]
          if pixel:
            image[y][x] = pixel + layer_index * 2
    return image

  def has_audio_track(self, track_index):
    return self.track_lengths[track_index] > 0

  def get_audio_track(self, track_index):
    size = self.track_lengths[track_index]
    # offset starts after sound header
    offset = self.sections["KSN"]["offset"] + 36
    for i in range(track_index):
      offset += self.track_lengths[i]
    self.buffer.seek(offset)

    # create an output buffer with enough space for 60 seconds of audio at 16364 Hz
    output = np.zeros(16364 * 60, dtype="<u2");
    outputOffset = 0

    # initial decoder state
    prev_diff = 0
    prev_step_index = 40

    for byte in self.buffer.read(size):

      bit_pos = 0
      while bit_pos < 8:

        # read a 2-bit sample if the previous step index is < 18, or if only 2 bits are left of the byte
        if prev_step_index < 18 or bit_pos == 6:
          # isolate 2-bit sample
          sample = (byte >> bit_pos) & 0x3
          # get diff
          diff = prev_diff + ADPCM_SAMPLE_TABLE_2[sample + 4 * prev_step_index]
          # get step index
          step_index = prev_step_index + ADPCM_INDEX_TABLE_2[sample]
          bit_pos += 2

        # else read a 4-bit sample
        else:
          # isolate 4-bit sample
          sample = (byte >> bit_pos) & 0xF
          # get diff
          diff = prev_diff + ADPCM_SAMPLE_TABLE_4[sample + 16 * prev_step_index]
          # get step index
          step_index = prev_step_index + ADPCM_INDEX_TABLE_4[sample]
          bit_pos += 4

        # clamp step index and diff
        step_index = max(0, min(step_index, 79))
        diff = max(-2048, min(diff, 2048))

        # add result to output buffer
        output[outputOffset] = diff * 16
        outputOffset +=1

        # set prev decoder state
        prev_step_index = step_index
        prev_diff = diff

    return output[:outputOffset]

if __name__ == "__main__":
  from sys import argv
  KWZParser.open(argv[1])