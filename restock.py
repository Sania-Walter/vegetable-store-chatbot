#!/usr/bin/env python
import sqlite3, sys
from pathlib import Path

DB_PATH = Path(__file__).with_name("store.db")

def main(argv):
    if len(argv) not in (3, 4):
        sys.exit("Usage: python restock.py <name> <qty> [price]")

    veg  = argv[1].lower()
    try:
        qty = float(argv[2])
    except ValueError:
        sys.exit("Quantity must be a number")

    price = float(argv[3]) if len(argv) == 4 else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO inventory (name, qty, price_per_kg)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
              qty = inventory.qty + excluded.qty,
              price_per_kg = COALESCE(excluded.price_per_kg, inventory.price_per_kg)
            """,
            (veg, qty, price)
        )
        conn.commit()

    line = f"✅ Restocked {qty} kg of {veg}"
    if price is not None:
        line += f" at ₹{price}/kg"
    print(line)

if __name__ == "__main__":
    main(sys.argv)
