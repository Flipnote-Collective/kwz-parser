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

def ROR(value, bits):
  return ((value >> bits) | (value << (32 - bits))) & 0xFFFFFFFF

class KWZParser:
  def __init__(self, buffer, linetable):
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

    self.buffer.seek(204)
    self.frame_count, self.thumb_index, self.frame_speed = struct.unpack("<HH2xB", self.buffer.read(7))
    self.framerate = FRAMERATES[self.frame_speed]

    # build frame meta list + frame offset list
    self.frame_meta = []
    self.frame_offsets = []
    self.buffer.seek(self.sections["KMI"]["offset"] + 8)
    offset = self.sections["KMC"]["offset"] + 12
    # parse each frame meta entry
    # https://github.com/Flipnote-Collective/flipnote-studio-3d-docs/wiki/kwz,-kwc-and-ico-format-documentation#kmi-memo-info-section
    for i in range(self.frame_count):
      meta = struct.unpack("<IHHH10xBBBBI", self.buffer.read(28))
      self.frame_meta.append(meta)
      self.frame_offsets.append(offset)
      offset += meta[1] + meta[2] + meta[3]

    self.table1 = np.full((256), 0x8, dtype=np.uint8)
    self.table1[0] = 0x00
    self.table1[1] = 0x01
    self.table1[15] = 0x02
    self.table1[16] = 0x03
    self.table1[17] = 0x04
    self.table1[31] = 0x05
    self.table1[240] = 0x06
    self.table1[241] = 0x07

    self.table2 = np.zeros((6561), dtype=np.uint32)
    values = [0, 1, 0xF, 0x10, 0x11, 0x1F, 0xF0, 0xF1, 0xFF]
    index = 0
    for a in range(9):
      for b in range(9):
        for c in range(9):
          for d in range(9):
            value = (values[a] << 24) | (values[b] << 16) | (values[c] << 8) | values[d]
            self.table2[index] = value
            index += 1

    self.table3 = np.array([
      0x00000000, 0x11111111, 0xFFFFFFFF, 0x00000001, 
      0x00000010, 0x00000100, 0x00001000, 0x00010000, 
      0x00100000, 0x01000000, 0x10000000, 0x0000000F, 
      0x000000F0, 0x00000F00, 0x0000F000, 0x000F0000, 
      0x00F00000, 0x0F000000, 0xF0000000, 0x00000011, 
      0x00000110, 0x00001100, 0x00011000, 0x00110000,
      0x01100000, 0x11000000, 0x01010101, 0x10101010, 
      0x0F0F0F0F, 0xF0F0F0F0, 0x1F1F1F1F, 0xF1F1F1F1
    ], dtype=np.uint32)
    
    self.table4 = np.array([
      0x0000, 0x0CD0, 0x19A0, 0x02D9, 0x088B, 0x0051, 0x00F3, 0x0009,
      0x001B, 0x0001, 0x0003, 0x05B2, 0x1116, 0x00A2, 0x01E6, 0x0012,
      0x0036, 0x0002, 0x0006, 0x0B64, 0x08DC, 0x0144, 0x00FC, 0x0024,
      0x001C, 0x0004, 0x0334, 0x099C, 0x0668, 0x1338, 0x1004, 0x166C
    ], dtype=np.uint16)

    self.linetable = np.frombuffer(linetable, dtype="V8")
    # layer buffers w/ rearranged tiles 
    self.layer_pixels = np.zeros((3, 240, 40), dtype="V8")
    self.bit_index = 16
    self.bit_value = 0

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

  # check if a frame can be decoded without having to decode previous frames
  def is_frame_new(self, frame_index):
    flags = self.frame_meta[frame_index][0]
    return (flags >> 4) & 0x07 == 7

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

  def decode_prev_frames(self, frame_index):
    back_index = 0
    is_new = 0
    while not is_new:
      back_index += 1
      is_new = self.is_frame_new(frame_index - back_index)
    back_index = frame_index - back_index;
    while back_index < index:
      self.decode_frame(back_index)
      back_index += 1

  def decode_frame(self, frame_index, use_prev_frames=False):
    if use_prev_frames and not self.is_frame_new(frame_index):
      self.decode_prev_frames(frame_index)

    meta = self.frame_meta[frame_index]
    offset = self.frame_offsets[frame_index]

    # loop through layers
    for layer_index in range(3):
      layer_length = meta[layer_index + 1]
      self.buffer.seek(offset)
      offset += layer_length
      
      # if the layer is 38 bytes then it hasn't changed since the previous frame, so we can skip it
      if layer_length == 38:
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

              # decode tile
              type = self.read_bits(3)

              if type == 0:
                line_value = self.table4[self.read_bits(5)]
                tile_buffer[0:8] = [self.linetable[line_value]] * 8

              elif type == 1:
                line_value = self.read_bits(13)
                tile_buffer[0:8] = [self.linetable[line_value]] * 8

              elif type == 2:
                index1 = self.read_bits(5)
                index2 = ROR(self.table3[index1], 4)
                v1 = self.table1[index2 & 0xFF]
                v2 = self.table1[(index2 >> 8) & 0xFF]
                v3 = self.table1[(index2 >> 16) & 0xFF]
                v4 = self.table1[index2 >> 24]
                a_value = self.table4[index1]
                b_value = ((v1 * 9 + v2) * 9 + v3) * 9 + v4
                a = self.linetable[a_value]
                b = self.linetable[b_value]
                tile_buffer[0:8] = [a, b, a, b, a, b, a, b]
              
              elif type == 3:
                a_value = self.read_bits(13)
                index = ROR(self.table2[a_value], 4)
                v1 = self.table1[index & 0xFF]
                v2 = self.table1[(index >> 8) & 0xFF]
                v3 = self.table1[(index >> 16) & 0xFF]
                v4 = self.table1[index >> 24]
                b_value = ((v1 * 9 + v2) * 9 + v3) * 9 + v4
                a = self.linetable[a_value]
                b = self.linetable[b_value]
                tile_buffer[0:8] = [a, b, a, b, a, b, a, b]

              elif type == 4:
                mask = self.read_bits(8)
                for i in range(8):
                  if mask & (1 << i):
                    line_value = self.table4[self.read_bits(5)]
                  else:
                    line_value = self.read_bits(13)
                  tile_buffer[i] = self.linetable[line_value]

              elif type == 5:
                skip = self.read_bits(5)
                continue
              
              elif type == 6:
                print("Found tile type 6 -- this is not implemented")
              
              elif type == 7:
                pattern = self.read_bits(2)
                use_table = self.read_bits(1)
                
                if use_table:
                  a_value = self.table4[self.read_bits(5)]
                  b_value = self.table4[self.read_bits(5)]
                  pattern = (pattern + 1) % 4
                else:
                  a_value = self.read_bits(13)
                  b_value = self.read_bits(13)

                a = self.linetable[a_value]
                b = self.linetable[b_value]

                if pattern == 0: tile_buffer[0:8] = [a, b, a, b, a, b, a, b]
                if pattern == 1: tile_buffer[0:8] = [a, a, b, a, a, b, a, a]
                if pattern == 2: tile_buffer[0:8] = [a, b, a, a, b, a, a, b]
                if pattern == 3: tile_buffer[0:8] = [a, b, b, a, b, b, a, b]

              # copy each line of the tile into the layer's pixel buffer
              for line_index in range(0, 8):
                pixel_buffer[y + line_index][x // 8] = tile_buffer[line_index]

    return self.layer_pixels.view(np.uint8)

  def get_frame_image(self, index, use_prev_frames=True):
    layers = self.decode_frame(index, use_prev_frames=use_prev_frames)
    image = np.zeros((240, 320), dtype=np.uint8)

    for y in range(240):
      for x in range(320):
        a = layers[0][y][x]
        b = layers[1][y][x]
        c = layers[2][y][x]
        if (c):
          image[y][x] = c + 4
        if (b):
          image[y][x] = b + 2
        if (a):
          image[y][x] = a
    
    return image

if __name__ == "__main__":
  print("Please use kwzViewer.py to view Flipnotes now :)")