"""Simple portable file formats used by the binary image editor."""

from __future__ import annotations

import struct
from pathlib import Path

from rle_codec import CodecError, decode, encode

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
