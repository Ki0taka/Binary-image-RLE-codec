"""RLE codec for binary images as described in Projet1.pdf.

Each packet starts with a two-byte big-endian word. Bit 15 marks a run
packet; the remaining 15 bits store its pixel count. Literal packets have
bit 15 clear and are followed by that many pixel bytes.
"""

from __future__ import annotations

MAX_PACKET_LENGTH = 0x7FFF
BLACK = 0x00
WHITE = 0xFF


class CodecError(ValueError):
    """Raised when image data or an RLE stream is invalid."""


def _validate_pixels(pixels: bytes) -> None:
    if any(pixel not in (BLACK, WHITE) for pixel in pixels):
        raise CodecError("Binary images may contain only 0x00 and 0xFF pixels")


def encode(pixels: bytes) -> bytes:
    """Encode a row-major binary pixel byte string."""
    _validate_pixels(pixels)
    out = bytearray()
    pos = 0
    size = len(pixels)

    while pos < size:
        run_end = pos + 1
        while run_end < size and pixels[run_end] == pixels[pos]:
            run_end += 1
        run_length = run_end - pos

        if run_length >= 3:
            # A long run is emitted in packets of at most 32767 pixels.
            remaining = run_length
            while remaining:
                count = min(remaining, MAX_PACKET_LENGTH)
                out.extend((0x8000 | count).to_bytes(2, "big"))
                out.append(pixels[pos])
                pos += count
                remaining -= count
            continue

        # Accumulate literals (including pairs) up to, but never across, a
        # run of three or more equal pixels.
        literal_start = pos
        pos = run_end
        while pos < size and pos - literal_start < MAX_PACKET_LENGTH:
            next_end = pos + 1
            while next_end < size and pixels[next_end] == pixels[pos]:
                next_end += 1
            if next_end - pos >= 3:
                break
            take = min(next_end - pos, MAX_PACKET_LENGTH - (pos - literal_start))
            pos += take
            if take < next_end - (pos - take):
                break

        count = pos - literal_start
        out.extend(count.to_bytes(2, "big"))
        out.extend(pixels[literal_start:pos])

    return bytes(out)


def decode(stream: bytes, expected_pixels: int | None = None) -> bytes:
    """Decode an RLE stream, optionally enforcing the image's pixel count."""
    out = bytearray()
    pos = 0
    while pos < len(stream):
        if len(stream) - pos < 2:
            raise CodecError("Truncated packet header")
        word = int.from_bytes(stream[pos : pos + 2], "big")
        pos += 2
        is_run = bool(word & 0x8000)
        count = word & MAX_PACKET_LENGTH
        if count == 0:
            raise CodecError("Packet length cannot be zero")

        if is_run:
            if pos >= len(stream):
                raise CodecError("Truncated run packet")
            pixel = stream[pos]
            pos += 1
            if pixel not in (BLACK, WHITE):
                raise CodecError("Invalid pixel value in run packet")
            out.extend(bytes((pixel,)) * count)
        else:
            end = pos + count
            if end > len(stream):
                raise CodecError("Truncated literal packet")
            literal = stream[pos:end]
            _validate_pixels(literal)
            out.extend(literal)
            pos = end

        if expected_pixels is not None and len(out) > expected_pixels:
            raise CodecError("Decoded image is larger than its declared dimensions")

    if expected_pixels is not None and len(out) != expected_pixels:
        raise CodecError(
            f"Decoded {len(out)} pixels, expected {expected_pixels}"
        )
    return bytes(out)
