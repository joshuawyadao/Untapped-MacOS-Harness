"""Read and rewrite packed ASAR entries without executing or extracting them."""
import copy
import hashlib
import json
import struct


class HarnessError(ValueError):
    """An input failed a safety or compatibility guard."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def entries(node, prefix=""):
    for name, entry in node.get("files", {}).items():
        if name in ("", ".", "..") or "/" in name or "\\" in name:
            raise HarnessError("Unsafe ASAR entry name")
        path = prefix + name
        if "files" in entry:
            yield from entries(entry, path + "/")
        else:
            yield path, entry


class Archive:
    def __init__(self, data):
        try:
            a, header_size, payload_size, length = struct.unpack("<4I", data[:16])
            if (a != 4 or header_size != payload_size + 4 or header_size % 4
                    or not 0 < length <= 32 * 1024 * 1024
                    or not 0 <= payload_size - 4 - length <= 3
                    or 8 + header_size > len(data)):
                raise HarnessError("Invalid ASAR header lengths")
            self.raw_header = data[16:16 + length]
            self.header = json.loads(self.raw_header)
            self.start = 8 + header_size
            self.data = data
            self.files = dict(entries(self.header))
            for entry in self.files.values():
                if "offset" in entry:
                    offset, size = int(entry["offset"]), entry["size"]
                    if (not isinstance(size, int) or size < 0 or offset < 0
                            or self.start + offset + size > len(data)):
                        raise HarnessError("ASAR entry outside payload")
        except (ValueError, TypeError, KeyError, AttributeError, struct.error) as exc:
            raise HarnessError("Malformed ASAR archive") from exc

    def read(self, path):
        entry = self.files.get(path, {})
        if "offset" not in entry or entry.get("unpacked") or "link" in entry:
            raise HarnessError("Required packed entry missing: " + path)
        start = self.start + int(entry["offset"])
        return self.data[start:start + entry["size"]]

    def rewrite(self, replacements):
        if not replacements.keys() <= self.files.keys():
            raise HarnessError("Cannot add unknown ASAR entries")
        header = copy.deepcopy(self.header)
        payload = bytearray()
        for path, entry in entries(header):
            if entry.get("unpacked") or "link" in entry:
                if path in replacements:
                    raise HarnessError("Cannot patch unpacked entries or links")
                continue
            content = replacements.get(path)
            if content is None:
                content = self.read(path)
            entry.update(offset=str(len(payload)), size=len(content))
            if path in replacements and "integrity" in entry:
                block_size = entry["integrity"]["blockSize"]
                if not isinstance(block_size, int) or block_size <= 0:
                    raise HarnessError("Invalid ASAR integrity block size")
                entry["integrity"] = {
                    "algorithm": "SHA256", "hash": sha256(content), "blockSize": block_size,
                    "blocks": [sha256(content[i:i + block_size])
                               for i in range(0, len(content), block_size)],
                }
            payload.extend(content)
        raw = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode()
        padding = bytes(-(4 + len(raw)) % 4)
        pickle = struct.pack("<II", 4 + len(raw) + len(padding), len(raw)) + raw + padding
        return struct.pack("<II", 4, len(pickle)) + pickle + payload
