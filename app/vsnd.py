"""Assemble a Source 2 .vsnd_c without Valve tools.

A compiled Sound resource is: fixed-size header (Source 2 resource blocks
RED2/CTRL/DATA) + raw PCM16 payload appended. For a FIXED frame count
(our canonical 76.000000 s loop) the header is constant, so we ship only the
reference header (1268 bytes, compiled once by resourcecompiler) and build:

    vsnd_c = reference_header + user PCM16

The only content-dependent header field is m_nFileCRC of the source .wav in
the RED2 dependency block (compiler metadata the game never reads); we patch
it so the file stays internally consistent.
"""
import struct
import zlib


def build_vsnd_c(header_bytes, pcm_bytes, wav_bytes):
    """Return full vsnd_c bytes for user audio.

    header_bytes: the reference header (ends where the DATA payload starts)
    pcm_bytes:    raw PCM16 payload, stereo 44.1 kHz, canonical frame count
    wav_bytes:    the source .wav bytes (its crc32 is recorded in RED2)
    """
    data_off = struct.unpack_from("<I", header_bytes, 0)[0]
    if data_off != len(header_bytes):
        raise ValueError("reference header size mismatch: %d vs %d"
                         % (data_off, len(header_bytes)))
    old_crc = struct.unpack_from("<I", header_bytes, 690)[0]
    new_crc = zlib.crc32(wav_bytes) & 0xFFFFFFFF
    header = bytearray(header_bytes)
    pos = header_bytes.find(struct.pack("<I", old_crc))
    if pos != -1:
        struct.pack_into("<I", header, pos, new_crc)
    return bytes(header) + pcm_bytes
