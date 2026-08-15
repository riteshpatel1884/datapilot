"""
Creates a sample SQLite DB simulating mall purchase data —
30 customers with realistic order history across mall categories.

Run: python db/setup_db.py   (or: uv run python db/setup_db.py)

Schema stays compatible with the existing pipeline (customers/orders
tables, same core column names the validator and few-shot examples
expect) — just extended with item_name and category on orders so
richer questions ("what's the best-selling category?") become possible.
"""
import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "sample.db")

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
    "Ishaan", "Rohan", "Ananya", "Diya", "Saanvi", "Aadhya", "Kavya", "Myra",
    "Anika", "Riya", "Priya", "Neha", "Pooja", "Simran", "Karan", "Rahul",
    "Amit", "Sanjay", "Vikram", "Nikhil", "Tanvi", "Meera",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Mehta", "Reddy",
    "Nair", "Iyer", "Chopra", "Malhotra", "Kapoor", "Joshi", "Rao",
]
CITIES = ["Delhi", "Mumbai", "Bangalore", "Gurgaon", "Noida", "Pune", "Hyderabad", "Chennai"]

# category -> list of (item_name, typical_price_range)
MALL_ITEMS = {
    "Electronics": [
        ("Wireless Earbuds", (1500, 4500)),
        ("Bluetooth Speaker", (1200, 3500)),
        ("Smartwatch", (2500, 8000)),
        ("Power Bank", (900, 2200)),
        ("Phone Case", (300, 900)),
    ],
    "Fashion": [
        ("Denim Jacket", (1800, 3500)),
        ("Cotton T-Shirt", (400, 1200)),
        ("Formal Shirt", (900, 2200)),
        ("Sneakers", (2000, 6000)),
        ("Handbag", (1500, 5000)),
    ],
    "Grocery": [
        ("Grocery Basket - Weekly", (800, 2500)),
        ("Organic Snack Pack", (300, 900)),
        ("Beverages Combo", (400, 1100)),
    ],
    "Footwear": [
        ("Running Shoes", (2200, 5500)),
        ("Casual Sandals", (600, 1800)),
        ("Formal Shoes", (1800, 4500)),
    ],
    "Toys": [
        ("Building Blocks Set", (700, 2000)),
        ("Remote Control Car", (1200, 3500)),
        ("Board Game", (500, 1500)),
    ],
    "Books": [
        ("Fiction Novel", (250, 700)),
        ("Self-Help Book", (300, 800)),
        ("Kids Story Set", (400, 1200)),
    ],
    "Home Decor": [
        ("Table Lamp", (900, 2800)),
        ("Wall Art Frame", (600, 2000)),
        ("Scented Candle Set", (400, 1200)),
    ],
    "Food Court": [
        ("Combo Meal", (250, 600)),
        ("Ice Cream Tub", (200, 500)),
        ("Coffee & Snack", (150, 400)),
    ],
}

NUM_CUSTOMERS = 30
MIN_ORDERS_PER_CUSTOMER = 2
MAX_ORDERS_PER_CUSTOMER = 12


def random_date(start_days_ago=240, end_days_ago=1):
    days_ago = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def setup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT,
            signup_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            order_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    # --- Generate 30 customers ---
    used_names = set()
    customers = []
    for cust_id in range(1, NUM_CUSTOMERS + 1):
        while True:
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break
        city = random.choice(CITIES)
        signup_date = random_date(start_days_ago=500, end_days_ago=250)
        customers.append((cust_id, name, city, signup_date))

    cur.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)

    # --- Generate orders per customer ---
    order_id = 1
    orders = []
    for cust_id, *_ in customers:
        num_orders = random.randint(MIN_ORDERS_PER_CUSTOMER, MAX_ORDERS_PER_CUSTOMER)
        for _ in range(num_orders):
            category = random.choice(list(MALL_ITEMS.keys()))
            item_name, (low, high) = random.choice(MALL_ITEMS[category])
            amount = round(random.uniform(low, high), 2)
            order_date = random_date()
            orders.append((order_id, cust_id, item_name, category, amount, order_date))
            order_id += 1

    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)

    conn.commit()
    conn.close()

    print(f"Sample DB created at {DB_PATH}")
    print(f"  {len(customers)} customers")
    print(f"  {len(orders)} orders across {len(MALL_ITEMS)} categories")


if __name__ == "__main__":
    setup()