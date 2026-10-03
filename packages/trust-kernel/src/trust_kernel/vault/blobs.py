from __future__ import annotations

import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


class BlobStore:
    def __init__(self, root: Path, key: bytes) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._aead = ChaCha20Poly1305(key[:32].ljust(32, b"\0")[:32])

    def put(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        nonce = bytes.fromhex(digest[:24].ljust(24, "0"))[:12]
        path = self.root / digest
        if not path.exists():
            path.write_bytes(nonce + self._aead.encrypt(nonce, data, None))
        return digest

    def get(self, digest: str) -> bytes:
        raw = (self.root / digest).read_bytes()
        nonce, ct = raw[:12], raw[12:]
        return self._aead.decrypt(nonce, ct, None)
