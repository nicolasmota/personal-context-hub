from __future__ import annotations

import secrets
from pathlib import Path

from pch_core.audit.ledger import Ledger
from pch_core.hub.actions import ActionsMixin
from pch_core.hub.capture import CaptureMixin
from pch_core.hub.const import OWNER
from pch_core.hub.context import ContextMixin
from pch_core.hub.evolution import EvolutionMixin
from pch_core.hub.explain import ExplainMixin
from pch_core.hub.objects import ObjectsMixin
from pch_core.hub.pairing import PairingMixin
from pch_core.hub.proposals import ProposalsMixin
from pch_core.hub.relations import RelationsMixin
from pch_core.hub.setup import SetupMixin
from pch_core.hub.state import StateMixin
from pch_core.retrieval.retriever import TokenOverlapRetriever
from pch_core.vault.blobs import BlobStore
from pch_core.vault.engine import Engine
from pch_core.vault.keys import load_or_create_key
from pch_core.vault.objects import ObjectStore
from pch_core.vault.owner_file import write_owner_token

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
