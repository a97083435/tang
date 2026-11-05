import math

TIMESTAMP_WRAP = 1 << 32
AUDIO_WAIT_MS = 400
SAMPLE_RATES = (96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350)
SILENT_FRAMES = {
    1: bytes((0, 200, 0, 128, 35, 128)),
    2: bytes((33, 0, 73, 144, 2, 25, 0, 35, 128)),
}


class Normalizer:
    def __init__(self):
        self.last = {}
        self.base = None
        self.restart = False
        self.config = None
        self.silence = None
        self.duration = 0
        self.next_audio = None
        self.reference = None

    def __call__(self, tag, data):
        kind = tag[0]
        stamp = int.from_bytes(tag[4:7], "big") + tag[7] * 16777216
        body = data[:-4]
        if kind == 18 and self.last:
            self.restart = True
            self.next_audio = None
            self.reference = None
        if kind == 8 and len(body) >= 4 and body[0] >> 4 == 10 and body[1] == 0 and body != self.config:
            self.config = bytes(body)
            self.silence, self.duration = _audio_config(body)
            self.next_audio = None
        if kind in (8, 9) and len(body) >= 2 and body[1] == 1:
            stamp = self._timestamp(stamp)
            if kind in self.last and stamp <= self.last[kind]:
                return
            if self.next_audio is None:
                self.next_audio = stamp
            if kind == 9:
                yield from self._fill_audio(stamp)
            else:
                self.next_audio = stamp + self.duration
            self.last[kind] = stamp
        else:
            stamp -= self.base or 0
        tag = bytearray(tag)
        _write_timestamp(tag, max(0, stamp))
        yield tag, data

    def _timestamp(self, value):
        if self.reference is not None:
            value -= (value - self.reference + TIMESTAMP_WRAP // 2) // TIMESTAMP_WRAP * TIMESTAMP_WRAP
        self.reference = max(self.reference if self.reference is not None else value, value)
        if self.base is None:
            self.base = value
        if self.restart:
            self.base = min(self.base, value - max(self.last.values()) - 1)
            self.restart = False
        return value - self.base

    def _fill_audio(self, stamp):
        while self.silence and self.next_audio + AUDIO_WAIT_MS < stamp:
            value = math.floor(self.next_audio + 0.5)
            yield _audio_tag(max(0, value), self.silence)
            self.last[8] = value
            self.next_audio += self.duration


def _audio_config(data):
    profile = data[2] >> 3
    index = (data[2] & 7) * 2 + (data[3] >> 7)
    channels = (data[3] >> 3) & 15
    if profile != 2 or index >= len(SAMPLE_RATES) or channels not in SILENT_FRAMES or data[3] & 7:
        return None, 0
    return bytes((data[0], 1)) + SILENT_FRAMES[channels], 1024000 / SAMPLE_RATES[index]


def _audio_tag(stamp, data):
    tag = bytearray(11)
    tag[0] = 8
    tag[1:4] = len(data).to_bytes(3, "big")
    _write_timestamp(tag, stamp)
    return tag, data + (len(data) + 11).to_bytes(4, "big")


def _write_timestamp(tag, stamp):
    value = stamp & 0xffffffff
    tag[4:8] = bytes((value >> 16 & 255, value >> 8 & 255, value & 255, value >> 24))
