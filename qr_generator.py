#!/usr/bin/env python3
"""Pure Python QR code generator.

This script generates a Version 1 QR code (error correction level L) using only
built-in Python modules. The resulting image is written as a simple binary PPM
file so that no external image libraries are required.
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, List

from PIL import Image


# ---------------------------- GF(256) arithmetic ----------------------------
# The QR code specification uses GF(256) with the primitive polynomial
# x^8 + x^4 + x^3 + x^2 + 1 (0x11D).  The tables below provide fast
# multiplication and exponentiation.
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256

x = 1
for i in range(255):
    _GF_EXP[i] = x
    _GF_LOG[x] = i
    x <<= 1
    if x & 0x100:
        x ^= 0x11D
for i in range(255, 512):
    _GF_EXP[i] = _GF_EXP[i - 255]


def _gf_mul(x: int, y: int) -> int:
    if x == 0 or y == 0:
        return 0
    return _GF_EXP[_GF_LOG[x] + _GF_LOG[y]]


# -------------------------- Reed-Solomon coding -----------------------------

def _rs_generator_poly(ec_len: int) -> List[int]:
    g = [1]
    for i in range(ec_len):
        g = _poly_mul(g, [1, _GF_EXP[i]])
    return g


def _poly_mul(p: Iterable[int], q: Iterable[int]) -> List[int]:
    res = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            res[i + j] ^= _gf_mul(a, b)
    return res


def _rs_compute(data: List[int], ec_len: int) -> List[int]:
    gen = _rs_generator_poly(ec_len)
    res = [0] * ec_len
    for byte in data:
        factor = byte ^ res[0]
        res = res[1:] + [0]
        for i, g in enumerate(gen[1:]):
            res[i] ^= _gf_mul(g, factor)
    return res


# --------------------------- QR matrix helpers ------------------------------
QR_VERSIONS = [
    (1, 21, 19, 7),
    (2, 25, 34, 10),
    (3, 29, 55, 15),
    (4, 33, 80, 20),
]


def _empty_matrix(size: int) -> List[List[int | None]]:
    return [[None for _ in range(size)] for _ in range(size)]


def _add_finder_pattern(mat: List[List[int]], x: int, y: int) -> None:
    pattern = [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 0, 1],
        [1, 0, 1, 1, 1, 0, 1],
        [1, 0, 1, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1],
    ]
    for dy, row in enumerate(pattern):
        for dx, val in enumerate(row):
            mat[y + dy][x + dx] = val


def _add_separators(mat: List[List[int]], x: int, y: int, size: int) -> None:
    for i in range(8):
        if 0 <= y + i < size and x - 1 >= 0:
            mat[y + i][x - 1] = 0
        if 0 <= y + i < size and x + 7 < size:
            mat[y + i][x + 7] = 0
        if 0 <= x + i < size and y - 1 >= 0:
            mat[y - 1][x + i] = 0
        if 0 <= x + i < size and y + 7 < size:
            mat[y + 7][x + i] = 0


def _add_timing_patterns(mat: List[List[int]], size: int) -> None:
    for i in range(8, size - 8):
        val = i % 2
        mat[6][i] = val
        mat[i][6] = val


def _reserve_format_info(mat: List[List[int]], size: int) -> None:
    for i in range(9):
        if mat[8][i] is None:
            mat[8][i] = 0
        if mat[i][8] is None:
            mat[i][8] = 0
    for i in range(8):
        mat[size - 1 - i][8] = 0
        mat[8][size - 1 - i] = 0
    mat[size - 8][8] = 1  # Dark module


def _set_data_bits(mat: List[List[int]], bits: List[int], size: int) -> None:
    i = 0
    x = size - 1
    y = size - 1
    direction = -1
    while x > 0:
        if x == 6:
            x -= 1
        for _ in range(size):
            for dx in (0, -1):
                col = x + dx
                if mat[y][col] is None:
                    bit = bits[i] if i < len(bits) else 0
                    if (col + y) % 2 == 0:  # mask pattern 0
                        bit ^= 1
                    mat[y][col] = bit
                    i += 1
            y += direction
            if y < 0 or y >= size:
                y -= direction
                break
        direction *= -1
        x -= 2
    if i < len(bits):
        raise ValueError("Data did not fit in matrix")


# --------------------------- Format information ----------------------------
FORMAT_BITS = 0b111011111000100  # Level L, mask 0


def _add_format_info(mat: List[List[int]], size: int) -> None:
    bits = [int(b) for b in f"{FORMAT_BITS:015b}"]
    # Top-left
    for i in range(6):
        mat[8][i] = bits[i]
    mat[8][7] = bits[6]
    mat[8][8] = bits[7]
    mat[7][8] = bits[8]
    for i in range(6):
        mat[5 - i][8] = bits[9 + i]

    # Top-right
    for i in range(8):
        mat[i][size - 8] = bits[i]
    for i in range(7):
        mat[size - 8][i + 1] = bits[8 + i]


# --------------------------- Image output ----------------------------------

def _write_ppm(mat: List[List[int]], path: str, scale: int = 10) -> None:
    size = len(mat) * scale
    with open(path, "wb") as f:
        f.write(f"P6\n{size} {size} 255\n".encode())
        for row in mat:
            for _ in range(scale):
                line = bytearray()
                for module in row:
                    val = 0 if module else 255
                    line.extend(bytes([val, val, val]) * scale)
                f.write(line)


def _write_jpeg(mat: List[List[int]], path: str, scale: int = 10) -> None:
    size = len(mat) * scale
    img = Image.new("L", (size, size), 255)
    pixels = img.load()
    for y, row in enumerate(mat):
        for x, module in enumerate(row):
            val = 0 if module else 255
            for dy in range(scale):
                for dx in range(scale):
                    pixels[x * scale + dx, y * scale + dy] = val
    img.save(path, "JPEG")


def _add_alignment_patterns(mat: list, version: int, size: int):
    # Alignment pattern locations for versions 2-4 (from QR spec)
    ALIGNMENT_LOC = {
        2: [6, 18],
        3: [6, 22],
        4: [6, 26],
    }
    if version < 2:
        return
    locs = ALIGNMENT_LOC[version]
    for y in locs:
        for x in locs:
            # Skip if overlaps with finder pattern
            if (x <= 8 and y <= 8) or (x <= 8 and y >= size - 8) or (x >= size - 8 and y <= 8):
                continue
            # Draw alignment pattern (5x5)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if 0 <= y+dy < size and 0 <= x+dx < size:
                        if abs(dx) == 2 or abs(dy) == 2 or (dx == 0 and dy == 0):
                            mat[y+dy][x+dx] = 1
                        else:
                            mat[y+dy][x+dx] = 0


# --------------------------- High level API --------------------------------

def generate_qr(data: str, output_file: str) -> None:
    """Generate a QR code and save it as a PPM image."""
    data_bytes = data.encode("iso-8859-1")
    bits = []
    bits.extend([0, 1, 0, 0])  # Mode indicator
    count = len(data_bytes)
    bits.extend(int(b) for b in f"{count:08b}")
    for b in data_bytes:
        bits.extend(int(x) for x in f"{b:08b}")
    bits.extend([0, 0, 0, 0])  # Terminator
    while len(bits) % 8 != 0:
        bits.append(0)
    # Select version
    for version, size, data_cw, ec_cw in QR_VERSIONS:
        if len(bits) // 8 <= data_cw:
            break
    else:
        raise ValueError("Data too long for Version 4 QR code")
    # Pad bytes
    data_codewords = []
    for i in range(0, len(bits), 8):
        data_codewords.append(int("".join(str(x) for x in bits[i:i+8]), 2))
    pad_bytes = [0xEC, 0x11]
    while len(data_codewords) < data_cw:
        data_codewords.append(pad_bytes[len(data_codewords) % 2])
    ec_codewords = _rs_compute(data_codewords, ec_cw)
    codewords = data_codewords + ec_codewords
    bit_stream = []
    for cw in codewords:
        bit_stream.extend(int(b) for b in f"{cw:08b}")
    mat = _empty_matrix(size)
    _add_finder_pattern(mat, 0, 0)
    _add_finder_pattern(mat, size - 7, 0)
    _add_finder_pattern(mat, 0, size - 7)
    _add_separators(mat, 0, 0, size)
    _add_separators(mat, size - 7, 0, size)
    _add_separators(mat, 0, size - 7, size)
    _add_alignment_patterns(mat, version, size)
    _add_timing_patterns(mat, size)
    _reserve_format_info(mat, size)
    _set_data_bits(mat, bit_stream, size)
    _add_format_info(mat, size)
    if output_file.lower().endswith('.jpg') or output_file.lower().endswith('.jpeg'):
        _write_jpeg(mat, output_file, scale=10)
    else:
        _write_ppm(mat, output_file, scale=10)


# --------------------------- CLI interface ---------------------------------

def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a QR code image")
    parser.add_argument("data", help="Data to encode")
    parser.add_argument("output", help="Output PPM file")
    args = parser.parse_args(argv)
    try:
        generate_qr(args.data, args.output)
    except Exception as exc:  # pragma: no cover - generic runtime errors
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"QR code saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
