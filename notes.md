### Frame Meta

The first 4 bits of a frame's meta entry indicate whether or not it is necessary to decode the previous frame first. 

If the highest bit is `0`, then there is only one frame/no previous frames are ever used (it seems to always be `1` except in kwc and ico files).
The following bits are set to `0` if a layer is based on the previous frame, in order of Layer C, Layer B, Layer A.

### Tile Compression

Layers are divided into 1200 8x8 tiles. An uncompressed tile is comprised of 8 offsets, each representing an 8-pixel horizontal line. Offsets can then be converted into pixels using table2, which contains every possible combination of pixels for a line.

A compressed tile starts with a 3-bit value which describes the compression method used:

#### Tile types

**Type 0**

A single 5-bit offset into table 4. The result is used for all 8 lines of the tile.

**Type 1**

A single 13-bit value, used for all 8 lines of the tile.

**Type 2**

Obfuscation? Psuedocode to read tile:

```python
index1 = read_bits(5)
index2 = ROR(table3[index1], 4)
v1 = table1[index2 & 0xFF]
v2 = table1[(index2 >> 8) & 0xFF]
v3 = table1[(index2 >> 16) & 0xFF]
v4 = table1[index2 >> 24]
X = table4[index1]
Y = ((v1 * 9 + v2) * 9 + v3) * 9 + v4
```

The result is then a line pattern of `X Y X Y X Y X Y`

**Type 3**

Obfuscation? Psuedocode to read tile:

```python
X = read_bits(13)
index = ROR(table2[X], 4)
v1 = table1[index & 0xFF]
v2 = table1[(index >> 8) & 0xFF]
v3 = table1[(index >> 16) & 0xFF]
v4 = table1[index >> 24]
Y = ((v1 * 9 + v2) * 9 + v3) * 9 + v4
```

The result is then a line pattern of `X Y X Y X Y X Y`

**Type 4**

Uses an 8-bit mask, with each bit representing a line in the tile. If the bit is set to `1`, this line uses a 5-bit offset into the common line table, otherwise this line uses a 13-bit line value.

**Type 5**

Indicates a series of one or more tiles haven't changed since the previous frame, so they can be skipped. The number of tiles to skip is given by a a 5-bit value which should be incremented by 1.

**Type 6**

Not used.

**Type 7**

The lines in this tile are arranged in a pattern of two values (X and Y). A 2-bit value describes the pattern type (detailed below), followed by a 1-bit value.

If the 1-bit value is set to `1`, then X and Y should be read as 5-bit offsets into the common line table, and the pattern type should also be incremented by 1.

If the 1-bit value is `0`, then X and Y should be read as 13-bit line values.


| Pattern Type | Pattern |
|:-------------|:--------|
| 0 | `X Y X Y X Y X Y` |
| 1 | `X X Y X X Y X X` |
| 2 | `X Y X X Y X X Y` |
| 3 | `X Y Y X Y Y X Y` |