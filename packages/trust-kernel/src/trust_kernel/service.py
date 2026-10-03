from __future__ import annotations

import secrets
from pathlib import Path

from trust_kernel.audit.ledger import Ledger
from trust_kernel.hub.actions import ActionsMixin
from trust_kernel.hub.capture import CaptureMixin
from trust_kernel.hub.const import OWNER
from trust_kernel.hub.context import ContextMixin
from trust_kernel.hub.evolution import EvolutionMixin
from trust_kernel.hub.explain import ExplainMixin
from trust_kernel.hub.objects import ObjectsMixin
from trust_kernel.hub.pairing import PairingMixin
from trust_kernel.hub.proposals import ProposalsMixin
from trust_kernel.hub.relations import RelationsMixin
from trust_kernel.hub.setup import SetupMixin
from trust_kernel.hub.state import StateMixin
from trust_kernel.retrieval.retriever import TokenOverlapRetriever
from trust_kernel.vault.blobs import BlobStore
from trust_kernel.vault.engine import Engine
from trust_kernel.vault.keys import load_or_create_key
from trust_kernel.vault.objects import ObjectStore
from trust_kernel.vault.owner_file import write_owner_token

__all__ = ["OWNER", "Hub"]


class Hub(
    SetupMixin,
    ObjectsMixin,
    ContextMixin,
    PairingMixin,
    StateMixin,
    ProposalsMixin,
    RelationsMixin,
    ActionsMixin,
    CaptureMixin,
    EvolutionMixin,
    ExplainMixin,
):
    def __init__(
        self, data_dir: Path, passphrase: str | None = None, *, plain: bool | None = None
    ) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.key = load_or_create_key(data_dir, passphrase)
        self.engine = Engine(data_dir / "vault.db", self.key, plain=plain)
        self.store = ObjectStore(self.engine)
        self.ledger = Ledger(self.engine)
        self.blobs = BlobStore(data_dir / "blobs", self.key)
        self.owner_token = self._kv_get("owner_token") or secrets.token_urlsafe(32)
        self._kv_set("owner_token", self.owner_token)
        self.retriever = TokenOverlapRetriever()
        self.last_compilation_trace = None
        write_owner_token(self.data_dir, self.owner_token)

    def close(self) -> None:
        self.engine.close()
