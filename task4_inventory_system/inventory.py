#!/usr/bin/env python3
"""Task 4 - Object-Oriented Inventory Management System.

A class-based inventory built around a ``Product`` base class and a
``PerishableProduct`` subclass that adds genuinely distinct behaviour (expiry
tracking that blocks the sale of expired goods and drives discounting).

``@property`` is used where validation or controlled access is actually needed:
price/quantity can never go negative, and a product's SKU is immutable.

Covered topics:
    Object-Oriented Programming | Inheritance | Properties & Validation |
    Project Structure

Bonus:
    * ``__str__`` on every model for clean object printing.
    * Reading ahead: a pytest-compatible test suite (``test_inventory.py``).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterator

# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class InventoryError(Exception):
    """Base class for all inventory-related errors."""


class DuplicateSKUError(InventoryError):
    """Raised when adding a product whose SKU already exists."""

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"A product with SKU {sku!r} already exists.")


class UnknownSKUError(InventoryError):
    """Raised when a SKU cannot be found in the inventory."""

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"No product found with SKU {sku!r}.")


class InsufficientStockError(InventoryError):
    """Raised when more stock is removed than is available."""

    def __init__(self, sku: str, requested: int, available: int) -> None:
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__(
            f"Cannot remove {requested} unit(s) of {sku!r}: only {available} in stock."
        )


class ExpiredProductError(InventoryError):
    """Raised when trying to sell stock that has already expired."""

    def __init__(self, sku: str, expiry_date: date) -> None:
        self.sku = sku
        self.expiry_date = expiry_date
        super().__init__(f"Product {sku!r} expired on {expiry_date.isoformat()} and cannot be sold.")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _coerce_date(value: Any) -> date:
    """Accept a ``date``/``datetime`` or an ISO ``YYYY-MM-DD`` string."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date {value!r}: expected YYYY-MM-DD.") from None
    raise ValueError(f"Invalid date {value!r}: expected a date or YYYY-MM-DD string.")


def _require_non_negative_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number, got {type(value).__name__}.")
    number = float(value)
    if number < 0:
        raise ValueError(f"{field} cannot be negative (got {number}).")
    return number


def _require_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a whole number, got {type(value).__name__}.")
    if value <= 0:
        raise ValueError(f"{field} must be greater than zero (got {value}).")
    return value


def _require_non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a whole number, got {type(value).__name__}.")
    if value < 0:
        raise ValueError(f"{field} cannot be negative (got {value}).")
    return value


# --------------------------------------------------------------------------- #
# Base model
# --------------------------------------------------------------------------- #
class Product:
    """A stock item with a price and a quantity on hand."""

    def __init__(
        self,
        sku: str,
        name: str,
        price: float,
        quantity: int = 0,
        low_stock_threshold: int = 5,
    ) -> None:
        self._sku = self._validate_sku(sku)
        self._name = self._validate_name(name)
        self._price = _require_non_negative_number(price, "Price")
        self._quantity = _require_non_negative_int(quantity, "Quantity")
        self._low_stock_threshold = _require_non_negative_int(low_stock_threshold, "Low-stock threshold")

    # -- validation ------------------------------------------------------- #
    @staticmethod
    def _validate_sku(sku: str) -> str:
        text = str(sku).strip().upper()
        if not text:
            raise ValueError("SKU cannot be empty.")
        return text

    @staticmethod
    def _validate_name(name: str) -> str:
        text = str(name).strip()
        if not text:
            raise ValueError("Product name cannot be empty.")
        return text

    # -- properties (validation / controlled access) ---------------------- #
    @property
    def sku(self) -> str:
        """Immutable identifier (read-only)."""
        return self._sku

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = self._validate_name(value)

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        self._price = _require_non_negative_number(value, "Price")

    @property
    def quantity(self) -> int:
        """Units on hand - the setter is what prevents negative stock."""
        return self._quantity

    @quantity.setter
    def quantity(self, value: int) -> None:
        self._quantity = _require_non_negative_int(value, "Quantity")

    @property
    def low_stock_threshold(self) -> int:
        return self._low_stock_threshold

    @low_stock_threshold.setter
    def low_stock_threshold(self, value: int) -> None:
        self._low_stock_threshold = _require_non_negative_int(value, "Low-stock threshold")

    @property
    def total_value(self) -> float:
        """Price x quantity for this line."""
        return round(self._price * self._quantity, 2)

    @property
    def low_stock(self) -> bool:
        """True when stock has dropped to the threshold or below."""
        return self._quantity <= self._low_stock_threshold

    # -- operations ------------------------------------------------------- #
    def add_stock(self, amount: int) -> int:
        """Add ``amount`` units and return the new quantity."""
        self._quantity += _require_positive_int(amount, "Amount")
        return self._quantity

    def remove_stock(self, amount: int) -> int:
        """Remove ``amount`` units and return the new quantity."""
        amount = _require_positive_int(amount, "Amount")
        if amount > self._quantity:
            raise InsufficientStockError(self._sku, amount, self._quantity)
        self._quantity -= amount
        return self._quantity

    def status(self) -> str:
        """Short human-readable status used in reports."""
        return "LOW STOCK" if self.low_stock else "OK"

    # -- representation / serialisation ----------------------------------- #
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "Product",
            "sku": self._sku,
            "name": self._name,
            "price": self._price,
            "quantity": self._quantity,
            "low_stock_threshold": self._low_stock_threshold,
        }

    def __str__(self) -> str:
        return f"{self._name} ({self._sku}) - ${self._price:.2f} x {self._quantity}"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(sku={self._sku!r}, name={self._name!r}, "
            f"price={self._price!r}, quantity={self._quantity!r}, "
            f"low_stock_threshold={self._low_stock_threshold!r})"
        )


# --------------------------------------------------------------------------- #
# Subclass with genuinely distinct behaviour
# --------------------------------------------------------------------------- #
class PerishableProduct(Product):
    """A product with an expiry date.

    Distinct behaviour beyond the base class:
        * Expired stock cannot be sold (``remove_stock`` raises).
        * Near-expiry stock is flagged and a discount is suggested.
        * Adds an expiry column to the report and its own serialisation.
    """

    def __init__(
        self,
        sku: str,
        name: str,
        price: float,
        expiry_date: date | str,
        quantity: int = 0,
        low_stock_threshold: int = 5,
        nearby_expiry_days: int = 3,
    ) -> None:
        super().__init__(sku, name, price, quantity, low_stock_threshold)
        self._expiry_date = _coerce_date(expiry_date)
        self._nearby_expiry_days = _require_non_negative_int(nearby_expiry_days, "Near-expiry window")

    # -- properties ------------------------------------------------------- #
    @property
    def expiry_date(self) -> date:
        return self._expiry_date

    @expiry_date.setter
    def expiry_date(self, value: date | str) -> None:
        self._expiry_date = _coerce_date(value)

    @property
    def is_expired(self) -> bool:
        return self._expiry_date < date.today()

    @property
    def days_until_expiry(self) -> int:
        """Days remaining (negative when already expired)."""
        return (self._expiry_date - date.today()).days

    @property
    def is_near_expiry(self) -> bool:
        return not self.is_expired and self.days_until_expiry <= self._nearby_expiry_days

    # -- distinct behaviour ---------------------------------------------- #
    def suggested_discount(self) -> float:
        """Return a discount percentage (0-50) based on how close expiry is."""
        days = self.days_until_expiry
        if days < 0:
            return 0.0
        if days == 0:
            return 50.0
        if days <= 2:
            return 30.0
        if days <= self._nearby_expiry_days:
            return 15.0
        return 0.0

    def remove_stock(self, amount: int) -> int:
        """Sell stock - but refuse to sell anything that has already expired."""
        if self.is_expired:
            raise ExpiredProductError(self._sku, self._expiry_date)
        return super().remove_stock(amount)

    def status(self) -> str:
        if self.is_expired:
            return "EXPIRED"
        if self.is_near_expiry:
            return f"EXPIRES IN {self.days_until_expiry}d"
        return super().status()

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "type": "PerishableProduct",
                "expiry_date": self._expiry_date.isoformat(),
                "nearby_expiry_days": self._nearby_expiry_days,
            }
        )
        return data

    def __str__(self) -> str:
        state = "expired" if self.is_expired else f"expires in {self.days_until_expiry} day(s)"
        return f"{super().__str__()} [{state}]"


def product_from_dict(data: dict[str, Any]) -> Product:
    """Rebuild a ``Product`` or ``PerishableProduct`` from its dict form."""
    kind = data.get("type", "Product")

    if kind == "PerishableProduct":
        return PerishableProduct(
            sku=data["sku"],
            name=data["name"],
            price=data["price"],
            expiry_date=data["expiry_date"],
            quantity=data.get("quantity", 0),
            low_stock_threshold=data.get("low_stock_threshold", 5),
            nearby_expiry_days=data.get("nearby_expiry_days", 3),
        )

    return Product(
        sku=data["sku"],
        name=data["name"],
        price=data["price"],
        quantity=data.get("quantity", 0),
        low_stock_threshold=data.get("low_stock_threshold", 5),
    )


# --------------------------------------------------------------------------- #
# Inventory collection
# --------------------------------------------------------------------------- #
class Inventory:
    """A collection of products keyed by SKU, with reporting and alerts."""

    def __init__(self, products: list[Product] | None = None) -> None:
        self._products: dict[str, Product] = {}
        for product in products or []:
            self.add_product(product)

    # -- dunder ----------------------------------------------------------- #
    def __len__(self) -> int:
        return len(self._products)

    def __iter__(self) -> Iterator[Product]:
        return iter(self._products.values())

    def __contains__(self, sku: object) -> bool:
        return isinstance(sku, str) and sku.strip().upper() in self._products

    # -- CRUD ------------------------------------------------------------- #
    def add_product(self, product: Product) -> Product:
        """Add a product, rejecting a duplicate SKU."""
        if product.sku in self._products:
            raise DuplicateSKUError(product.sku)
        self._products[product.sku] = product
        return product

    def remove_product(self, sku: str) -> Product:
        """Remove and return a product by SKU."""
        return self._products.pop(self._normalise(sku), None) or self._missing(sku)

    def get(self, sku: str) -> Product:
        """Look up a product by SKU."""
        return self._products.get(self._normalise(sku)) or self._missing(sku)

    def add_stock(self, sku: str, amount: int) -> int:
        return self.get(sku).add_stock(amount)

    def remove_stock(self, sku: str, amount: int) -> int:
        return self.get(sku).remove_stock(amount)

    # -- queries ---------------------------------------------------------- #
    @property
    def total_units(self) -> int:
        return sum(product.quantity for product in self)

    @property
    def total_value(self) -> float:
        return round(sum(product.total_value for product in self), 2)

    def low_stock_products(self) -> list[Product]:
        """Products at or below their low-stock threshold, emptiest first."""
        return sorted(
            (product for product in self if product.low_stock),
            key=lambda product: product.quantity,
        )

    def expired_products(self) -> list[PerishableProduct]:
        """Perishable products that are past their expiry date."""
        return [p for p in self if isinstance(p, PerishableProduct) and p.is_expired]

    def expiring_soon(self) -> list[PerishableProduct]:
        """Perishable products approaching expiry, soonest first."""
        return sorted(
            (p for p in self if isinstance(p, PerishableProduct) and p.is_near_expiry),
            key=lambda p: p.days_until_expiry,
        )

    # -- reporting -------------------------------------------------------- #
    def report(self) -> str:
        """Return a formatted multi-section inventory report."""
        lines: list[str] = []
        width = 70

        lines.append("=" * width)
        lines.append("INVENTORY REPORT".center(width))
        lines.append("=" * width)
        lines.append(f"Products: {len(self):<10}Units on hand: {self.total_units}")
        lines.append(f"Total value: ${self.total_value:,.2f}")
        lines.append("")

        header = f"{'SKU':<10}{'NAME':<22}{'PRICE':>9}{'QTY':>6}{'VALUE':>11}  {'STATUS':<12}"
        lines.append("-" * width)
        lines.append(header)
        lines.append("-" * width)

        if not self._products:
            lines.append("(no products)")
        else:
            for product in sorted(self, key=lambda p: p.sku):
                lines.append(
                    f"{product.sku:<10}"
                    f"{product.name:<22}"
                    f"{product.price:>9.2f}"
                    f"{product.quantity:>6}"
                    f"{product.total_value:>11.2f}  "
                    f"{product.status():<12}"
                )

        lines.append("-" * width)

        low_stock = self.low_stock_products()
        if low_stock:
            lines.append("")
            lines.append("LOW-INVENTORY ALERTS")
            for product in low_stock:
                lines.append(
                    f"  ! {product.name} ({product.sku}) - only {product.quantity} left "
                    f"(threshold {product.low_stock_threshold})"
                )

        expiring = self.expiring_soon()
        if expiring:
            lines.append("")
            lines.append("EXPIRING SOON")
            for product in expiring:
                lines.append(
                    f"  ~ {product.name} ({product.sku}) - expires in {product.days_until_expiry} day(s); "
                    f"suggested discount {product.suggested_discount():.0f}%"
                )

        expired = self.expired_products()
        if expired:
            lines.append("")
            lines.append("EXPIRED - DO NOT SELL")
            for product in expired:
                lines.append(
                    f"  X {product.name} ({product.sku}) - expired {product.expiry_date.isoformat()} "
                    f"({product.quantity} unit(s) to write off)"
                )

        lines.append("")
        lines.append("=" * width)
        return "\n".join(lines)

    # -- internals -------------------------------------------------------- #
    @staticmethod
    def _normalise(sku: str) -> str:
        return str(sku).strip().upper()

    @staticmethod
    def _missing(sku: str) -> Any:
        raise UnknownSKUError(sku)
