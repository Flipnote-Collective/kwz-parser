import struct
from sys import argv
import numpy as np
from PIL import Image
import pygame

def ROR(value, bits):
  return ((value >> bits) | (value << (32 - bits))) & 0xFFFFFFFF

class Decompressor:
  def __init__(self, table1, table3, table4):
    self.table1 = table1
    self.table3 = struct.unpack("<32I", table3)
    self.table4 = struct.unpack("<32H", table4)
        
  def reset(self, data, prev):
    self.data = data
    self.prev = prev
    self.bit_index = 16
    self.bit_offs = 0
    self.bit_value = 0

  def bits(self, num):
    if self.bit_index + num > 16:
      next_bits = struct.unpack_from("<H", self.data, self.bit_offs)[0]
      self.bit_offs += 2
      self.bit_value |= next_bits << (16 - self.bit_index)
      self.bit_index -= 16

    mask = (1 << num) - 1
    result = self.bit_value & mask
    self.bit_value >>= num
    self.bit_index += num
    return result

  def decompress(self, data, prev=None):
    self.reset(data, prev)
    self.output = b""
    while len(self.output) < 0x4B00:
      self.output += self.process_chunk()
    return self.output

  def make_chunk(self, values):
    return struct.pack("<8H", *values)

  def process_chunk(self):
    type = self.bits(3)

    if type == 0:
      value = self.table4[self.bits(5)]
      return self.make_chunk([value] * 8)

    elif type == 1:
      value = self.bits(13)
      return self.make_chunk([value] * 8)

    elif type == 2:
      index1 = self.bits(5)
      index2 = ROR(self.table3[index1], 4) #Why are they rotating the bits?
      v1 = self.table1[index2 & 0xFF]
      v2 = self.table1[(index2 >> 8) & 0xFF]
      v3 = self.table1[(index2 >> 16) & 0xFF]
      v4 = self.table1[index2 >> 24]

      x = self.table4[index1]
      y = ((v1 * 9 + v2) * 9 + v3) * 9 + v4 #Wtf?
      return self.make_chunk([x, y, x, y, x, y, x, y])

    elif type == 4:
      mask = self.bits(8)
      words = []
      for i in range(8):
        if mask & (1 << i):
          words.append(self.table4[self.bits(5)])
        else:
          words.append(self.bits(13))
      return self.make_chunk(words)

    elif type == 5:
      length = self.bits(5) + 1
      offset = len(self.output)
      return self.prev[offset : offset + length * 0x10]

    elif type == 7:
      pattern = self.bits(2)
      use_table = self.bits(1)

      if use_table:
        x = self.table4[self.bits(5)]
        y = self.table4[self.bits(5)]
        pattern = (pattern + 1) % 4
      else:
        x = self.bits(13)
        y = self.bits(13)

      if pattern == 0: return self.make_chunk([x, y, x, y, x, y, x, y])
      elif pattern == 1: return self.make_chunk([x, x, y, x, x, y, x, y])
      elif pattern == 2: return self.make_chunk([x, y, x, x, y, x, x, y])
      elif pattern == 3: return self.make_chunk([x, y, y, x, y, y, x, y])
        
    else:
      raise NotImplementedError("Chunk type not implemented (%i)" %type)
        

class KWZParser:
  def __init__(self, buffer, table1, table3, table4, linedefs):
    self.buffer = buffer
    # lazy way to get file length - seek to the end (ignore signature), get the position, then seek back to the start
    self.buffer.seek(0, 2)
    self.size = self.buffer.tell() - 256
    self.buffer.seek(0, 0)
    self.decompressor = Decompressor(table1, table3, table4)
    self.linedefs = np.frombuffer(linedefs, dtype=np.uint8).reshape(-1, 8)
    # build list of section offsets + lengths
    self.sections = {}
    offset = 0
    while offset < self.size:
      self.buffer.seek(offset)
      magic, length = struct.unpack("<3sxI", self.buffer.read(8))
      self.sections[str(magic, 'utf-8')] = {"offset": offset, "length": length}
      offset += length + 8

    # build frame meta list
    self.frameMeta = []
    frameCount = self.sections["KMI"]["length"] // 28
    self.buffer.seek(self.sections["KMI"]["offset"] + 8)
    for i in range(frameCount):
      self.frameMeta.append(struct.unpack("<IHHH10xBBBBI", self.buffer.read(28)))

    self.prev = [b"", b"", b""]

  def close(self):
    self.buffer.close()

  def get_frame_palette(self, index):
    flags = self.frameMeta[index][0]

    return [
      (flags >> 0) & 0xF,
      (flags >> 12) & 0xF,
      (flags >> 8) & 0xF,
      (flags >> 20) & 0xF,
      (flags >> 16) & 0xF,
      (flags >> 28) & 0xF,
      (flags >> 24) & 0xF,
    ]

  def decode_frame(self, index):
    # get frame offset
    offset = self.sections["KMC"]["offset"] + 12
    for i in range(index):
      meta = self.frameMeta[i]
      offset += meta[1] + meta[2] + meta[3]

    meta = self.frameMeta[index]
    self.buffer.seek(offset)

    ret = []

    # loop through layers
    for layerIndex in range(3):
      layerLength = meta[layerIndex + 1]
      data = self.buffer.read(layerLength)
      try: 
        data = self.decompressor.decompress(data, prev=self.prev[layerIndex])
        layer = np.frombuffer(data, dtype=np.uint16)
        layerOffset = 0
        arranged = np.zeros((240, 320), dtype=np.uint8)
        tileIndex = 0
        # loop through 128 * 128 large tiles
        for tileOffsetY in range(0, 240, 128):
          for tileOffsetX in range(0, 320, 128):
            # each large tile is made of 8 * 8 small tiles
            for subTileOffsetY in range(0, 128, 8):
              y = tileOffsetY + subTileOffsetY
              # if the tile falls off the bottom of the frame, jump to the next large tile
              if y >= 240: break

              for subTileOffsetX in range(0, 128, 8):
                x = tileOffsetX + subTileOffsetX
                # if the tile falls off the right of the frame, jump to the next small tile row
                if x >= 320: break
                
                # unpack the 8*8 tile - (x, y) gives the position of the tile's top-left pixel
                for lineIndex in range(0, 8):
                  # get the line data
                  # each line is defined as an uint16 offset into a table of all possible line values
                  lineValue = layer[layerOffset]
                  # in certain cases we have to flip the endianess because... of course?
                  if lineValue > 0x3340:
                    lineValue = ((lineValue) >> 8) | ((lineValue & 0x00FF) << 8)
                  lineValue //= 2
                  # adjust line pixel order
                  line = self.linedefs[lineValue].reshape(-1, 2)
                  line = np.flip(line, 1)
                  line = line.flatten()
                  # loop through each pixel in the line
                  for pixelIndex in range(0, 8):
                    arranged[y + lineIndex][x + pixelIndex] = line[pixelIndex]
                  layerOffset += 1

        ret.append(arranged)
        self.prev[layerIndex] = data
      except NotImplementedError as err:
        print("Decompress Error - Frame:", frameIndex, "Layer:", layerIndex, "Offset:", self.buffer.tell(), "-", err)
    
    return ret

class layerSurface:
  def __init__(self, size=(320, 240)):
    self.surface = pygame.Surface(size, depth=8)
    self.surface.set_colorkey(0)
    self.surface.set_palette_at(0, (255, 255, 255))

  def set_palette_at(self, index, color):
    self.surface.set_palette_at(index, color)

  def set_pixels(self, pixels):
    pixels = np.swapaxes(pixels.astype(np.uint8), 0, 1)
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
  with open(argv[2], "rb") as f: table1 = f.read()
  with open(argv[3], "rb") as f: table3 = f.read()
  with open(argv[4], "rb") as f: table4 = f.read()
  with open(argv[5], "rb") as f: linedefs = f.read()

  parser = KWZParser(kwz, table1, table3, table4, linedefs)

  palette = [
    (0xff, 0xff, 0xff),
    (0x14, 0x14, 0x14),
    (0xff, 0x17, 0x17),
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
  frameIndex = 0

  while not done:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        done = True

    frame.set_layers(parser.decode_frame(frameIndex))
    frame.set_colors(parser.get_frame_palette(frameIndex), palette)
    frameIndex += 1

    frame.blit_to(screen, (0, 0))
    pygame.display.flip()