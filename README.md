# Binary Image RLE Codec

A small Python application for drawing, storing, and compressing black-and-white images with run-length encoding (RLE). It includes a Tkinter desktop editor and a reusable codec for binary pixel data.

## Features

- Draw binary images in a Tkinter GUI.
- Paint black pixels with the left mouse button.
- Paint white pixels with the right mouse button.
- Create images from 1×1 up to 256×256 pixels in the editor.
- Save and load uncompressed binary images using the `.bimg` format.
- Compress and decompress images using the `.rle` format.
- Validate image dimensions, pixel values, packet lengths, and decoded output size.
- Split long runs into packets when they exceed the maximum packet size.
- Display the current image dimensions and black/white pixel counts.

## Requirements

- Python 3.10 or newer
- Tkinter

Tkinter is included with most Python installations. On some Linux distributions, it must be installed separately, for example with the `python3-tk` package.

## Run the application

From the repository directory, run:

```bash
python3 main.py
```

The editor starts with a 32×24 white image.

### Editor controls

- **New image**: creates a blank white image using the selected dimensions.
- **Open**: loads an uncompressed `.bimg` image.
- **Save image**: saves the current image as `.bimg`.
- **Compress and save**: encodes the current image and saves it as `.rle`.
- **Decompress / open**: decodes an `.rle` image and opens it in the editor.
- **Left mouse button**: paints black pixels.
- **Right mouse button**: paints white pixels.

The canvas includes scrollbars for images that do not fit in the window.

## Python API

The project is split into two reusable modules:

### `rle_codec.py`

Provides the raw RLE implementation:

```python
from rle_codec import decode, encode

pixels = bytes([0x00, 0x00, 0x00, 0xFF, 0xFF])
encoded = encode(pixels)
decoded = decode(encoded, expected_pixels=len(pixels))

assert decoded == pixels
```

`encode()` accepts a row-major `bytes` object containing only `0x00` (black) and `0xFF` (white). `decode()` reconstructs the pixel stream and can optionally verify the expected number of pixels.

Invalid data raises `CodecError`.

### `image_file.py`

Provides file-level helpers:

```python
from image_file import load_compressed, load_image, save_compressed, save_image

save_image("image.bimg", width, height, pixels)
save_compressed("image.rle", width, height, pixels)

width, height, pixels = load_image("image.bimg")
width, height, pixels = load_compressed("image.rle")
```

Image dimensions must be positive, the pixel count must equal `width * height`, and the total image size is limited to 100,000,000 pixels by the file-format layer.

## File formats

Both file formats use a 12-byte big-endian header:

| Offset | Size | Description |
|---:|---:|---|
| 0 | 4 bytes | File signature: `BIMG` or `RLE1` |
| 4 | 4 bytes | Width as an unsigned 32-bit integer |
| 8 | 4 bytes | Height as an unsigned 32-bit integer |
| 12 | variable | Image data |

### `.bimg`

A `.bimg` file stores the raw row-major pixel bytes after the header. Each pixel must be either:

- `0x00` for black
- `0xFF` for white

### `.rle`

An `.rle` file stores an RLE stream after the header. Each packet begins with a 16-bit big-endian word:

- Bit 15: packet type (`1` for a run packet, `0` for a literal packet)
- Bits 0–14: number of pixels in the packet

A run packet is followed by one pixel byte. A literal packet is followed by the specified number of pixel bytes.

Runs of three or more identical pixels are encoded as run packets. Shorter sequences are grouped into literal packets. Each packet can contain up to 32,767 pixels; longer runs are split across multiple packets.

## Project structure

```text
.
├── image_file.py  # .bimg and .rle file I/O
├── main.py        # Tkinter graphical editor
├── rle_codec.py   # RLE encoder and decoder
└── README.md
```

## Error handling

Malformed files and invalid pixel data raise `CodecError`. Examples include truncated headers or packets, invalid file signatures, unsupported pixel values, zero-length packets, dimension mismatches, and decoded streams that do not contain the declared number of pixels.

## License

No license file is currently included in this repository. Add a license before distributing or reusing the project publicly under specific terms.
