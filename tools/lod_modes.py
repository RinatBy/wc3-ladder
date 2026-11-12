"""Classify LoD lanes from map events in private Warcraft 1.29 replays."""

from datetime import datetime
from pathlib import Path
import re
import struct
import zlib


HISTORICAL_MODES = {
    (11, "2026-11-07 19:40:17"): ("no-mid", "game-log"),
    (12, "2026-11-07 20:35:43"): ("only-mid", "game-log"),
    (18, "2026-11-11 19:59:28"): ("only-mid", "map-event"),
}
MODE_TOKENS = set(
    "ap ar dm sp aa ai as id np sc em du sh om nm nt nb ns nr sd pm oi mi "
    "fr mo ro zm ul ss ab s5 s6 fn d2 d3 d4 d5 os bo md ra 3ls ls ff eb fh ma rc rd ah nn so"
    .split()
)
LANE_TOKENS = {"om": "only-mid", "nm": "no-mid", "nt": "no-top", "nb": "no-bottom"}
REPLAY_NAME = re.compile(r"GHost\+\+ (\d{4}-\d{2}-\d{2} \d{2}-\d{2}) (.+) \((\d+)m(\d{2})s\)\.w3g")
MODE_EVENT = re.compile(rb"\x6bdr\.x\x00Data\x00Mode([a-zA-Z0-9]{2,110})\x00(?=.{4})", re.S)


def lane_mode(code):
    tokens = []
    while code:
        token = "3ls" if code.startswith("3ls") else code[:2]
        if token not in MODE_TOKENS:
            return None
        tokens.append(token)
        code = code[len(token):]
    lanes = {LANE_TOKENS[token] for token in tokens if token in LANE_TOKENS}
    if len(lanes) > 1:
        return None
    return next(iter(lanes), "all-lanes")


def read_replay_mode(path):
    if path.stat().st_size > 16 * 1024 * 1024:
        return None
    raw = path.read_bytes()
    if len(raw) < 68 or raw[:28] != b"Warcraft III recorded game\x1a\x00":
        return None
    offset, compressed, header_version, expanded, count = struct.unpack_from("<5I", raw, 28)
    if (header_version != 1 or offset != 68 or compressed != len(raw)
            or not 0 < count <= 8192 or not 0 < expanded <= 48 * 1024 * 1024):
        return None
    if struct.unpack_from("<I", raw, 52)[0] != 29:
        return None
    data = bytearray()
    for _ in range(count):
        if offset + 8 > len(raw):
            return None
        size, out_size, _ = struct.unpack_from("<HHI", raw, offset)
        offset += 8
        if not size or not 0 < out_size <= 8192 or offset + size > len(raw):
            return None
        block = zlib.decompressobj().decompress(raw[offset:offset + size], out_size + 1)
        if len(block) != out_size or len(data) + out_size > expanded + 8192:
            return None
        data.extend(block)
        offset += size
    if offset != len(raw) or len(data) < expanded:
        return None
    modes = {key.lower().decode("ascii") for key in MODE_EVENT.findall(data[:expanded])}
    if len(modes) != 1:
        return None
    return lane_mode(modes.pop())


def replay_index(directory):
    index = {}
    for path in Path(directory).glob("GHost++ *.w3g"):
        match = REPLAY_NAME.fullmatch(path.name)
        if not match or path.is_symlink() or not path.is_file():
            continue
        stamp, room, minutes, seconds = match.groups()
        try:
            date = datetime.strptime(stamp, "%Y-%m-%d %H-%M")
        except ValueError:
            continue
        index.setdefault(room, []).append((date, int(minutes) * 60 + int(seconds), path))
    return index


def game_mode(game, replays):
    historical = HISTORICAL_MODES.get((game["id"], game["datetime"]))
    if historical:
        return historical
    if not game["datetime"] or not game["gamename"] or game["duration"] is None:
        return None
    try:
        date = datetime.fromisoformat(game["datetime"])
    except ValueError:
        return None
    room = re.sub(r"[\\/:*?<>|]", "_", game["gamename"])
    candidates = [
        path for saved_at, duration, path in replays.get(room, ())
        if abs((saved_at - date).total_seconds()) < 120
        and abs(duration - game["duration"]) <= 30
    ]
    if len(candidates) != 1:
        return None
    try:
        mode = read_replay_mode(candidates[0])
    except (OSError, zlib.error):
        return None
    return (mode, "map-event") if mode else None
