# Task 4 — Object-Oriented Inventory Management System

**Level 2 · Module 5 · Tools: Python (standard library only)**

An inventory system built on a `Product` base class and a `PerishableProduct`
subclass that adds **genuinely distinct behaviour** — not an empty extension.

**Covered topics:** Object-Oriented Programming · Inheritance · Properties & Validation · Project Structure

**Bonus implemented:** `__str__` / `__repr__` on every model for clean object
printing, plus a pytest-compatible test suite (reading ahead).

## Files

| File | Purpose |
|------|---------|
| `inventory.py` | Models + exceptions + the `Inventory` collection and reporting. |
| `main.py` | Scripted demo exercising every behaviour. |
| `test_inventory.py` | 25 unit tests (stdlib `unittest`, also runs under `pytest`). |

## Run

```bash
cd task4_inventory_system
python main.py            # scripted demo
python main.py --quiet    # report only

python -m unittest test_inventory -v
# or:  pytest test_inventory.py -v
```

## Design

### `Product` (base class)
- Fields: `sku` (immutable), `name`, `price`, `quantity`, `low_stock_threshold`.
- **`@property` validation where it matters:**
  - `quantity` setter rejects negative values → **negative stock is impossible**.
  - `price` setter rejects negative values.
  - `name` setter rejects blank strings.
  - `sku` has **no setter** → controlled access to the identifier.
- Derived properties: `total_value` (price × quantity) and `low_stock`.
- Operations: `add_stock()`, `remove_stock()`, `status()`.
- `to_dict()` for serialisation and a readable `__str__` / `__repr__`.

### `PerishableProduct` (subclass — distinct behaviour)
- Adds `expiry_date` (accepts a `date` or an ISO `YYYY-MM-DD` string).
- **Real behavioural differences, not just a new attribute:**
  - `remove_stock()` is **overridden to refuse selling expired goods**
    (`ExpiredProductError`) — the base class knows nothing about this.
  - `is_expired`, `days_until_expiry`, `is_near_expiry`.
  - `suggested_discount()` — expiry-driven discount (50% today → 30% ≤2 days →
    15% within the window → 0%).
  - `status()` shows `EXPIRED` / `EXPIRES IN Nd`.
  - Extends `to_dict()` so a round trip rebuilds the correct subtype.

### `Inventory` (collection)
- `dict` keyed by normalised SKU; `add_product` rejects duplicate SKUs.
- Convenience wrappers: `add_stock(sku, n)`, `remove_stock(sku, n)`, `get`, `remove_product`.
- Queries: `low_stock_products()`, `expired_products()`, `expiring_soon()`, `total_units`, `total_value`.
- `report()` renders the product table plus **low-inventory alerts**, an
  **expiring-soon** section with suggested discounts, and an
  **"EXPIRED — DO NOT SELL"** write-off list.
- Implements `__len__`, `__iter__`, `__contains__` for Pythonic use.

### Exceptions
`InventoryError` (base) → `DuplicateSKUError`, `UnknownSKUError`,
`InsufficientStockError`, `ExpiredProductError`. Each carries structured context
(e.g. `requested` vs `available`) in addition to a clear message.

## Sample report

```
======================================================================
                          INVENTORY REPORT
======================================================================
Products: 7         Units on hand: 92
Total value: $1,740.70

SKU       NAME                      PRICE   QTY      VALUE  STATUS
----------------------------------------------------------------------
CB-900    USB-C Cable                9.75    40     390.00  OK
CH-002    Cheddar Block              6.40    15      96.00  OK
HD-500    USB-C Hub                 39.00     0       0.00  LOW STOCK
KB-100    Mechanical Keyboard       89.99    10     899.90  OK
ML-001    Whole Milk 1L              2.10     8      16.80  EXPIRES IN 1d
MS-200    Wireless Mouse            24.50    13     318.50  OK
YG-003    Greek Yogurt 500g          3.25     6      19.50  EXPIRED
----------------------------------------------------------------------

LOW-INVENTORY ALERTS
  ! USB-C Hub (HD-500) - only 0 left (threshold 2)

EXPIRING SOON
  ~ Whole Milk 1L (ML-001) - expires in 1 day(s); suggested discount 30%

EXPIRED - DO NOT SELL
  X Greek Yogurt 500g (YG-003) - expired 2026-10-18 (6 unit(s) to write off)
======================================================================
```
