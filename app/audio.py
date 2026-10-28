"""Shared audio pipeline for Slide Mod Maker.

Takes any mp3/wav + loop start time, produces the canonical loop:
  stereo 44.1 kHz PCM16, FIXED length LOOP_SECONDS (76.000000 s exactly),
  tail->head crossfade, loudness normalized to the requested LUFS,
  wrapped in a WAV with a smpl loop chunk.

Everything downstream (vsnd_c patching, vsndevts) depends on the loop being
exactly LOOP_SECONDS, so pad/trim to the frame here.
"""
import math
import struct

SR = 44100
CH = 2
LOOP_SECONDS = 76.000000
LOOP_FRAMES = int(round(LOOP_SECONDS * SR))      # 3 351 600
DEFAULT_LUFS = -10.0


def decode(path):
    """Decode mp3/wav -> float32 ndarray (n, 2) at SR."""
    import numpy as np
    if path.lower().endswith(".wav"):
        return _decode_wav(path)
    import miniaudio
    buf = miniaudio.decode_file(path, nchannels=CH, sample_rate=SR,
                                dither=miniaudio.DitherMode.TRIANGLE)
    samples = np.frombuffer(buf.samples, dtype=np.int16).astype(np.float32) / 32768.0
    return samples.reshape(-1, CH)


def _decode_wav(path):
    import numpy as np
    import wave
    w = wave.open(path, "rb")
    ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    raw = w.readframes(n)
    w.close()
    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sw == 4:
        x = np.frombuffer(raw, dtype="<f4").astype(np.float32)
    else:
        raise ValueError("unsupported wav bit depth: %d" % (sw * 8))
    x = x.reshape(-1, ch)
    if sr != SR:
        x = _resample(x, sr, SR)
    if ch == 1:
        x = np.repeat(x, 2, axis=1)
    elif ch > 2:
        x = x[:, :2]
    return x


def _resample(x, sr_in, sr_out):
    import numpy as np
    n_out = int(round(len(x) * sr_out / sr_in))
    t = np.linspace(0.0, len(x) / sr_in, n_out, endpoint=False, dtype=np.float64)
    idx = t * sr_in
    i0 = np.clip(idx.astype(np.int64), 0, len(x) - 1)
    i1 = np.clip(i0 + 1, 0, len(x) - 1)
    frac = (idx - i0).astype(np.float32)[:, None]
    return x[i0] * (1 - frac) + x[i1] * frac


def build_loop(x, start_seconds, target_lufs=DEFAULT_LUFS):
    """Cut from start_seconds, fit to LOOP_FRAMES, crossfade seam, normalize."""
    import numpy as np
    a = int(round(start_seconds * SR))
    seg = x[a:].copy()
    if len(seg) < LOOP_FRAMES // 2:
        raise ValueError("starting point is too close to the end of the track")
    if len(seg) < LOOP_FRAMES:
        # not enough tail: wrap around the track end to fill (still seamless
        # because the seam crossfade runs after padding)
        reps = LOOP_FRAMES // len(seg) + 1
        seg = np.tile(seg, (reps, 1))[:LOOP_FRAMES]
    else:
        seg = seg[:LOOP_FRAMES]

    # close the loop: crossfade the tail into the head, XF snapped to the
    # quietest head step so the wrap discontinuity is minimal
    XF_LO, XF_HI = int(0.120 * SR), int(0.180 * SR)
    best = None
    for xf in range(XF_LO, XF_HI):
        step = float(np.max(np.abs(seg[xf] - seg[0])))
        if best is None or step < best[0]:
            best = (step, xf)
    xf = best[1]
    tail = seg[LOOP_FRAMES - xf:].copy()
    head = seg[:xf].copy()
    t = np.linspace(0.0, 1.0, xf, dtype=np.float32)[:, None]
    fo = np.cos(t * math.pi / 2) ** 2
    fi = np.sin(t * math.pi / 2) ** 2
    seg[LOOP_FRAMES - xf:] = tail * fo + head * fi

    seg = _normalize(seg, target_lufs)
    return seg


def _normalize(seg, target_lufs):
    import numpy as np
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(SR)
        data = np.ascontiguousarray(seg, dtype=np.float64)
        loud = meter.integrated_loudness(data)
        if loud > -70 and math.isfinite(loud):
            gain = 10 ** ((target_lufs - loud) / 20.0)
            seg = seg * np.float32(gain)
    except Exception:
        # fallback: RMS normalization to roughly -10 LUFS
        rms = math.sqrt(float(np.mean(seg ** 2)))
        if rms > 1e-9:
            seg = seg * np.float32(0.112 / rms)
    peak = float(np.max(np.abs(seg)))
    if peak > 0.985:
        seg = seg * np.float32(0.985 / peak)
    return np.clip(seg, -1.0, 1.0)


def loop_to_wav_bytes(seg):
    """float32 (n,2) in [-1,1] -> WAV bytes (PCM16 44.1k stereo + smpl chunk)."""
    import numpy as np
    pcm = (np.clip(seg, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    assert len(pcm) == LOOP_FRAMES * CH * 2
    fmt = struct.pack("<HHIIHH", 1, CH, SR, SR * CH * 2, CH * 2, 16)
    smpl = struct.pack("<9I", 0, 0, int(round(1e9 / SR)), 60, 0, 0, 0, 1, 0)
    smpl += struct.pack("<6I", 0, 0, 0, LOOP_FRAMES - 1, 0, 0)  # forward loop 0..N-1
    body = (b"fmt " + struct.pack("<I", len(fmt)) + fmt +
            b"smpl" + struct.pack("<I", len(smpl)) + smpl +
            b"data" + struct.pack("<I", len(pcm)) + pcm)
    return b"RIFF" + struct.pack("<I", len(body) + 4) + b"WAVE" + body
