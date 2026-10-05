"""Carga y validación del registro extensible de cadenas."""
from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FIELDS = {
    "id", "name", "geographic_scope", "postal_coverage", "official_url",
    "source_type", "requires_location", "requires_session", "requires_loyalty",
    "adapter_status", "last_validated", "known_restrictions",
}
VALID_STATUSES = {"active", "pending", "blocked", "manual"}


class RegistryError(ValueError):
    pass


class SupermarketRegistry:
    def __init__(self, entries: list[dict]):
        self.entries = entries
        self._by_id = {entry["id"]: entry for entry in entries}
        if len(self._by_id) != len(entries):
            raise RegistryError("El registro contiene identificadores duplicados.")

    @classmethod
    def load(cls, path: Path) -> "SupermarketRegistry":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise RegistryError("El registro debe ser una lista JSON.")
        for index, entry in enumerate(data, start=1):
            missing = REQUIRED_FIELDS - set(entry)
            if missing:
                raise RegistryError(f"Entrada {index}: faltan {', '.join(sorted(missing))}.")
            if entry["adapter_status"] not in VALID_STATUSES:
                raise RegistryError(f"Entrada {index}: estado de adaptador no válido.")
        return cls(data)

    def get(self, store_id: str) -> dict:
        try:
            return self._by_id[store_id]
        except KeyError as error:
            raise RegistryError(f"Cadena desconocida: {store_id}.") from error

    def list(self, status: str | None = None) -> list[dict]:
        return [entry for entry in self.entries if status is None or entry["adapter_status"] == status]
