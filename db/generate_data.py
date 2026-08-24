"""
Generates the sample mall-purchase data as CSV files —
db/customers.csv and db/orders.csv.

This is the SOURCE OF TRUTH for the demo data. Run this once (or
whenever you want fresh/different sample data), commit the resulting
CSVs to git, and setup_db.py will load the SQLite database from them.

Run: python db/generate_data.py   (or: uv run python db/generate_data.py)

FIX vs the old inline-generation approach: this version is seeded
(random.seed(SEED)), so re-running it produces the SAME data every
time. The old setup_db.py had no seed, meaning every fresh deploy or
re-run silently generated DIFFERENT random customers/orders — causing
production data to drift from whatever you'd tested against locally.
CSVs are also readable/diffable in git, unlike a binary .db file, so
you can actually see what changed in a commit.
"""
import csv
import os
import random
from datetime import datetime, timedelta

SEED = 42  # change this deliberately if you want a different dataset

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
CUSTOMERS_CSV = os.path.join(OUTPUT_DIR, "customers.csv")
ORDERS_CSV = os.path.join(OUTPUT_DIR, "orders.csv")

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


def random_date(rng: random.Random, start_days_ago=240, end_days_ago=1):
    days_ago = rng.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def generate():
    rng = random.Random(SEED)  # dedicated instance, seeded deterministically

    # --- Generate customers ---
    used_names = set()
    customers = []
    for cust_id in range(1, NUM_CUSTOMERS + 1):
        while True:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break
        city = rng.choice(CITIES)
        signup_date = random_date(rng, start_days_ago=500, end_days_ago=250)
        customers.append((cust_id, name, city, signup_date))

    # --- Generate orders per customer ---
    order_id = 1
    orders = []
    for cust_id, *_ in customers:
        num_orders = rng.randint(MIN_ORDERS_PER_CUSTOMER, MAX_ORDERS_PER_CUSTOMER)
        for _ in range(num_orders):
            category = rng.choice(list(MALL_ITEMS.keys()))
            item_name, (low, high) = rng.choice(MALL_ITEMS[category])
            amount = round(rng.uniform(low, high), 2)
            order_date = random_date(rng)
            orders.append((order_id, cust_id, item_name, category, amount, order_date))
            order_id += 1

    # --- Write CSVs ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(CUSTOMERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_id", "name", "city", "signup_date"])
        writer.writerows(customers)

    with open(ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "customer_id", "item_name", "category", "amount", "order_date"])
        writer.writerows(orders)

    print(f"Wrote {CUSTOMERS_CSV} ({len(customers)} customers)")
    print(f"Wrote {ORDERS_CSV} ({len(orders)} orders across {len(MALL_ITEMS)} categories)")
    print("\nNext: run 'python db/load_csvs.py' to load these (or any other CSVs in db/data/) into sample.db")


if __name__ == "__main__":
    generate()