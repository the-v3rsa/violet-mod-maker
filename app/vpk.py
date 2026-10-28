"""VPK v2 writer (pure Python, mirrors C:\\DeadlockModding\\work\\build_vpk.py).

build(entries, out_path): entries = dict rel_path -> bytes.
"""
import hashlib
import os
import struct
import zlib


def build(entries, out_path):
    # tree: extension -> dir -> list of (name_without_ext, rel_key)
    tree = {}
    for rel in sorted(entries):
        d, name = rel.rsplit("/", 1) if "/" in rel else (" ", rel)
        stem, ext = (name.rsplit(".", 1) if "." in name else (name, " "))
        tree.setdefault(ext, {}).setdefault(d, []).append((stem, rel))

    data = bytearray()
    offsets = {}
    for rel in sorted(entries):
        blob = entries[rel]
        offsets[rel] = (zlib.crc32(blob) & 0xFFFFFFFF, len(data), len(blob))
        data += blob

    body = bytearray()
    for ext in sorted(tree):
        body += ext.encode() + b"\0"
        for path in sorted(tree[ext]):
            body += path.encode() + b"\0"
            for stem, rel in sorted(tree[ext][path]):
                crc, off, ln = offsets[rel]
                body += stem.encode() + b"\0"
                body += struct.pack("<IHHIIH", crc, 0, 0x7FFF, off, ln, 0xFFFF)
            body += b"\0"          # end of this path's file list
        body += b"\0"              # end of this extension's path list
    body += b"\0"                  # end of tree

    hdr = struct.pack("<7I", 0x55AA1234, 2, len(body), len(data), 0, 48, 0)
    tree_md5 = hashlib.md5(bytes(body)).digest()
    arch_md5 = hashlib.md5(b"").digest()
    file_md5 = hashlib.md5(hdr + bytes(body) + bytes(data) + tree_md5 + arch_md5).digest()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "wb").write(hdr + bytes(body) + bytes(data) + tree_md5 + arch_md5 + file_md5)
    return len(hdr) + len(body) + len(data) + 48
