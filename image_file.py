"""Simple portable file formats used by the binary image editor."""

from __future__ import annotations

import struct
from pathlib import Path

import cv2
import numpy as np

from rle_codec import CodecError, decode, decode_with_trace, encode, encode_with_trace

IMAGE_MAGIC = b"BIMG"
RLE_MAGIC = b"RLE1"
HEADER = struct.Struct(">4sII")
MAX_PIXELS = 100_000_000


def _check_dimensions(width: int, height: int) -> None:
    if width < 1 or height < 1:
        raise CodecError("Image width and height must be positive")
    if width * height > MAX_PIXELS:
        raise CodecError(f"Images are limited to {MAX_PIXELS:,} pixels")


def save_image(path: str | Path, width: int, height: int, pixels: bytes) -> None:
    _check_dimensions(width, height)
    if len(pixels) != width * height:
        raise CodecError("Pixel count does not match image dimensions")
    Path(path).write_bytes(HEADER.pack(IMAGE_MAGIC, width, height) + pixels)


def load_image(path: str | Path) -> tuple[int, int, bytes]:
    data = Path(path).read_bytes()
    if len(data) < HEADER.size:
        raise CodecError("Image file is too short")
    magic, width, height = HEADER.unpack_from(data)
    if magic != IMAGE_MAGIC:
        raise CodecError("Not a BIMG binary image file")
    _check_dimensions(width, height)
    pixels = data[HEADER.size :]
    if len(pixels) != width * height:
        raise CodecError("Image file pixel count does not match its dimensions")
    if any(pixel not in (0, 255) for pixel in pixels):
        raise CodecError("Image file contains a value other than 0 or 255")
    return width, height, pixels


def save_compressed(path: str | Path, width: int, height: int, pixels: bytes) -> None:
    _check_dimensions(width, height)
    if len(pixels) != width * height:
        raise CodecError("Pixel count does not match image dimensions")
    body = encode(pixels)
    Path(path).write_bytes(HEADER.pack(RLE_MAGIC, width, height) + body)


def save_compressed_with_trace(
    path: str | Path, width: int, height: int, pixels: bytes
) -> list[str]:
    _check_dimensions(width, height)
    if len(pixels) != width * height:
        raise CodecError("Pixel count does not match image dimensions")
    body, trace = encode_with_trace(pixels)
    Path(path).write_bytes(HEADER.pack(RLE_MAGIC, width, height) + body)
    return trace


def load_compressed(path: str | Path) -> tuple[int, int, bytes]:
    data = Path(path).read_bytes()
    if len(data) < HEADER.size:
        raise CodecError("Compressed file is too short")
    magic, width, height = HEADER.unpack_from(data)
    if magic != RLE_MAGIC:
        raise CodecError("Not an RLE1 compressed image")
    _check_dimensions(width, height)
    pixels = decode(data[HEADER.size :], width * height)
    return width, height, pixels


def load_compressed_with_trace(
    path: str | Path,
) -> tuple[int, int, bytes, list[str]]:
    data = Path(path).read_bytes()
    if len(data) < HEADER.size:
        raise CodecError("Compressed file is too short")
    magic, width, height = HEADER.unpack_from(data)
    if magic != RLE_MAGIC:
        raise CodecError("Not an RLE1 compressed image")
    _check_dimensions(width, height)
    pixels, trace = decode_with_trace(data[HEADER.size :], width * height)
    return width, height, pixels, trace


def load_png(path: str | Path) -> tuple[int, int, bytes]:
    """Read a regular image with OpenCV and convert it to black/white pixels."""
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise CodecError("OpenCV could not read this image")
    height, width = image.shape
    _check_dimensions(width, height)
    _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
    return width, height, binary.tobytes()


def save_png(path: str | Path, width: int, height: int, pixels: bytes) -> None:
    """Write the binary image as a PNG using OpenCV."""
    _check_dimensions(width, height)
    if len(pixels) != width * height:
        raise CodecError("Pixel count does not match image dimensions")
    image = np.frombuffer(pixels, dtype=np.uint8).reshape((height, width))
    if not cv2.imwrite(str(path), image):
        raise CodecError("OpenCV could not write the PNG image")
