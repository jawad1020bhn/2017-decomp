#!/usr/bin/env python3
"""CPK (CRI PAK) archive dumper/extractor.

Handles the @UTF column-descriptor variant used by "PES CPK TOOL by StpN_17"
(5-byte descriptors: u8 flags + u32 name offset, values laid out sequentially
in each row for columns flagged 0x5X) and the classic 7-byte descriptor form.

Usage:
  python3 cpk_dump.py ARCHIVE.cpk            # list contents
  python3 cpk_dump.py ARCHIVE.cpk -x OUTDIR  # list + extract
"""
import argparse
import os
import struct
import sys

TYPE_SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 0xA: 4, 0xB: 8}


def crilayla_decompress(blob):
    """CRILAYLA: body is decoded BACKWARDS (file end -> start).

    Layout: "CRILAYLA" | u32 body_size | u32 stream_len | stream | raw 0x100 header.
    The first 0x100 output bytes are stored raw after the stream. Bits are read
    from the last stream byte backwards, MSB-first. Tokens: 1 bit flag
    (1 = match: 13-bit dist (+3) + gamma-coded length; 0 = literal: 8 bits).
    """
    if blob[:8] != b"CRILAYLA":
        raise ValueError("not CRILAYLA")
    body_size = struct.unpack_from("<I", blob, 8)[0]
    stream_len = struct.unpack_from("<I", blob, 12)[0]
    total = body_size + 0x100
    out = bytearray(total)
    out[:0x100] = blob[0x10 + stream_len:0x10 + stream_len + 0x100]
    stream = blob[0x10:0x10 + stream_len]

    remaining, pool, left, failed = stream_len, 0, 0, False

    def take(n):
        nonlocal remaining, pool, left, failed
        v = 0
        while n:
            if left == 0:
                if remaining == 0:
                    failed = True
                    return 0
                remaining -= 1
                pool = stream[remaining]
                left = 8
            now = min(n, left)
            v = (v << now) | ((pool >> (left - now)) & ((1 << now) - 1))
            left -= now
            n -= now
        return v

    written = 0
    while written < body_size:
        if take(1):
            dist = take(13) + 3
            ln, done = 3, False
            for w in (2, 3, 5):
                v = take(w)
                ln += v
                if v != (1 << w) - 1:
                    done = True
                    break
            while not done:
                v = take(8)
                ln += v
                if v != 255:
                    done = True
                if failed or ln > body_size - written:
                    break
            if failed or dist > written or ln > body_size - written:
                raise ValueError("corrupt CRILAYLA stream")
            dest = total - 1 - written
            for i in range(ln):
                out[dest - i] = out[dest - i + dist]
            written += ln
        else:
            v = take(8)
            if failed:
                raise ValueError("corrupt CRILAYLA stream")
            out[total - 1 - written] = v
            written += 1
    return bytes(out)


def parse_utf(data, tbl_off):
    """Parse an @UTF table whose '@UTF' magic sits at tbl_off + 0x10."""
    base = tbl_off + 0x10
    if data[base:base + 4] != b"@UTF":
        raise ValueError("no @UTF table at %#x" % tbl_off)
    tsize, rows_off, strs_off, dats_off, name_off, ncols, rlen, nrows = \
        struct.unpack_from(">IIIIIHHI", data, base + 4)
    strs_base = base + 8 + strs_off
    rows_base = base + 8 + rows_off

    def cstr(s_off):
        end = data.find(b"\0", strs_base + s_off)
        return data[strs_base + s_off:end].decode("utf-8", "replace")

    # column descriptors: 5 bytes (this tool) or 7 bytes (classic CRI @UTF)
    col_region = rows_base - (base + 0x20)
    desc_size = col_region // ncols if ncols else 0
    if desc_size not in (5, 7):
        raise ValueError(f"unexpected column descriptor size {desc_size}")

    cols = []
    p = base + 0x20
    for _ in range(ncols):
        flags = data[p]
        if desc_size == 5:
            (noff,) = struct.unpack_from(">I", data, p + 1)
        else:
            (noff,) = struct.unpack_from(">H", data, p + 1)
        cols.append((cstr(noff), flags))
        p += desc_size

    rows_out = []
    for r in range(nrows):
        rp = rows_base + r * rlen
        row = {}
        for cname, flags in cols:
            t = flags & 0x0F
            storage = flags & 0xF0
            if storage == 0x50 or (desc_size == 7 and storage == 0x00):
                if t in (6, 7):
                    v = struct.unpack_from(">Q", data, rp)[0]
                    rp += 8
                elif t == 4:
                    v = struct.unpack_from(">I", data, rp)[0]
                    rp += 4
                elif t == 2:
                    v = struct.unpack_from(">H", data, rp)[0]
                    rp += 2
                elif t == 0:
                    v = data[rp]
                    rp += 1
                elif t == 0xA:
                    (so,) = struct.unpack_from(">I", data, rp)
                    rp += 4
                    v = cstr(so)
                elif t == 0xB:
                    off, ln = struct.unpack_from(">II", data, rp)
                    rp += 8
                    v = ("blob", off, ln)
                else:
                    v = data[rp:rp + TYPE_SIZE[t]].hex()
                    rp += TYPE_SIZE[t]
                row[cname] = v
            else:
                row[cname] = None  # constant/zero column (value not needed here)
        rows_out.append(row)
    return {"name": cstr(name_off), "cols": cols, "rows": rows_out,
            "nrows": nrows, "rlen": rlen, "end": base + 8 + tsize}


def main():
    ap = argparse.ArgumentParser(description="Dump/extract a CPK archive")
    ap.add_argument("cpk")
    ap.add_argument("-x", "--extract", metavar="OUTDIR", help="extract files")
    args = ap.parse_args()

    with open(args.cpk, "rb") as f:
        data = f.read()
    if data[:4] != b"CPK ":
        sys.exit("error: not a CPK file")

    hdr = parse_utf(data, 0x0)["rows"][0]
    content_off = hdr.get("ContentOffset") or 0
    toc_off = hdr.get("TocOffset")
    print(f"CPK header: Files={hdr.get('Files')} ContentOffset={content_off:#x} "
          f"TocOffset={toc_off:#x} Tvers={hdr.get('Tvers')!r}")

    toc = parse_utf(data, toc_off)
    entries = toc["rows"]
    print(f"TOC {toc['name']!r}: {len(entries)} entries\n")

    print(f"{'#':>3}  {'ID':>5}  {'packed':>9}  {'unpacked':>9}  {'offset':>9}  Name")
    for i, e in enumerate(entries):
        name = e.get("FileName", "?")
        d = e.get("DirName") or ""
        if d and d != ".":
            name = f"{d}/{name}"
        print(f"{i:>3}  {e.get('ID', 0):>5}  {e.get('FileSize', 0):>9}  "
              f"{e.get('ExtractSize', 0):>9}  {e.get('FileOffset', 0):>9}  {name}")

    if args.extract:
        os.makedirs(args.extract, exist_ok=True)
        for e in entries:
            name = e.get("FileName", "unnamed")
            d = e.get("DirName") or ""
            if d and d != ".":
                name = f"{d}/{name}"
            size = e.get("FileSize", 0)
            off = e.get("FileOffset", 0)
            blob = data[content_off + off:content_off + off + size] if size else b""
            if blob[:8] == b"CRILAYLA":
                blob = crilayla_decompress(blob)
            out = os.path.join(args.extract, name.replace("\\", "/"))
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with open(out, "wb") as f:
                f.write(blob)
        print(f"\nextracted to {args.extract}")


if __name__ == "__main__":
    main()
