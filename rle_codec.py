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
    return encode_with_trace(pixels)[0]


def encode_with_trace(pixels: bytes) -> tuple[bytes, list[str]]:
    """Encode pixels and explain each emitted packet for the GUI."""
    _validate_pixels(pixels)
    out = bytearray()
    trace: list[str] = []
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
                tail = remaining - count
                if 0 < tail < 3:
                    count -= 3 - tail
                word = 0x8000 | count
                trace.append(
                    f"Packet {len(trace) + 1}: RUN — pixels {pos}..{pos + count - 1}\n"
                    f"  Repeated value: {pixels[pos]} ({'black' if pixels[pos] == BLACK else 'white'})\n"
                    f"  Count: {count} = {count:015b}\n"
                    f"  Header: 1 | {count:015b} = {word:016b} (0x{word:04X})\n"
                    f"  Payload: {pixels[pos]:02X}"
                )
                out.extend(word.to_bytes(2, "big"))
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
        word = count
        literal = pixels[literal_start:pos]
        preview = " ".join(f"{value:02X}" for value in literal[:32])
        if len(literal) > 32:
            preview += f" … ({len(literal) - 32} more bytes)"
        trace.append(
            f"Packet {len(trace) + 1}: LITERAL — pixels {literal_start}..{pos - 1}\n"
            f"  Count: {count} = {count:015b}\n"
            f"  Header: 0 | {count:015b} = {word:016b} (0x{word:04X})\n"
            f"  Pixel bytes (first 32): {preview}"
        )
        out.extend(word.to_bytes(2, "big"))
        out.extend(literal)

    return bytes(out), trace


def decode(stream: bytes, expected_pixels: int | None = None) -> bytes:
    """Decode an RLE stream, optionally enforcing the image's pixel count."""
    return decode_with_trace(stream, expected_pixels)[0]


def decode_with_trace(
    stream: bytes, expected_pixels: int | None = None
) -> tuple[bytes, list[str]]:
    """Decode an RLE stream and explain how every packet is interpreted."""
    out = bytearray()
    trace: list[str] = []
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
            trace.append(
                f"Packet {len(trace) + 1}: RUN — header {word:016b} (0x{word:04X})\n"
                f"  Flag: 1 (repeat), count: {count}\n"
                f"  Payload byte: {pixel:02X} ({'black' if pixel == BLACK else 'white'})\n"
                f"  Write {count} pixels at output positions {len(out)}..{len(out) + count - 1}"
            )
            out.extend(bytes((pixel,)) * count)
        else:
            end = pos + count
            if end > len(stream):
                raise CodecError("Truncated literal packet")
            literal = stream[pos:end]
            _validate_pixels(literal)
            preview = " ".join(f"{value:02X}" for value in literal[:32])
            if len(literal) > 32:
                preview += f" … ({len(literal) - 32} more bytes)"
            trace.append(
                f"Packet {len(trace) + 1}: LITERAL — header {word:016b} (0x{word:04X})\n"
                f"  Flag: 0 (literal), count: {count}\n"
                f"  Payload bytes (first 32): {preview}\n"
                f"  Write {count} pixels at output positions {len(out)}..{len(out) + count - 1}"
            )
            out.extend(literal)
            pos = end

        if expected_pixels is not None and len(out) > expected_pixels:
            raise CodecError("Decoded image is larger than its declared dimensions")

    if expected_pixels is not None and len(out) != expected_pixels:
        raise CodecError(
            f"Decoded {len(out)} pixels, expected {expected_pixels}"
        )
    return bytes(out), trace
