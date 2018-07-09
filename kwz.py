import struct
from sys import argv
import numpy as np
from PIL import Image
import pygame

def ROR(value, bits):
  return ((value >> bits) | (value << (32 - bits))) & 0xFFFFFFFF

class KWZParser:
  def __init__(self, buffer, table1, table2, table3, table4, linetable):
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

    # build frame meta list + frame offset list
    self.frame_meta = []
    self.frame_offsets = []
    self.frame_count = self.sections["KMI"]["length"] // 28
    self.buffer.seek(self.sections["KMI"]["offset"] + 8)
    offset = self.sections["KMC"]["offset"] + 12
    # parse each frame meta entry
    # https://github.com/Flipnote-Collective/flipnote-studio-3d-docs/wiki/kwz,-kwc-and-ico-format-documentation#kmi-memo-info-section
    for i in range(self.frame_count):
      meta = struct.unpack("<IHHH10xBBBBI", self.buffer.read(28))
      self.frame_meta.append(meta)
      self.frame_offsets.append(offset)
      offset += meta[1] + meta[2] + meta[3]

    self.table1 = table1
    self.table2 = np.frombuffer(table2, dtype=np.uint32)
    self.table3 = np.frombuffer(table3, dtype=np.uint32)
    self.table4 = np.frombuffer(table4, dtype=np.uint16)
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

  # check if each layer in a given frame are based on the previous frame
  def is_p_frame(self, index):
    flags = self.frame_meta[index][0]
    uses_compression = (flags >> 7) & 0x1
    is_p_frame = (flags >> 4) & 0x07 < 7
    layer_c = (flags >> 6) & 0x1
    layer_b = (flags >> 5) & 0x1
    layer_a = (flags >> 4) & 0x1
    return [is_p_frame, layer_a == 0, layer_b == 0, layer_c == 0]

  def get_frame_palette(self, index):
    flags = self.frame_meta[index][0]
    return [
      flags & 0xF,         # paper color
      (flags >> 8) & 0xF,  # layer A color 1
      (flags >> 12) & 0xF, # layer A color 2
      (flags >> 16) & 0xF, # layer B color 1
      (flags >> 20) & 0xF, # layer B color 2
      (flags >> 24) & 0xF, # layer C color 1
      (flags >> 28) & 0xF, # layer C color 2
    ]

  def decode_frame(self, index):
    meta = self.frame_meta[index]
    offset = self.frame_offsets[index]

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
                index = ROR(self.table2[x], 4)
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

    return self.layer_pixels

class layerSurface:
  def __init__(self, size=(320, 240)):
    self.surface = pygame.Surface(size, depth=8)
    self.surface.set_colorkey(0)
    self.surface.set_palette_at(0, (255, 255, 255))

  def set_palette_at(self, index, color):
    self.surface.set_palette_at(index, color)

  def set_pixels(self, pixels):
    pixels = np.swapaxes(pixels.view(np.uint8), 0, 1)
    pygame.pixelcopy.array_to_surface(self.surface, pixels)

  def get_surface(self, size=(320, 240)):
    if size != (320, 240):
      return pygame.transform.scale(self.surface, size)
    else:
      return self.surface

class frameSurface:
  def __init__(self, size=(320, 240)):
    self.size = size
    self.paper = pygame.Surface(size, depth=8)
    self.layer1 = layerSurface()
    self.layer2 = layerSurface()
    self.layer3 = layerSurface()

  def set_layers(self, layers):
    self.layer1.set_pixels(layers[0])
    self.layer2.set_pixels(layers[1])
    self.layer3.set_pixels(layers[2])
    
  def set_colors(self, colors, palette):
    self.paper.set_palette_at(0, palette[colors[0]])
    self.layer1.set_palette_at(1, palette[colors[1]])
    self.layer1.set_palette_at(2, palette[colors[2]])
    self.layer2.set_palette_at(1, palette[colors[3]])
    self.layer2.set_palette_at(2, palette[colors[4]])
    self.layer3.set_palette_at(1, palette[colors[5]])
    self.layer3.set_palette_at(2, palette[colors[6]])

  def blit_to(self, surface, pos):
    surface.blit(self.paper, pos)
    surface.blit(self.layer3.get_surface(self.size), pos)
    surface.blit(self.layer2.get_surface(self.size), pos)
    surface.blit(self.layer1.get_surface(self.size), pos)


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

  screen = pygame.display.set_mode((320*2, 240*2))
  frame = frameSurface((320*2, 240*2))

  pygame.init()
  pygame.display.set_caption("crappy proof-of-concept kwz player™")

  done = False
  frame_index = 0

  while not done:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        done = True

    parser.is_p_frame(frame_index)
    frame.set_layers(parser.decode_frame(frame_index))
    frame.set_colors(parser.get_frame_palette(frame_index), palette)
    # print("Decoded frame:", frameIndex, "flag:", parser.get_frame_flag(frameIndex))
    if frame_index == parser.frame_count - 1:
      frame_index = 0
    else:
      frame_index += 1

    frame.blit_to(screen, (0, 0))
    pygame.display.flip()