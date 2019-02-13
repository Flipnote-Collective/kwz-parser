Experimental decoder and utilities (image/video conversion, etc) for Flipnote Studio 3D's .kwz animation format. Frames and audio can both be decoded without any problems.

All scripts were written for Python 3.7 and require the [numpy](http://www.numpy.org/) module to be installed.

#### Credits

* **[Jaames](https://github.com/jaames)** - general reverse-engineering and python implementation
* **[Kinnay](https://github.com/Kinnay)** - reverse-engineering tile compression
* **[Khangaroo](https://github.com/khang06)** - reverse-engineering a large chunk of the audio format
* **[Shutterbug](https://github.com/shutterbug2000)** - early decompression and frame diffing work
* **[MrNbaYoh](https://github.com/MrNbaYoh)** - identifying the use of a line table
* **[Stary](https://github.com/stary2001)**, **[JoshuaDoes](https://github.com/JoshuaDoes)** and **[thejsa](https://github.com/thejsa)** - debugging/optimisation help
* **[Sudofox](https://github.com/sudofox)** - audio format help and comment sample files

## Utilities

### kwzImage

Converts specific kwz frames as well folder icons and Flipnote Gallery World comments (.kwc) to standard image formats such as png, gif, jpeg, etc. Requires the [Pillow](https://pillow.readthedocs.io/en/5.2.x/) module to be installed.

Usage: 

```bash
python kwzImage.py <input path> <frame index> <output path>
```

`<frame index>`:
  
 * Specific frame index (e.g. `0` for the first frame)
 * `thumb` to get the thumbnail frame
 * `gif` to encode the whole Flipnote to an animated GIF.

`<output path>`:

 * Can include placeholders: `{name}` for the input filename (without extention), `{ext}` for input extention, `{index}` for the item index and `{dirname}` for the input file directory.

`<input path>`:

 * You can pass glob patterns as the input filepath to batch convert. For example, the following will extract thumbnail images from all the kwzs in a directory:

	```bash
	python kwzImage.py "/flipnotes/*.kwz" thumb /flipnotes/{name}.png
	```

### kwzVideo

Experimental kwz to mp4 encoder using [ffmpeg](https://www.ffmpeg.org/). Tries to ensure optimal compression and image quality while also upscaling the Flipntote to 480p.

Usage: 

```bash
python kwzVideo.py <input.kwz> <output.kwz>
```

### kwzAudio

Exports a Flipnote audio track and converts it to WAV.

**Usage:**

```bash
python kwzAudio.py <input.kwz> <track id> <output.wav>
```

Where `<track id>` is `0` for BGM, or `1` - `4` for SE1 - SE4.

### kwzViewer

Crappy viewer made with [pygame](https://www.pygame.org/news). It doesn't quite achieve realtime decoding for most Flipnotes, but it can be useful as a quick debug tool.

**Usage:**

```bash
python kwzViewer.py <input.kwz>
```
