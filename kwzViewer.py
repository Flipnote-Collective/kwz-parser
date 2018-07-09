from sys import argv
from kwz import KWZParser
import numpy as np
import pygame

class layerSurface:
  def __init__(self, size=(320, 240)):
    self.surface = pygame.Surface(size, depth=8)
    self.surface.set_colorkey(0)
    self.surface.set_palette_at(0, (255, 255, 255))

  def set_palette_at(self, index, color):
    self.surface.set_palette_at(index, color)

  def set_pixels(self, pixels):
    pixels = np.swapaxes(pixels, 0, 1)
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

    frame.set_layers(parser.decode_frame(frame_index))
    frame.set_colors(parser.get_frame_palette(frame_index), palette)
    # print("Decoded frame:", frameIndex, "flag:", parser.get_frame_flag(frameIndex))
    if frame_index == parser.frame_count - 1:
      frame_index = 0
    else:
      frame_index += 1

    frame.blit_to(screen, (0, 0))
    pygame.display.flip()