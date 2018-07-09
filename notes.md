### Tile Compression

Layers are divided into 1200 8x8 tiles which are compressed individually. An uncompressed tile is comprised of 8 values which each represent a horizontal line of 8 pixels. 

Every compressed tile starts with a 3-bit value which describes the compression method used:

#### Tile types

**Type 0**

A single 5-bit offset into the common line table. The result is used for all 8 lines of the tile.

**Type 1**

A single 13-bit value, used for all 8 lines of the tile.

**Type 4**

Uses an 8-bit mask, with each bit representing a line in the tile. If the bit is set to `1`, this line uses a 5-bit offset into the common line table, otherwise this line uses a 13-bit line value.

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