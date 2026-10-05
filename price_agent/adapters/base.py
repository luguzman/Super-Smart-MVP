"""Contrato común para fuentes de supermercados."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from price_agent.models import AdapterResult, CoverageResult, NormalizedProduct, PriceObservation


class SupermarketAdapter(ABC):
    """Interfaz estable; una implementación no debe enumerar catálogos completos."""

    adapter_id: str

    @abstractmethod
    def discover_coverage(self, postal_code: str) -> CoverageResult:
        raise NotImplementedError

    @abstractmethod
    def search_product(self, query: NormalizedProduct, postal_code: str) -> list[NormalizedProduct]:
        raise NotImplementedError

    @abstractmethod
    def get_product_details(self, product_url: str, postal_code: str) -> NormalizedProduct | None:
        raise NotImplementedError

    @abstractmethod
    def get_price(self, product: NormalizedProduct, postal_code: str) -> PriceObservation | None:
        raise NotImplementedError

    def collect(self, products: Iterable[NormalizedProduct], postal_code: str) -> AdapterResult:
        coverage = self.discover_coverage(postal_code)
        result = AdapterResult(adapter_id=self.adapter_id, coverage=coverage)
        for product in products:
            try:
                observation = self.get_price(product, postal_code)
                if observation is None:
                    result.not_found.append(product.product_id)
                else:
                    result.observations.append(observation)
            except Exception as error:  # Un adaptador no debe abortar toda la ejecución.
                result.errors.append({"product_id": product.product_id, "error": str(error)})
        return result
