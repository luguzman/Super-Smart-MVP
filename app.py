#!/usr/bin/env python3
"""Servidor local del MVP Super Smart."""
from __future__ import annotations

import json
import math
import re
from datetime import date
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from import_prices import PriceImportError, import_csv_text


ROOT = Path(__file__).parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
CUSTOM_OBSERVATIONS = DATA / "local_price_observations.json"


def load_json(path: Path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def clean_tokens(value: str) -> set[str]:
    words = re.findall(r"[a-záéíóúñü0-9]+", value.lower())
    return {word for word in words if len(word) > 1 and word not in {"de", "del", "la", "el", "con", "sin", "para", "en", "y"}}


def category_root(product):
    return (product.get("category") or "").lower().split("/")[0].strip()


def product_similarity(source, target):
    if source["id"] == target["id"]:
        return 1.0, "idéntico"
    if source.get("ean") and source.get("ean") == target.get("ean"):
        return 1.0, "EAN idéntico"
    source_category, target_category = category_root(source), category_root(target)
    if not source_category or source_category != target_category:
        return 0.0, None
    source_words, target_words = set(source.get("name_tokens") or clean_tokens(source["name"])), set(target.get("name_tokens") or clean_tokens(target["name"]))
    overlap = len(source_words & target_words) / max(1, len(source_words | target_words))
    weight_a, weight_b = source.get("weight_g"), target.get("weight_g")
    weight_score = 0.35
    if weight_a and weight_b:
        weight_score = max(0, 1 - abs(math.log(weight_a / weight_b)))
    brand_bonus = 0.18 if source.get("brand") and source.get("brand") == target.get("brand") else 0
    score = min(0.89, 0.38 + 0.42 * overlap + 0.2 * weight_score + brand_bonus)
    return score, "equivalente por categoría y formato" if score >= 0.58 else None


def effective_price(observation, include_loyalty):
    if observation.get("loyalty_required") and not include_loyalty:
        return observation["price_eur"]
    return max(0, observation["price_eur"] - observation.get("promotion_eur", 0))


def latest_observations(observations):
    """Evita que un precio histórico gane frente a una captura reciente."""
    selected = {}
    for observation in observations:
        key = (observation.get("product_id"), str(observation.get("store", "")).lower())
        rank = (
            observation.get("observed_on") or "0000-00-00",
            observation.get("source") != "catalogo_historico",
        )
        if key not in selected or rank >= selected[key][0]:
            selected[key] = (rank, observation)
    return [value[1] for value in selected.values()]


def build_candidates(requested, products, observations, allow_equivalents, include_loyalty):
    candidates = []
    for observation in observations:
        target = products.get(observation["product_id"])
        if not target:
            continue
        score, reason = product_similarity(requested, target)
        if score == 1 or (allow_equivalents and reason):
            candidates.append({
                "product_id": target["id"], "name": target["name"], "store": observation["store"],
                "price_eur": effective_price(observation, include_loyalty), "score": score, "reason": reason,
                "source": observation.get("source", "manual"), "loyalty_required": observation.get("loyalty_required", False),
            })
    # Una opción idéntica siempre prevalece ante un equivalente de menor calidad.
    exact = [candidate for candidate in candidates if candidate["score"] == 1]
    return exact or sorted(candidates, key=lambda candidate: (candidate["score"] < 0.75, candidate["price_eur"]))[:6]


def optimize(payload):
    catalog = {product["id"]: product for product in load_json(DATA / "catalog.json", [])}
    observations = latest_observations(
        load_json(DATA / "price_observations.json", []) + load_json(CUSTOM_OBSERVATIONS, [])
    )
    items = payload.get("items", [])
    include_loyalty = bool(payload.get("include_loyalty", True))
    allow_equivalents = bool(payload.get("allow_equivalents", True))
    max_stores = max(1, min(5, int(payload.get("max_stores", 3))))
    extra_store_cost = max(0, float(payload.get("extra_store_cost", 0)))

    item_options, unavailable = [], []
    for item in items:
        product = catalog.get(item.get("product_id"))
        quantity = float(item.get("quantity", 1))
        if not product or quantity <= 0:
            continue
        options = build_candidates(product, catalog, observations, allow_equivalents, include_loyalty)
        if not options:
            unavailable.append(product["name"])
        else:
            item_options.append((product, quantity, options))

    states = [{"cost": 0, "stores": set(), "lines": []}]
    for requested, quantity, options in item_options:
        next_states = []
        for state in states:
            for option in options:
                stores = state["stores"] | {option["store"]}
                if len(stores) > max_stores:
                    continue
                next_states.append({
                    "cost": state["cost"] + option["price_eur"] * quantity,
                    "stores": stores,
                    "lines": state["lines"] + [{**option, "requested_name": requested["name"], "quantity": quantity, "line_total": round(option["price_eur"] * quantity, 2)}],
                })
        states = sorted(next_states, key=lambda state: state["cost"] + max(0, len(state["stores"]) - 1) * extra_store_cost)[:120]

    if not states:
        return {"plan": None, "unavailable": unavailable, "message": "No hay precios suficientes para optimizar esta cesta."}
    best = min(states, key=lambda state: state["cost"] + max(0, len(state["stores"]) - 1) * extra_store_cost)
    grouped = {}
    for line in best["lines"]:
        grouped.setdefault(line["store"], []).append(line)
    product_cost = round(best["cost"], 2)
    travel_cost = round(max(0, len(best["stores"]) - 1) * extra_store_cost, 2)
    return {
        "plan": {"stores": grouped, "product_cost": product_cost, "travel_cost": travel_cost, "total": round(product_cost + travel_cost, 2), "store_count": len(best["stores"])},
        "unavailable": unavailable,
        "message": "Los precios del catálogo son históricos hasta que se sustituyan por observaciones recientes.",
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/catalog":
            return self.send_json(load_json(DATA / "catalog.json", []))
        if route == "/api/quality":
            return self.send_json(load_json(DATA / "quality_report.json", {}))
        return super().do_GET()

    def do_POST(self):
        route = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self.send_json({"error": "JSON no válido"}, HTTPStatus.BAD_REQUEST)
        if route == "/api/plan":
            return self.send_json(optimize(payload))
        if route == "/api/observations":
            required = {"product_id", "store", "price_eur"}
            if not required <= payload.keys() or float(payload["price_eur"]) <= 0:
                return self.send_json({"error": "Faltan product_id, store o price_eur válido."}, HTTPStatus.BAD_REQUEST)
            catalog = {product["id"] for product in load_json(DATA / "catalog.json", [])}
            if payload["product_id"] not in catalog:
                return self.send_json({"error": "Producto desconocido."}, HTTPStatus.BAD_REQUEST)
            rows = load_json(CUSTOM_OBSERVATIONS, [])
            rows.append({
                "id": f"manual-{len(rows) + 1}", "product_id": payload["product_id"], "store": str(payload["store"]).strip(),
                "price_eur": float(payload["price_eur"]), "observed_on": payload.get("observed_on") or date.today().isoformat(),
                "promotion_eur": float(payload.get("promotion_eur") or 0), "loyalty_required": bool(payload.get("loyalty_required")),
                "source": "entrada_manual", "confidence": "alta",
            })
            CUSTOM_OBSERVATIONS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            return self.send_json({"saved": True})
        if route == "/api/import-prices":
            try:
                imported = import_csv_text(payload.get("csv_text", ""), DATA / "catalog.json", CUSTOM_OBSERVATIONS)
            except PriceImportError as error:
                return self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return self.send_json({"imported": len(imported)})
        return self.send_json({"error": "Ruta no encontrada"}, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    print("Super Smart MVP en http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
