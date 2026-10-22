#!/usr/bin/env python3
"""Task 4 - demo driver for the inventory system.

Runs a scripted scenario that exercises the core operations and the
PerishableProduct-specific behaviour, then prints the formatted report.

Usage:
    python main.py            # scripted demo
    python main.py --quiet    # demo without the step-by-step narration
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from inventory import (
    DuplicateSKUError,
    ExpiredProductError,
    InsufficientStockError,
    Inventory,
    PerishableProduct,
    Product,
    UnknownSKUError,
    product_from_dict,
)


def build_sample_inventory() -> Inventory:
    """Create a small inventory with a mix of regular and perishable items."""
    today = date.today()

    return Inventory(
        [
            Product("KB-100", "Mechanical Keyboard", 89.99, quantity=12, low_stock_threshold=4),
            Product("MS-200", "Wireless Mouse", 24.50, quantity=3, low_stock_threshold=5),
            Product("HD-500", "USB-C Hub", 39.00, quantity=0, low_stock_threshold=2),
            Product("CB-900", "USB-C Cable", 9.75, quantity=40, low_stock_threshold=10),
            PerishableProduct("ML-001", "Whole Milk 1L", 2.10, expiry_date=today + timedelta(days=1), quantity=8),
            PerishableProduct("CH-002", "Cheddar Block", 6.40, expiry_date=today + timedelta(days=10), quantity=15),
            PerishableProduct("YG-003", "Greek Yogurt 500g", 3.25, expiry_date=today - timedelta(days=1), quantity=6),
        ]
    )


def step(message: str) -> None:
    print(f"\n>> {message}")


def demo(verbose: bool = True) -> None:
    inventory = build_sample_inventory()

    if verbose:
        step("Built inventory from Product and PerishableProduct instances")
        for product in inventory:
            print(f"   {product!r}")

    # --- core operations ---------------------------------------------- #
    if verbose:
        step("Add stock: +10 Mice")
    print(f"   MS-200 quantity -> {inventory.add_stock('MS-200', 10)}")

    if verbose:
        step("Remove stock: -2 Keyboards")
    print(f"   KB-100 quantity -> {inventory.remove_stock('KB-100', 2)}")

    # --- validation / error handling ---------------------------------- #
    if verbose:
        step("Error handling")

    checks: list[tuple[str, callable]] = [
        ("negative quantity rejected", lambda: setattr(inventory.get("KB-100"), "quantity", -5)),
        ("negative price rejected", lambda: setattr(inventory.get("KB-100"), "price", -1)),
        ("oversell rejected", lambda: inventory.remove_stock("KB-100", 999)),
        ("duplicate SKU rejected", lambda: inventory.add_product(Product("KB-100", "Clone", 1.0))),
        ("unknown SKU rejected", lambda: inventory.get("NOPE-1")),
        ("selling expired stock rejected", lambda: inventory.remove_stock("YG-003", 1)),
    ]

    for label, action in checks:
        try:
            action()
            print(f"   [UNEXPECTED] {label} did not raise")
        except (InsufficientStockError, DuplicateSKUError, UnknownSKUError,
                ExpiredProductError, ValueError) as exc:
            print(f"   [ok] {label}: {type(exc).__name__}: {exc}")

    # --- polymorphic expiry behaviour --------------------------------- #
    yogurt = inventory.get("YG-003")
    if isinstance(yogurt, PerishableProduct) and verbose:
        step("PerishableProduct-specific behaviour")
        print(f"   {yogurt}")
        print(f"   is_expired={yogurt.is_expired} days_until_expiry={yogurt.days_until_expiry}")
        print(f"   suggested_discount={yogurt.suggested_discount():.0f}%")

    # --- round-trip serialisation -------------------------------------- #
    if verbose:
        step("Serialise and rebuild (to_dict / product_from_dict)")
    for product in list(inventory)[-2:]:
        restored = product_from_dict(product.to_dict())
        print(f"   {type(restored).__name__:<18} -> {restored}")

    # --- report --------------------------------------------------------- #
    print()
    print(inventory.report())


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory management demo")
    parser.add_argument("--quiet", action="store_true", help="Only print the final report.")
    args = parser.parse_args()

    demo(verbose=not args.quiet)


if __name__ == "__main__":
    main()
