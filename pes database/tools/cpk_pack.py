#!/usr/bin/env python3
"""Build an enhanced 'Realistic Gameplay Update.cpk' from the original CPK.

Self-contained pipeline (no extracted-folder input):
  1. parse original CPK (CpkHeader + TOC + GTOC + ETOC) with utf_table.py;
  2. decode every entry in memory (CRILAYLA -> content; raw -> as-is);
  3. apply the gameplay_enhance.EDITS regex pass to the target files
     (Shift-JIS comment bytes are preserved: edits are ASCII-byte regexes);
  4. rebuild: unchanged entries keep their ORIGINAL stored blob verbatim
     (compression + size fields + CRCs identical), changed entries are stored
     raw (FileSize == ExtractSize, matching the CPK's own convention);
  5. CpkHeader mirrors the original (offsets/sizes recomputed), TOC is rebuilt
     with UTFBuilder keeping the original row order, GTOC/ETOC packets are
     copied verbatim.

Packet layout (verified against the original file):
  magic(4: "CPK "/"TOC "/"GTOC"/"ETOC") + u32le(0xFF) + u32le(8+tsize) +
  u32le(0) + "@UTF" + u32be(tsize) + table
  Header fields TocSize/GtocSize/EtocSize = full packet length = 24 + tsize.

Usage:  python3 cpk_pack.py "Realistic Gameplay Update.cpk" -o "Realistic Gameplay Update ENHANCED.cpk"
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utf_table import UTFTable
from cpk_dump import crilayla_decompress
from gameplay_enhance import EDITS

ALIGN = 1024


def align_up(v, a=ALIGN):
    return (v + a - 1) & ~(a - 1)


def utf_packet(magic, table_bytes):
    tsize = len(table_bytes)
    return (magic + b"\xff\x00\x00\x00" + struct.pack("<II", 8 + tsize, 0)
            + b"@UTF" + struct.pack(">I", tsize) + table_bytes)


class UTFBuilder:
    """Serialize a @UTF table body (without packet frame).
    Storage hi nibble: 0x5=row, 0x3=const, 0x1=none. Type lo nibble:
    0=u8 2=u16 4=u32 6=u64 0xA=str.  add_column(name, type_lo, storage_hi,
    const): const is used for 0x3 columns; pass None for '<NULL>' (offset 0)."""

    def __init__(self, table_name):
        self.table_name = table_name
        self.cols = []          # (flags, const, name)
        self.rows = []

    def add_column(self, name, type_lo, storage_hi, const=None):
        self.cols.append((storage_hi | type_lo, const, name))

    def add_row(self, values):
        self.rows.append(list(values))

    def build(self):
        ncols = len(self.cols)
        if ncols == 0:
            raise ValueError("no columns")
        rowlen = 0
        for flags, _, _ in self.cols:
            if flags >> 4 == 0x5:
                rowlen += {0: 1, 2: 2, 4: 4, 6: 8, 0xA: 4}[flags & 0x0F]

        strs = bytearray(b"<NULL>\x00")
        str_off = {}

        def sofs(s):
            if s is None:
                return 0
            if s not in str_off:
                str_off[s] = len(strs)
                strs.extend(s.encode("utf-8") + b"\x00")
            return str_off[s]

        dats = bytearray()
        dat_off = {}

        def dofs(b):
            key = bytes(b)
            if key not in dat_off:
                dat_off[key] = len(dats)
                dats.extend(key)
            return dat_off[key]

        # 1) column descriptors
        cols_meta = []
        for flags, const, name in self.cols:
            noff = sofs(name)
            cval = 0
            if flags >> 4 == 0x3:
                if isinstance(const, str):
                    cval = sofs(const)
                else:
                    cval = int(const or 0)   # None -> 0 -> "<NULL>"
            cols_meta.append((flags, noff, cval))

        # 2) rows (may append to the pools)
        rows_b = bytearray()
        for row in self.rows:
            if len(row) != ncols:
                raise ValueError("row width mismatch")
            for (flags, const, name), val in zip(self.cols, row):
                if flags >> 4 != 0x5:
                    continue
                t = flags & 0x0F
                if t == 0:
                    rows_b += struct.pack(">B", int(val))
                elif t == 2:
                    rows_b += struct.pack(">H", int(val))
                elif t == 4:
                    rows_b += struct.pack(">I", int(val))
                elif t == 6:
                    rows_b += struct.pack(">Q", int(val))
                elif t == 0xA:
                    rows_b += struct.pack(">I", sofs(val if val != "" else ""))
                else:
                    raise ValueError(f"bad type {t:#x}")

        # 3) table name, then final layout.  Table body layout (offsets
        # relative to body start, i.e. right after the 8-byte @UTF header):
        #   +0  u16 version | +2 u16 rows_off | +4 u32 strs_off | +8 u32 dats_off
        #   +12 u32 name_off | +16 u16 ncols | +18 u16 rowlen | +20 u32 nrows
        #   +24 column descriptors, then rows, then string pool, then data pool.
        tname_off = sofs(self.table_name)
        rows_len = len(rows_b)
        desc_len = sum(9 if (f >> 4) == 0x3 else 5 for f, _, _ in self.cols)
        rows_off = 24 + desc_len
        strs_off = rows_off + rows_len
        dats_off = strs_off + len(strs)
        size = dats_off + len(dats)

        table = bytearray(size)
        struct.pack_into(">H", table, 2, rows_off)
        struct.pack_into(">I", table, 4, strs_off)
        struct.pack_into(">I", table, 8, dats_off)
        struct.pack_into(">I", table, 12, tname_off)
        struct.pack_into(">H", table, 16, ncols)
        struct.pack_into(">H", table, 18, rowlen)
        struct.pack_into(">I", table, 20, len(self.rows))
        p = 24
        for flags, noff, cval in cols_meta:
            table[p] = flags
            p += 1
            struct.pack_into(">I", table, p, noff)
            p += 4
            if flags >> 4 == 0x3:
                struct.pack_into(">I", table, p, cval)
                p += 4
        assert p == rows_off
        table[rows_off:rows_off + rows_len] = rows_b
        table[strs_off:strs_off + len(strs)] = strs
        if dats:
            table[dats_off:dats_off + len(dats)] = dats
        return bytes(table)


# exact CpkHeader columns (name, type_lo, storage_hi) in original order
CPK_HDR_COLS = [
    ("UpdateDateTime", 6, 0x50), ("FileSize", 6, 0x10),
    ("ContentOffset", 6, 0x50), ("ContentSize", 6, 0x50),
    ("TocOffset", 6, 0x50), ("TocSize", 6, 0x50), ("TocCrc", 4, 0x50),
    ("EtocOffset", 6, 0x50), ("EtocSize", 6, 0x50),
    ("ItocOffset", 6, 0x10), ("ItocSize", 6, 0x10), ("ItocCrc", 4, 0x10),
    ("GtocOffset", 6, 0x50), ("GtocSize", 6, 0x50), ("GtocCrc", 4, 0x50),
    ("EnabledPackedSize", 6, 0x50), ("EnabledDataSize", 6, 0x50),
    ("TotalDataSize", 6, 0x10), ("Tocs", 4, 0x10),
    ("Files", 4, 0x50), ("Groups", 4, 0x50), ("Attrs", 4, 0x50),
    ("TotalFiles", 4, 0x10), ("Directories", 4, 0x10), ("Updates", 4, 0x10),
    ("Version", 2, 0x50), ("Revision", 2, 0x50), ("Align", 2, 0x50),
    ("Sorted", 2, 0x50), ("EID", 2, 0x10), ("CpkMode", 4, 0x50),
    ("Tvers", 0xA, 0x50), ("Comment", 0xA, 0x10),
    ("Codec", 4, 0x50), ("DpkItoc", 4, 0x50),
]

TOC_COLS = [
    ("DirName", 0xA, 0x50), ("FileName", 0xA, 0x50), ("FileSize", 4, 0x50),
    ("ExtractSize", 4, 0x50), ("FileOffset", 6, 0x50), ("ID", 4, 0x50),
    ("UserString", 0xA, 0x30), ("CRC", 4, 0x50),
]


def build_cpk(orig, out_path):
    hdr = UTFTable.parse(orig, 0)
    h = hdr.rows[0]
    content_off0 = h["ContentOffset"]
    toc = UTFTable.parse(orig, h["TocOffset"])
    gtoc_raw = orig[h["GtocOffset"]:h["GtocOffset"] + h["GtocSize"]]
    etoc_raw = orig[h["EtocOffset"]:h["EtocOffset"] + h["EtocSize"]]

    by_path = {}
    for path, pat, rep, note in EDITS:
        by_path.setdefault(path, []).append((pat, rep, note))
    from gameplay_enhance import BIN_EDITS
    from qwesys import patch as qwesys_patch
    bin_by_path = {p: (ps, n) for p, ps, n in BIN_EDITS}
    from gameplay_enhance import RAW_EDITS
    raw_by_path = {p: (ps, n) for p, ps, n in RAW_EDITS}
    from gameplay_enhance import QRAW_EDITS
    import qwesys as _qw, zlib as _zlib
    qraw_by_path = {}
    for p, fb, nb, cnt, n in QRAW_EDITS:
        qraw_by_path.setdefault(p, []).append((fb, nb, cnt, n))

    entries = []   # per original TOC row order: (id, dir, name, user, crc,
                   # stored, content, changed)
    for e in toc.rows:
        d = e["DirName"] or ""
        rel = f"{d}/{e['FileName']}" if d else e["FileName"]
        s = content_off0 + e["FileOffset"]
        stored = orig[s:s + e["FileSize"]]
        if stored[:8] == b"CRILAYLA":
            content = crilayla_decompress(stored)
            if len(content) != e["ExtractSize"]:
                raise ValueError(f"{rel}: decode {len(content)} != ExtractSize {e['ExtractSize']}")
        else:
            content = stored
        changed = False
        if rel in by_path:
            for pat, rep, note in by_path[rel]:
                n = len(re.findall(pat, content))
                if n != 1:
                    raise ValueError(f"{rel}: pattern matches {n}x: {pat!r} ({note})")
                content = re.sub(pat, rep, content, count=1)
                changed = True
        if rel in bin_by_path:
            patches, note = bin_by_path[rel]
            content = qwesys_patch(content, patches)
            changed = True
        if rel in raw_by_path:
            for off, old, new in raw_by_path[rel][0]:
                if content[off:off + len(old)] != old:
                    raise ValueError(f"{rel}: raw patch @{off} old-bytes mismatch")
                content = content[:off] + new + content[off + len(old):]
                changed = True
        if rel in qraw_by_path:
          for fb, nb, cnt, qnote in qraw_by_path[rel]:
            qcomp_len, qplain_len = struct.unpack_from("<II", content, 8)
            qpay = _zlib.decompress(content[16:16 + qcomp_len])
            assert len(qpay) == qplain_len, rel
            if qpay.count(fb) != cnt:
                raise ValueError(f"{rel}: qraw count {qpay.count(fb)} != {cnt} ({qnote})")
            qpay2 = qpay.replace(fb, nb)
            qcomp = _zlib.compress(qpay2, 9)
            content = content[:8] + struct.pack("<II", len(qcomp), len(qpay2)) + qcomp
            changed = True
        entries.append((e["ID"], d, e["FileName"], e["UserString"], e["CRC"],
                        stored, content, changed))

    ids = [x[0] for x in entries]
    assert len(ids) == len(set(ids)), "duplicate IDs"
    by_id = {x[0]: x for x in entries}

    changed_ids = sorted(x[0] for x in entries if x[7])
    print(f"original: files={len(entries)} toc@{h['TocOffset']:#x} "
          f"gtoc@{h['GtocOffset']:#x} etoc@{h['EtocOffset']:#x}")
    print(f"changed entries (stored raw): {changed_ids}")

    # ---- content section at 0x800, ID order, 1024-aligned -----------------
    out = bytearray()
    out += utf_packet(b"CPK ", b"\x00" * 0)  # placeholder, rebuilt at the end
    del out[:]
    out += b"CPK " + b"\xff\x00\x00\x00" + b"\x00" * 8
    out += b"\x00" * (0x800 - len(out))

    offsets = {}
    for i in sorted(by_id):
        _, _, _, _, _, stored, content, changed = by_id[i]
        offsets[i] = len(out)
        blob = content if changed else stored
        out += blob
        out += b"\x00" * (align_up(len(out)) - len(out))

    toc_off = align_up(len(out))
    out += b"\x00" * (toc_off - len(out))

    def stored_len(i):
        _, _, _, _, _, stored, content, changed = by_id[i]
        return len(content) if changed else len(stored)

    # TOC: original row order preserved verbatim
    tb = UTFBuilder("CpkTocInfoEx")
    for name, t, st in TOC_COLS:
        tb.add_column(name, t, st)
    for ID, d, fn, us, crc, stored, content, changed in entries:
        tb.add_row([d, fn, stored_len(ID), len(content),
                    offsets[ID] - content_off0, ID, us if us is not None else "", crc])
    toc_packet = utf_packet(b"TOC ", tb.build())
    out += toc_packet
    out += b"\x00" * (align_up(len(out)) - len(out))

    gtoc_off = len(out)
    out += gtoc_raw
    out += b"\x00" * (align_up(len(out)) - len(out))
    etoc_off = len(out)
    out += etoc_raw

    hb = UTFBuilder("CpkHeader")
    for name, t, st in CPK_HDR_COLS:
        hb.add_column(name, t, st)
    vals = {
        "UpdateDateTime": h["UpdateDateTime"],
        "ContentOffset": content_off0,
        "ContentSize": toc_off - content_off0,
        "TocOffset": toc_off, "TocSize": len(toc_packet),
        "TocCrc": h["TocCrc"],
        "EtocOffset": etoc_off, "EtocSize": len(etoc_raw),
        "GtocOffset": gtoc_off, "GtocSize": len(gtoc_raw),
        "GtocCrc": h["GtocCrc"],
        "EnabledPackedSize": h["EnabledPackedSize"],
        "EnabledDataSize": h["EnabledDataSize"],
        "Files": len(entries), "Groups": h["Groups"], "Attrs": h["Attrs"],
        "Version": h["Version"], "Revision": h["Revision"],
        "Align": h["Align"], "Sorted": h["Sorted"], "CpkMode": h["CpkMode"],
        "Tvers": h["Tvers"], "Codec": h["Codec"], "DpkItoc": h["DpkItoc"],
    }
    row = [vals.get(name) for name, _, _ in CPK_HDR_COLS]
    hb.add_row(row)
    header_packet = utf_packet(b"CPK ", hb.build())
    assert len(header_packet) <= 0x800, "header packet larger than 0x800"
    out[0:len(header_packet)] = header_packet

    with open(out_path, "wb") as f:
        f.write(out)
    print(f"wrote {out_path}: {len(out)} bytes (content 0x800..{toc_off:#x}, "
          f"toc {toc_off:#x} ({len(toc_packet)}B), gtoc {gtoc_off:#x}, "
          f"etoc {etoc_off:#x})")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    orig_path = sys.argv[1]
    out_path = None
    args = sys.argv[2:]
    if "-o" in args:
        out_path = args[args.index("-o") + 1]
    else:
        base, ext = os.path.splitext(orig_path)
        out_path = base + " ENHANCED" + ext
    orig = open(orig_path, "rb").read()
    build_cpk(orig, out_path)


if __name__ == "__main__":
    main()
