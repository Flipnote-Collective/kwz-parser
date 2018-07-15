# ====================
# kwz.py version 1.0.0
# ====================
# 
# Class for reading frame data and audio from Flipnote Studio 3D's .kwz, .ico, and .kwc formats
# Implementation by James Daniel (github.com/jaames | rakujira.jp)
# 
# Credits:
#   MrNbaYoh - identifying the use of a line table
#   Kinnay - reverse-engineering tile compression
#   Shutterbug - early decompression and frame diffing work
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

class KWZParser:
  def __init__(self, buffer=None):
    # table1 - commonly occuring line offsets
    self.table1 = np.array([
      0x0000, 0x0CD0, 0x19A0, 0x02D9, 0x088B, 0x0051, 0x00F3, 0x0009,
      0x001B, 0x0001, 0x0003, 0x05B2, 0x1116, 0x00A2, 0x01E6, 0x0012,
      0x0036, 0x0002, 0x0006, 0x0B64, 0x08DC, 0x0144, 0x00FC, 0x0024,
      0x001C, 0x0004, 0x0334, 0x099C, 0x0668, 0x1338, 0x1004, 0x166C
    ], dtype=np.uint16)

    # table2 - commonly occuring line offsets, but the lines are shifted to the left by one pixel
    self.table2 = np.array([
      0x0000, 0x0CD0, 0x19A0, 0x0003, 0x02D9, 0x088B, 0x0051, 0x00F3, 
      0x0009, 0x001B, 0x0001, 0x0006, 0x05B2, 0x1116, 0x00A2, 0x01E6, 
      0x0012, 0x0036, 0x0002, 0x02DC, 0x0B64, 0x08DC, 0x0144, 0x00FC, 
      0x0024, 0x001C, 0x099C, 0x0334, 0x1338, 0x0668, 0x166C, 0x1004
    ], dtype=np.uint16)

    # table3 - line offsets, but the lines are shifted to the left by one pixel
    self.table3 = np.zeros((6561), dtype=np.uint16)
    values = [0, 3, 7, 1, 4, 8, 2, 5, 6]
    index = 0
    for a in range(9):
      for b in range(9):
        for c in range(9):
          for d in range(9):
            self.table3[index] = ((values[a] * 9 + values[b]) * 9 + values[c]) * 9 + values[d]
            index += 1

    # linetable - contains every possible sequence of pixels for each tile line
    self.linetable = np.zeros((6561), dtype="V8")
    index = 0
    for a in range(3):
      for b in range(3):
        for c in range(3):
          for d in range(3):
            for e in range(3):
              for f in range(3):
                for g in range(3):
                  for h in range(3):
                    self.linetable[index] = bytes([b, a, d, c, f, e, h, g])
                    index += 1

    # layer buffers w/ rearranged tiles 
    self.layer_pixels = np.zeros((3, 240, 40), dtype="V8")
    self.bit_index = 16
    self.bit_value = 0

    if buffer:
      self.load(buffer)

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
      # read part of the file header to get frame count, frame speed, etc
      self.buffer.seek(204)
      self.frame_count, self.thumb_index, self.frame_speed, layer_flags = struct.unpack("<HH2xBB", self.buffer.read(8))
      self.framerate = FRAMERATES[self.frame_speed]
      self.layer_visibility = [
        (layer_flags) & 0x1 == 0,      # Layer A
        (layer_flags >> 1) & 0x1 == 0, # Layer B
        (layer_flags >> 2) & 0x1 == 0, # Layer C
      ]
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
                line_index = self.table1[self.read_bits(5)]
                tile_buffer[0:8] = [self.linetable[line_index] * 8

              elif type == 1:
                line_index = self.read_bits(13)
                tile_buffer[0:8] = [self.linetable[line_index]] * 8

              elif type == 2:
                line_value = self.read_bits(5)
                a = self.linetable[self.table1[line_value]]
                b = self.linetable[self.table2[line_value]]
                tile_buffer[0:8] = [a, b, a, b, a, b, a, b]
              
              elif type == 3:
                line_value = self.read_bits(13)
                a = self.linetable[line_value]
                b = self.linetable[self.table3[line_value]]
                tile_buffer[0:8] = [a, b, a, b, a, b, a, b]

              elif type == 4:
                mask = self.read_bits(8)
                for i in range(8):
                  if mask & (1 << i):
                    line_index = self.table1[self.read_bits(5)]
                  else:
                    line_index = self.read_bits(13)
                  tile_buffer[i] = self.linetable[line_index]

              elif type == 5:
                skip = self.read_bits(5)
                continue
              
              elif type == 6:
                print("Found tile type 6 -- this is not implemented")
              
              elif type == 7:
                pattern = self.read_bits(2)
                use_table = self.read_bits(1)

                if use_table:
                  a_index = self.table1[self.read_bits(5)]
                  b_index = self.table1[self.read_bits(5)]
                  pattern = (pattern + 1) % 4
                else:
                  a_index = self.read_bits(13)
                  b_index = self.read_bits(13)

                a = self.linetable[a_value]
                b = self.linetable[b_value]

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
    # swap nibbles
    data = bytes(((byte << 4) & 0xF0) | (byte >> 4) for byte in self.buffer.read(size))
    return data