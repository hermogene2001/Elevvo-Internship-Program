#!/usr/bin/env python3
"""Tests for the inventory system.

Run with either::

    python -m unittest test_inventory -v
    pytest test_inventory.py -v
"""

from __future__ import annotations

import unittest
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


class TestProductValidation(unittest.TestCase):
    def test_basic_construction(self) -> None:
        product = Product("kb-1", "Keyboard", 50.0, quantity=4, low_stock_threshold=3)
        self.assertEqual(product.sku, "KB-1")  # normalised
        self.assertEqual(product.quantity, 4)
        self.assertFalse(product.low_stock)

    def test_negative_quantity_rejected_by_setter(self) -> None:
        product = Product("A1", "Thing", 10.0, quantity=3)
        with self.assertRaises(ValueError):
            product.quantity = -1
        self.assertEqual(product.quantity, 3)  # unchanged

    def test_negative_price_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Product("A1", "Thing", -5.0)

    def test_blank_name_or_sku_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Product("", "Thing", 1.0)
        with self.assertRaises(ValueError):
            Product("A1", "   ", 1.0)

    def test_sku_is_read_only(self) -> None:
        product = Product("A1", "Thing", 1.0)
        with self.assertRaises(AttributeError):
            product.sku = "B2"  # type: ignore[misc]

    def test_total_value(self) -> None:
        self.assertEqual(Product("A1", "Thing", 2.5, quantity=4).total_value, 10.0)


class TestStockOperations(unittest.TestCase):
    def setUp(self) -> None:
        self.product = Product("A1", "Thing", 10.0, quantity=5, low_stock_threshold=3)

    def test_add_stock(self) -> None:
        self.assertEqual(self.product.add_stock(5), 10)

    def test_remove_stock(self) -> None:
        self.assertEqual(self.product.remove_stock(2), 3)

    def test_oversell_raises(self) -> None:
        with self.assertRaises(InsufficientStockError):
            self.product.remove_stock(6)
        self.assertEqual(self.product.quantity, 5)

    def test_non_positive_amounts_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.product.add_stock(0)
        with self.assertRaises(ValueError):
            self.product.remove_stock(-3)

    def test_low_stock_flag(self) -> None:
        self.assertFalse(self.product.low_stock)
        self.product.remove_stock(2)
        self.assertTrue(self.product.low_stock)


class TestPerishableProduct(unittest.TestCase):
    def test_expiry_properties(self) -> None:
        product = PerishableProduct("M1", "Milk", 2.0, expiry_date=date.today() + timedelta(days=5))
        self.assertFalse(product.is_expired)
        self.assertEqual(product.days_until_expiry, 5)

    def test_accepts_iso_string(self) -> None:
        iso = (date.today() + timedelta(days=2)).isoformat()
        self.assertEqual(PerishableProduct("M1", "Milk", 2.0, expiry_date=iso).expiry_date.isoformat(), iso)

    def test_invalid_date_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PerishableProduct("M1", "Milk", 2.0, expiry_date="not-a-date")

    def test_expired_cannot_be_sold(self) -> None:
        product = PerishableProduct(
            "M1", "Milk", 2.0, expiry_date=date.today() - timedelta(days=1), quantity=4
        )
        with self.assertRaises(ExpiredProductError):
            product.remove_stock(1)
        self.assertEqual(product.quantity, 4)

    def test_near_expiry_discount(self) -> None:
        soon = PerishableProduct("M1", "Milk", 2.0, expiry_date=date.today(), quantity=1)
        later = PerishableProduct("M2", "Cheese", 5.0, expiry_date=date.today() + timedelta(days=30), quantity=1)
        self.assertGreater(soon.suggested_discount(), 0)
        self.assertEqual(later.suggested_discount(), 0)

    def test_expiry_status_text(self) -> None:
        expired = PerishableProduct("M1", "Milk", 2.0, expiry_date=date.today() - timedelta(days=1))
        self.assertEqual(expired.status(), "EXPIRED")

    def test_polymorphism_and_serialisation_roundtrip(self) -> None:
        original = PerishableProduct(
            "M1", "Milk", 2.0, expiry_date=date.today() + timedelta(days=7), quantity=3
        )
        restored = product_from_dict(original.to_dict())
        self.assertIsInstance(restored, PerishableProduct)
        self.assertEqual(restored.expiry_date, original.expiry_date)
        self.assertEqual(restored.quantity, 3)
        # Expired rules still apply after the round trip.
        restored.expiry_date = date.today() - timedelta(days=1)
        with self.assertRaises(ExpiredProductError):
            restored.remove_stock(1)

    def test_str_mentions_expiry(self) -> None:
        product = PerishableProduct("M1", "Milk", 2.0, expiry_date=date.today(), quantity=1)
        self.assertIn("expire", str(product))


class TestInventory(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = Inventory(
            [
                Product("A1", "Alpha", 10.0, quantity=10, low_stock_threshold=2),
                Product("B2", "Beta", 5.0, quantity=1, low_stock_threshold=3),
                PerishableProduct("C3", "Cream", 4.0, expiry_date=date.today() - timedelta(days=1), quantity=2),
            ]
        )

    def test_len_and_contains(self) -> None:
        self.assertEqual(len(self.inventory), 3)
        self.assertIn("a1", self.inventory)  # case-insensitive
        self.assertNotIn("Z9", self.inventory)

    def test_duplicate_sku_rejected(self) -> None:
        with self.assertRaises(DuplicateSKUError):
            self.inventory.add_product(Product("A1", "Clone", 1.0))

    def test_unknown_sku_raises(self) -> None:
        with self.assertRaises(UnknownSKUError):
            self.inventory.get("ZZ")
        with self.assertRaises(UnknownSKUError):
            self.inventory.remove_product("ZZ")

    def test_totals(self) -> None:
        self.assertEqual(self.inventory.total_units, 13)
        self.assertEqual(self.inventory.total_value, round(10 * 10 + 5 * 1 + 4 * 2, 2))

    def test_low_stock_query(self) -> None:
        low = self.inventory.low_stock_products()
        # B2 (qty 1, threshold 3) and C3 (qty 2, default threshold 5), emptiest first.
        self.assertEqual([p.sku for p in low], ["B2", "C3"])

    def test_expired_and_expiring_queries(self) -> None:
        self.assertEqual([p.sku for p in self.inventory.expired_products()], ["C3"])
        self.assertEqual(self.inventory.expiring_soon(), [])

    def test_report_renders_alerts(self) -> None:
        report = self.inventory.report()
        self.assertIn("LOW-INVENTORY ALERTS", report)
        self.assertIn("EXPIRED - DO NOT SELL", report)

    def test_remove_product(self) -> None:
        removed = self.inventory.remove_product("A1")
        self.assertEqual(removed.sku, "A1")
        self.assertNotIn("A1", self.inventory)

    def test_add_and_remove_stock_via_inventory(self) -> None:
        self.assertEqual(self.inventory.add_stock("A1", 5), 15)
        self.assertEqual(self.inventory.remove_stock("A1", 5), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
