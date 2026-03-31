from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from backend.core.config import settings


DEFAULT_CATALOG: list[dict[str, str]] = [
    {"sku": "beverage_tea", "label": "Beverage - Tea", "name": "Tea", "unit_price": "5.00", "size": "regular", "specs": "sweetness=low"},
    {"sku": "beverage_coffee", "label": "Beverage - Coffee", "name": "Coffee", "unit_price": "6.00", "size": "regular", "specs": "milk=whole"},
    {"sku": "beverage_juice", "label": "Beverage - Juice", "name": "Juice", "unit_price": "7.00", "size": "small", "specs": "ice=no"},
    {"sku": "food_soup", "label": "Room Service - Soup", "name": "Soup", "unit_price": "12.00", "size": "regular", "specs": "bread=side"},
    {"sku": "food_club_sandwich", "label": "Room Service - Club Sandwich", "name": "Club sandwich", "unit_price": "14.00", "size": "regular", "specs": "sauce=light"},
    {"sku": "spa_express_massage", "label": "Spa Add-on - Express Massage", "name": "Express massage add-on", "unit_price": "65.00", "size": "30min", "specs": "therapist=any"},
    {"sku": "late_checkout_2pm", "label": "Late Checkout - 2 PM", "name": "Late checkout extension", "unit_price": "45.00", "size": "2pm", "specs": "floor=any"},
    {"sku": "amenity_welcome_basket", "label": "Amenity - Welcome Basket", "name": "Welcome amenity basket", "unit_price": "32.00", "size": "standard", "specs": "snacks=mixed"},
]


def _catalog_path() -> Path:
    configured = Path(settings.order_catalog_path)
    if configured.is_absolute():
        return configured
    return Path.cwd() / configured


def load_catalog_items() -> list[dict[str, str]]:
    path = _catalog_path()
    if not path.exists():
        return [dict(item) for item in DEFAULT_CATALOG]
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Order catalog JSON must be an array.")

    items: list[dict[str, str]] = []
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("Each catalog row must be an object.")
        sku = str(row.get("sku") or "").strip()
        name = str(row.get("name") or "").strip()
        unit_price = str(row.get("unit_price") or "").strip()
        if not sku or not name or not unit_price:
            raise ValueError("Catalog rows require sku, name, and unit_price.")
        Decimal(unit_price)
        items.append(
            {
                "sku": sku,
                "label": str(row.get("label") or name).strip(),
                "name": name,
                "unit_price": unit_price,
                "size": str(row.get("size") or "").strip(),
                "specs": str(row.get("specs") or "").strip(),
            }
        )
    return items


def catalog_price_maps() -> tuple[dict[str, tuple[str, Decimal]], dict[str, str]]:
    by_sku: dict[str, tuple[str, Decimal]] = {}
    name_to_sku: dict[str, str] = {}
    for item in load_catalog_items():
        sku = item["sku"]
        by_sku[sku] = (item["name"], Decimal(item["unit_price"]))
        name_to_sku[item["name"].lower()] = sku
    return by_sku, name_to_sku
