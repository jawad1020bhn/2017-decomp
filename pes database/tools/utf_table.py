#!/usr/bin/env python3
"""Spec-compliant @UTF reader/writer for CRI CPK tables (big-endian).

Column descriptor (per CRI spec, confirmed against kamikat/cpktools
STRUCT_COLUMN_SCHEMA='>BL' and BogdanLask/cpk-runtime docs):
    u8 flags   (high nibble: 0x10 name-only/NULL, 0x30 name+constant, 0x50 name+row;
                low nibble: value type 0=u8 1=s8 2=u16 3=s16 4=u32 5=s32 6=u64 7=s64
                8=f32 A=string(4) B=blob(8) C=guid(16))
    u32 name offset into string pool            (if flags & 0x10)
    constant value of type size                  (if flags & 0x20)

Row values for 0x50 columns are laid out sequentially in column order.
Offsets in the table header are relative to byte 8 (after magic+table_size).
"""
import struct

TYPE_SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 0xA: 4, 0xB: 8, 0xC: 16}

COL_NAME = 0x10
COL_CONST = 0x20
COL_ROW = 0x40


def _read_val(data, p, t, str_base):
    if t == 0:
        return data[p], 1
    if t == 1:
        return struct.unpack_from(">b", data, p)[0], 1
    if t == 2:
        return struct.unpack_from(">H", data, p)[0], 2
    if t == 3:
        return struct.unpack_from(">h", data, p)[0], 2
    if t == 4:
        return struct.unpack_from(">I", data, p)[0], 4
    if t == 5:
        return struct.unpack_from(">i", data, p)[0], 4
    if t == 6:
        return struct.unpack_from(">Q", data, p)[0], 8
    if t == 7:
        return struct.unpack_from(">q", data, p)[0], 8
    if t == 8:
        return struct.unpack_from(">f", data, p)[0], 4
    if t == 0xA:
        (so,) = struct.unpack_from(">I", data, p)
        end = data.find(b"\0", str_base + so)
        return data[str_base + so:end].decode("utf-8", "replace"), 4
    if t == 0xB:
        return struct.unpack_from(">II", data, p), 8
    if t == 0xC:
        return data[p:p + 16].hex(), 16
    raise ValueError("bad type %x" % t)


def _write_val(buf, v, t):
    if t == 0:
        buf.append(v & 0xFF)
    elif t == 1:
        buf += struct.pack(">b", v)
    elif t == 2:
        buf += struct.pack(">H", v)
    elif t == 3:
        buf += struct.pack(">h", v)
    elif t == 4:
        buf += struct.pack(">I", v)
    elif t == 5:
        buf += struct.pack(">i", v)
    elif t == 6:
        buf += struct.pack(">Q", v)
    elif t == 7:
        buf += struct.pack(">q", v)
    elif t == 8:
        buf += struct.pack(">f", v)
    elif t == 0xA:
        buf += struct.pack(">I", v)  # v = string offset
    elif t == 0xB:
        buf += struct.pack(">II", *v)
    elif t == 0xC:
        buf += bytes.fromhex(v)
    else:
        raise ValueError("bad type %x" % t)


class UTFTable:
    def __init__(self, name, cols, rows):
        self.name = name          # table name string
        self.cols = cols          # list of (name, flags, const_or_None)
        self.rows = rows          # list of dict name->value (row columns only)

    @classmethod
    def parse(cls, data, tbl_off):
        """tbl_off = offset of the 16-byte packet frame; @UTF at tbl_off+0x10."""
        base = tbl_off + 0x10
        assert data[base:base + 4] == b"@UTF", "no @UTF at %#x" % tbl_off
        tsize, version_rows, strs_off, dats_off, name_off, ncols, rlen, nrows = \
            struct.unpack_from(">IIIIIHHI", data, base + 4)
        version = version_rows >> 16
        rows_off = version_rows & 0xFFFF
        assert version == 0, "unsupported @UTF version %d" % version
        str_base = base + 8 + strs_off
        rows_base = base + 8 + rows_off

        def cstr(s_off):
            end = data.find(b"\0", str_base + s_off)
            return data[str_base + s_off:end].decode("utf-8", "replace")

        cols = []
        p = base + 0x20
        for _ in range(ncols):
            flags = data[p]
            p += 1
            cname = None
            if flags & COL_NAME:
                (noff,) = struct.unpack_from(">I", data, p)
                p += 4
                cname = cstr(noff)
            const = None
            if flags & COL_CONST:
                const, sz = _read_val(data, p, flags & 0x0F, str_base)
                p += sz
            cols.append((cname, flags, const))

        rows = []
        for r in range(nrows):
            rp = rows_base + r * rlen
            row = {}
            for cname, flags, const in cols:
                if flags & COL_ROW:
                    v, sz = _read_val(data, rp, flags & 0x0F, str_base)
                    rp += sz
                    row[cname] = v
                elif flags & COL_CONST:
                    row[cname] = const
                else:
                    row[cname] = None
            rows.append(row)
        return cls(cstr(name_off), cols, rows)

    def dump(self):
        """Serialize to bytes. Returns the @UTF table (without packet frame).

        Strings referenced by row string columns are taken from the row values
        (str): they are interned into the string pool. Constant strings are
        interned likewise.
        """
        # build string pool: index strings, assign offsets
        strings = []

        def intern(s):
            for i, (txt, _) in enumerate(strings):
                if txt == s:
                    return i
            strings.append([s, None])
            return len(strings) - 1

        intern("")  # offset 0 = empty string, convenient
        name_idx = intern(self.name)
        col_name_idx = []
        for cname, flags, const in self.cols:
            if flags & COL_NAME:
                col_name_idx.append(intern(cname))
            else:
                col_name_idx.append(None)

        # first pass: compute pool layout (need offsets before writing rows)
        def pool_offsets():
            offs = []
            p = 0
            for txt, _ in strings:
                offs.append(p)
                p += len(txt.encode("utf-8")) + 1
            return offs

        # constant string values need intern too
        for cname, flags, const in self.cols:
            if (flags & (COL_CONST | 0x0F)) == (COL_CONST | 0xA):
                intern(const if isinstance(const, str) else "")

        # row string columns: intern values (they are raw offsets in parse output,
        # so here we expect actual strings in rows for convenience)
        str_cols = [c for c in self.cols if (c[1] & COL_ROW) and (c[1] & 0x0F) == 0xA]
        for row in self.rows:
            for cname, flags, const in str_cols:
                intern(row.get(cname) or "")

        offs = pool_offsets()
        str_base_rel = None  # computed later

        # compute row length and serialize row values as byte blocks
        def row_block(row):
            buf = bytearray()
            for cname, flags, const in self.cols:
                if flags & COL_ROW:
                    t = flags & 0x0F
                    v = row.get(cname)
                    if t == 0xA:
                        v = offs[strings.index([v or "", None])] if False else None
                    buf_v = bytearray()
                    if t == 0xA:
                        # string: offset into pool
                        txt = row.get(cname) or ""
                        idx = next(i for i, (s, _) in enumerate(strings) if s == txt)
                        _write_val(buf_v, offs[idx], t)
                    else:
                        _write_val(buf_v, v, t)
                    buf += buf_v
            return bytes(buf)

        blocks = [row_block(r) for r in self.rows]
        rlen = len(blocks[0]) if blocks else 0
        for b in blocks:
            assert len(b) == rlen, "ragged rows"

        # column descriptors size
        desc = bytearray()
        for (cname, flags, const), nidx in zip(self.cols, col_name_idx):
            desc.append(flags)
            if flags & COL_NAME:
                desc += struct.pack(">I", offs[nidx])
            if flags & COL_CONST:
                t = flags & 0x0F
                if t == 0xA:
                    txt = const or ""
                    idx = next(i for i, (s, _) in enumerate(strings) if s == txt)
                    _write_val(desc, offs[idx], t)
                else:
                    _write_val(desc, const, t)

        header_len = 0x20  # fixed header (magic..nrows) == 32 bytes
        rows_rel = header_len - 8 + len(desc)     # relative to base+8
        rows_size = rlen * len(blocks)
        strs_rel = rows_rel + rows_size
        pool = bytearray()
        for txt, _ in strings:
            pool += txt.encode("utf-8") + b"\0"
        dats_rel = strs_rel + len(pool)

        total = 8 + dats_rel  # table_size excludes the 4-byte magic? see below
        # Per spec: "Table size in bytes, excluding the magic" and
        # "total table size is table_size + 8". So table_size = total - 8.
        table_size = total - 8

        out = bytearray()
        out += b"@UTF"
        out += struct.pack(">I", table_size)
        out += struct.pack(">H", 0)            # version
        out += struct.pack(">H", rows_rel & 0xFFFF) if rows_rel < 0x10000 else None
        if out[-2:] == b"" or rows_rel >= 0x10000:
            raise ValueError("rows offset too large for u16: %#x" % rows_rel)
        out += struct.pack(">I", strs_rel)
        out += struct.pack(">I", dats_rel)
        out += struct.pack(">I", offs[name_idx])
        out += struct.pack(">H", len(self.cols))
        out += struct.pack(">H", rlen)
        out += struct.pack(">I", len(blocks))
        out += desc
        for b in blocks:
            out += b
        out += pool
        assert len(out) == total
        return bytes(out)
