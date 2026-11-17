"""QWESYS zlib container toolkit — PES 2017 dt18 constant bins.

constant_team.bin (and friends) are 16-byte QWESYS headers wrapping a zlib
payload that holds a named-entry table. Layout (verified on our
constant_team.bin, 1382 B -> 3760 B payload):

  0x00  u8[2] 00 10            (tag, kept verbatim)
  0x02  char[6] 'QWESYS'
  0x08  u32le  compressed payload size (zlib stream length)
  0x0C  u32le  uncompressed payload size
  0x10  zlib stream

Payload layout (constant_team.bin):

  0x00  u32le  count (16)
  0x04  u32le  index_off   (8)
  0x08  u32le  name_table  (416)
  0x0C  u32le  aux_names   (864)
  0x10  count * (u32le name_off, u32le data_off, u32le size)
        -- teamId.o is a 2-field external-ref entry: name_off then an inline
           CPK path string; its data/size fields are string bytes, not offsets.

Entry data regions are contiguous 0x500..0xeb0, all sizes multiples of 16.
Field semantics come from the community mappings vendored in tools/mappings/
(the4chancup/pes-gameplay-editor + implyingrigged wiki); PES 2017 offsets were
re-validated against our payload (see changelog Pass 8).
"""
import struct
import zlib

HDR_LEN = 16


def parse(raw: bytes) -> bytes:
    """Return the uncompressed payload of a QWESYS container."""
    assert raw[2:8] == b"QWESYS", "not a QWESYS container"
    comp_size, raw_size = struct.unpack_from("<II", raw, 8)
    payload = zlib.decompress(raw[HDR_LEN:HDR_LEN + comp_size])
    assert len(payload) == raw_size, (len(payload), raw_size)
    return payload


def rebuild(payload: bytes, orig_hdr: bytes) -> bytes:
    """Wrap payload back into the QWESYS container, preserving the 8-byte tag."""
    comp = zlib.compress(payload)
    return orig_hdr[:8] + struct.pack("<II", len(comp), len(payload)) + comp


def parse_index(payload: bytes):
    """-> (entries: name -> (data_off, size), order: [name])."""
    count = struct.unpack_from("<I", payload, 0)[0]
    entries, order = {}, []
    for i in range(count):
        name_off, data_off, size = struct.unpack_from("<III", payload, 16 + i * 12)
        name = payload[name_off:payload.index(b"\0", name_off)].decode("ascii")
        entries[name] = (data_off, size)
        order.append(name)
    return entries, order


def patch(raw: bytes, patches) -> bytes:
    """Apply (entry, byte_off, 'u32'|'f32', old, new) patches with old-value
    assertions; returns the rebuilt container bytes."""
    hdr = raw[:HDR_LEN]
    payload = bytearray(parse(raw))
    entries, _ = parse_index(bytes(payload))
    for entry, off, kind, old, new in patches:
        base, size = entries[entry]
        assert 0 <= off and off + 4 <= size, (entry, off, size)
        pos = base + off
        if kind == "u32":
            cur = struct.unpack_from("<I", payload, pos)[0]
            assert cur == old, f"{entry}+{off}: expected {old} got {cur}"
            struct.pack_into("<I", payload, pos, new)
        elif kind == "f32":
            cur = struct.unpack_from("<f", payload, pos)[0]
            assert abs(cur - old) < 1e-6, f"{entry}+{off}: expected {old} got {cur}"
            struct.pack_into("<f", payload, pos, new)
        else:
            raise ValueError(kind)
    return rebuild(bytes(payload), hdr)
