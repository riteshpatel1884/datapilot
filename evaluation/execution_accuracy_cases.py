"""
Execution-accuracy dataset — Experiment 1 (v2: trimmed to 90 cases).

CHANGE FROM v1 (112 cases): trimmed to fit Groq's 200,000 tokens/day
free-tier budget in a single clean pass. Measured from the v1 run: the
pipeline averages ~2,200 tokens/case (one classify call + one generate
call, each carrying retrieved schema/examples). 112 cases needed
~246,000 tokens — over budget before any retries even happened. 90
cases needs ~198,000 — tight, but fits in one pass. The checkpoint/
resume system in run_execution_accuracy.py remains as a safety net
regardless, since this is still close to the edge.

The 22 cuts were NOT random — they specifically removed:
  1. The one acknowledged bad test case (`median_style_middle_order`,
     phrased in an artificially technical way no real user would type).
  2. Cases with genuine SQL-shape ambiguity (wide/pivoted vs long/
     grouped answers to "compare X vs Y" questions) that would fail
     under ANY reasonable scoring method, strict or lenient, because
     there's no single correct row shape — not because the pipeline
     is wrong.
  3. Near-duplicate query shapes within categories that had heavy
     redundancy, to maximize distinct coverage per token spent, not
     just case count.

Every other design property from v1 is preserved unchanged: every
case is deliberately unambiguous, ground truth is NEVER hardcoded
(every `ground_truth_sql` executes live against the current database),
and the dynamically-fetched sample customer/city/category/item values
mean this file stays valid after the CSVs are regenerated with a
different seed or row count.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from executor.db_executor import execute_query


def _first_value(sql: str, fallback: str) -> str:
    result = execute_query(sql)
    if result.success and result.rows:
        return result.rows[0][0]
    return fallback


_SAMPLE_CUSTOMER = _first_value("SELECT name FROM customers ORDER BY customer_id LIMIT 1", "Unknown Customer")
_SAMPLE_CUSTOMER_2 = _first_value("SELECT name FROM customers ORDER BY customer_id DESC LIMIT 1", "Unknown Customer")
_SAMPLE_CITY = _first_value("SELECT city FROM customers WHERE city IS NOT NULL ORDER BY customer_id LIMIT 1", "Delhi")
_SAMPLE_CATEGORY = _first_value("SELECT category FROM orders ORDER BY order_id LIMIT 1", "Electronics")
_SAMPLE_CATEGORY_2 = _first_value(
    "SELECT category FROM orders WHERE category != '" + _SAMPLE_CATEGORY + "' LIMIT 1", "Fashion"
)
_SAMPLE_ITEM = _first_value("SELECT item_name FROM orders ORDER BY order_id LIMIT 1", "Wireless Earbuds")


def _case(id_, query, sql):
    return {"id": id_, "query": query, "expected_type": "result", "ground_truth_sql": sql}


EXECUTION_ACCURACY_CASES = []

# ============================================================
# A. Basic counts (7)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("count_customers", "how many customers are there?",
          "SELECT COUNT(*) AS customer_count FROM customers"),
    _case("count_orders", "how many orders have been placed?",
          "SELECT COUNT(*) AS order_count FROM orders"),
    _case("count_distinct_cities", "how many different cities do customers come from?",
          "SELECT COUNT(DISTINCT city) AS city_count FROM customers"),
    _case("count_distinct_categories", "how many product categories are there?",
          "SELECT COUNT(DISTINCT category) AS category_count FROM orders"),
    _case("count_distinct_items", "how many distinct items have been ordered?",
          "SELECT COUNT(DISTINCT item_name) AS item_count FROM orders"),
    _case("count_customers_with_orders", "how many customers have placed at least one order?",
          "SELECT COUNT(DISTINCT customer_id) AS customers_with_orders FROM orders"),
    _case("count_high_value_orders", "how many orders were over 2000?",
          "SELECT COUNT(*) AS high_value_orders FROM orders WHERE amount > 2000"),
]

# ============================================================
# B. Basic aggregates — sum / avg / min / max, whole table (8)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("total_revenue", "what is the total revenue across all orders?",
          "SELECT SUM(amount) AS total_revenue FROM orders"),
    _case("average_order_amount", "what is the average order amount?",
          "SELECT AVG(amount) AS avg_amount FROM orders"),
    _case("max_order_amount", "what is the highest single order amount?",
          "SELECT MAX(amount) AS max_amount FROM orders"),
    _case("min_order_amount", "what is the lowest single order amount?",
          "SELECT MIN(amount) AS min_amount FROM orders"),
    _case("earliest_order_date", "what is the earliest order date on record?",
          "SELECT MIN(order_date) AS earliest_date FROM orders"),
    _case("latest_order_date", "what is the most recent order date on record?",
          "SELECT MAX(order_date) AS latest_date FROM orders"),
    _case("earliest_signup", "who has the earliest signup date?",
          "SELECT name, signup_date FROM customers ORDER BY signup_date ASC LIMIT 1"),
    _case("latest_signup", "who signed up most recently?",
          "SELECT name, signup_date FROM customers ORDER BY signup_date DESC LIMIT 1"),
]

# ============================================================
# C. Per-city breakdowns (8)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("customers_per_city", "how many customers are in each city?",
          "SELECT city, COUNT(*) AS customer_count FROM customers GROUP BY city ORDER BY customer_count DESC"),
    _case("customer_count_sample_city", f"how many customers are from {_SAMPLE_CITY}?",
          f"SELECT COUNT(*) AS customer_count FROM customers WHERE city = '{_SAMPLE_CITY}'"),
    _case("customers_from_sample_city", f"list the customers from {_SAMPLE_CITY}",
          f"SELECT name, city FROM customers WHERE city = '{_SAMPLE_CITY}'"),
    _case("revenue_per_city", "what is the total revenue by customer city?",
          "SELECT c.city, SUM(o.amount) AS total_revenue FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.city ORDER BY total_revenue DESC"),
    _case("top_city_by_revenue", "which city generates the most revenue?",
          "SELECT c.city, SUM(o.amount) AS total_revenue FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.city ORDER BY total_revenue DESC LIMIT 1"),
    _case("top_city_by_customer_count", "which city has the most customers?",
          "SELECT city, COUNT(*) AS customer_count FROM customers GROUP BY city ORDER BY customer_count DESC LIMIT 1"),
    _case("avg_order_amount_sample_city", f"what is the average order amount for customers in {_SAMPLE_CITY}?",
          f"SELECT AVG(o.amount) AS avg_amount FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.city = '{_SAMPLE_CITY}'"),
    _case("distinct_cities_list", "what cities do customers live in?",
          "SELECT DISTINCT city FROM customers"),
]

# ============================================================
# D. Per-category breakdowns (11)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("orders_per_category", "how many orders were placed in each category?",
          "SELECT category, COUNT(*) AS order_count FROM orders GROUP BY category ORDER BY order_count DESC"),
    _case("revenue_per_category", "what is the total revenue by category?",
          "SELECT category, SUM(amount) AS total_revenue FROM orders GROUP BY category ORDER BY total_revenue DESC"),
    _case("top_category_by_revenue", "which category generates the most revenue?",
          "SELECT category, SUM(amount) AS total_revenue FROM orders GROUP BY category ORDER BY total_revenue DESC LIMIT 1"),
    _case("top_category_by_orders", "which category has the most orders?",
          "SELECT category, COUNT(*) AS order_count FROM orders GROUP BY category ORDER BY order_count DESC LIMIT 1"),
    _case("lowest_category_by_revenue", "which category has the lowest total revenue?",
          "SELECT category, SUM(amount) AS total_revenue FROM orders GROUP BY category ORDER BY total_revenue ASC LIMIT 1"),
    _case("avg_amount_sample_category", f"what is the average order amount in {_SAMPLE_CATEGORY}?",
          f"SELECT AVG(amount) AS avg_amount FROM orders WHERE category = '{_SAMPLE_CATEGORY}'"),
    _case("max_amount_sample_category", f"what is the highest order amount in {_SAMPLE_CATEGORY}?",
          f"SELECT MAX(amount) AS max_amount FROM orders WHERE category = '{_SAMPLE_CATEGORY}'"),
    _case("who_spent_most_sample_category", f"who spent the most on {_SAMPLE_CATEGORY}?",
          f"SELECT c.name, SUM(o.amount) AS total_spent FROM customers c "
          f"JOIN orders o ON c.customer_id = o.customer_id WHERE o.category = '{_SAMPLE_CATEGORY}' "
          f"GROUP BY c.customer_id ORDER BY total_spent DESC LIMIT 1"),
    _case("categories_over_revenue_threshold", "which categories have total revenue over 10000?",
          "SELECT category, SUM(amount) AS total_revenue FROM orders GROUP BY category HAVING SUM(amount) > 10000"),
    _case("distinct_categories_list", "what product categories exist?",
          "SELECT DISTINCT category FROM orders"),
    _case("category_with_most_distinct_items", "which category has the most distinct items?",
          "SELECT category, COUNT(DISTINCT item_name) AS distinct_items FROM orders "
          "GROUP BY category ORDER BY distinct_items DESC LIMIT 1"),
]

# ============================================================
# E. Top-N rankings (10)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("top_5_customers_by_revenue", "who are the top 5 customers by total revenue?",
          "SELECT c.name, SUM(o.amount) AS total_revenue FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "ORDER BY total_revenue DESC LIMIT 5"),
    _case("top_3_customers_by_orders", "who are the top 3 customers by number of orders?",
          "SELECT c.name, COUNT(o.order_id) AS order_count FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "ORDER BY order_count DESC LIMIT 3"),
    _case("best_customer_by_revenue", "who is the customer with the highest total spend?",
          "SELECT c.name, SUM(o.amount) AS total_revenue FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "ORDER BY total_revenue DESC LIMIT 1"),
    _case("customer_with_fewest_orders", "which customer has placed the fewest orders?",
          "SELECT c.name, COUNT(o.order_id) AS order_count FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "ORDER BY order_count ASC LIMIT 1"),
    _case("top_10_orders_by_amount", "what are the 10 largest individual orders?",
          "SELECT order_id, item_name, amount FROM orders ORDER BY amount DESC LIMIT 10"),
    _case("cheapest_5_orders", "what are the 5 smallest individual orders?",
          "SELECT order_id, item_name, amount FROM orders ORDER BY amount ASC LIMIT 5"),
    _case("top_3_items_by_frequency", "what are the 3 most frequently ordered items?",
          "SELECT item_name, COUNT(*) AS times_ordered FROM orders GROUP BY item_name "
          "ORDER BY times_ordered DESC LIMIT 3"),
    _case("newest_5_customers", "who are the 5 most recently signed up customers?",
          "SELECT name, signup_date FROM customers ORDER BY signup_date DESC LIMIT 5"),
    _case("oldest_5_customers", "who are the 5 earliest signed up customers?",
          "SELECT name, signup_date FROM customers ORDER BY signup_date ASC LIMIT 5"),
    _case("most_recent_5_orders", "what are the 5 most recent orders?",
          "SELECT order_id, item_name, order_date FROM orders ORDER BY order_date DESC LIMIT 5"),
]

# ============================================================
# F. Date-range filters (8)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("orders_after_2026_01_01", "how many orders were placed after January 1, 2026?",
          "SELECT COUNT(*) AS order_count FROM orders WHERE order_date > '2026-01-01'"),
    _case("revenue_after_2026_06_01", "what is the total revenue from orders placed after June 1, 2026?",
          "SELECT SUM(amount) AS total_revenue FROM orders WHERE order_date > '2026-06-01'"),
    _case("customers_signed_up_after_2025_06_01", "how many customers signed up after June 1, 2025?",
          "SELECT COUNT(*) AS customer_count FROM customers WHERE signup_date > '2025-06-01'"),
    _case("orders_in_date_range", "how many orders were placed between March 1 and June 1, 2026?",
          "SELECT COUNT(*) AS order_count FROM orders WHERE order_date BETWEEN '2026-03-01' AND '2026-06-01'"),
    _case("avg_amount_orders_after_2026_01_01", "what is the average order amount for orders after January 1, 2026?",
          "SELECT AVG(amount) AS avg_amount FROM orders WHERE order_date > '2026-01-01'"),
    _case("count_customers_signed_up_before_2025_09_01", "how many customers signed up before September 1, 2025?",
          "SELECT COUNT(*) AS customer_count FROM customers WHERE signup_date < '2025-09-01'"),
    _case("most_recent_order_per_customer_sample", f"when did {_SAMPLE_CUSTOMER} place their most recent order?",
          f"SELECT MAX(o.order_date) AS latest_order FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.name = '{_SAMPLE_CUSTOMER}'"),
    _case("orders_count_2026", "how many orders were placed in 2026?",
          "SELECT COUNT(*) AS order_count FROM orders WHERE order_date LIKE '2026%'"),
]

# ============================================================
# G. Customer-specific lookups (8)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("orders_from_sample_customer", f"show me all orders from {_SAMPLE_CUSTOMER}",
          f"SELECT o.order_id, o.item_name, o.amount, o.order_date FROM orders o "
          f"JOIN customers c ON o.customer_id = c.customer_id WHERE c.name = '{_SAMPLE_CUSTOMER}'"),
    _case("total_spent_sample_customer", f"how much has {_SAMPLE_CUSTOMER} spent in total?",
          f"SELECT SUM(o.amount) AS total_spent FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.name = '{_SAMPLE_CUSTOMER}'"),
    _case("order_count_sample_customer", f"how many orders has {_SAMPLE_CUSTOMER} placed?",
          f"SELECT COUNT(*) AS order_count FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.name = '{_SAMPLE_CUSTOMER}'"),
    _case("avg_order_amount_sample_customer", f"what is {_SAMPLE_CUSTOMER}'s average order amount?",
          f"SELECT AVG(o.amount) AS avg_amount FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.name = '{_SAMPLE_CUSTOMER}'"),
    _case("most_expensive_order_sample_customer", f"what is the most expensive order {_SAMPLE_CUSTOMER} placed?",
          f"SELECT o.item_name, o.amount FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.name = '{_SAMPLE_CUSTOMER}' ORDER BY o.amount DESC LIMIT 1"),
    _case("compare_two_customers_spend", f"compare total spend between {_SAMPLE_CUSTOMER} and {_SAMPLE_CUSTOMER_2}",
          f"SELECT c.name, SUM(o.amount) AS total_spent FROM customers c "
          f"JOIN orders o ON c.customer_id = o.customer_id "
          f"WHERE c.name IN ('{_SAMPLE_CUSTOMER}', '{_SAMPLE_CUSTOMER_2}') GROUP BY c.name"),
    _case("categories_purchased_sample_customer", f"what categories has {_SAMPLE_CUSTOMER} purchased from?",
          f"SELECT DISTINCT o.category FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.name = '{_SAMPLE_CUSTOMER}'"),
    _case("did_sample_customer_buy_item", f"has {_SAMPLE_CUSTOMER} ever ordered {_SAMPLE_ITEM}?",
          f"SELECT COUNT(*) AS match_count FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.name = '{_SAMPLE_CUSTOMER}' AND o.item_name = '{_SAMPLE_ITEM}'"),
]

# ============================================================
# H. Threshold / comparison filters (10)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("customers_spent_over_10000", "which customers have spent over 10000 in total?",
          "SELECT c.name, SUM(o.amount) AS total_spent FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "HAVING SUM(o.amount) > 10000"),
    _case("customers_with_more_than_5_orders", "which customers have placed more than 5 orders?",
          "SELECT c.name, COUNT(o.order_id) AS order_count FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "HAVING COUNT(o.order_id) > 5"),
    _case("orders_under_500", "how many orders were under 500?",
          "SELECT COUNT(*) AS order_count FROM orders WHERE amount < 500"),
    _case("customers_with_no_orders", "are there any customers who have never placed an order?",
          "SELECT COUNT(*) AS customers_without_orders FROM customers "
          "WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders)"),
    _case("customers_with_exactly_one_order", "which customers have placed exactly one order?",
          "SELECT c.name, COUNT(o.order_id) AS order_count FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "HAVING COUNT(o.order_id) = 1"),
    _case("percentage_orders_over_1000", "what percentage of orders were over 1000?",
          "SELECT (CAST(SUM(CASE WHEN amount > 1000 THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) * 100 "
          "AS pct_over_1000 FROM orders"),
    _case("customers_below_average_spend", "how many customers spent below the average total spend?",
          "SELECT COUNT(*) AS below_avg_count FROM (SELECT customer_id, SUM(amount) AS total "
          "FROM orders GROUP BY customer_id) sub WHERE sub.total < "
          "(SELECT AVG(total) FROM (SELECT SUM(amount) AS total FROM orders GROUP BY customer_id))"),
    _case("orders_above_avg_amount", "how many orders were above the average order amount?",
          "SELECT COUNT(*) AS above_avg_count FROM orders WHERE amount > (SELECT AVG(amount) FROM orders)"),
    _case("total_revenue_orders_over_3000", "what is the total revenue from orders over 3000?",
          "SELECT SUM(amount) AS total_revenue FROM orders WHERE amount > 3000"),
    _case("categories_with_avg_order_over_1500", "which categories have an average order value over 1500?",
          "SELECT category, AVG(amount) AS avg_amount FROM orders GROUP BY category HAVING AVG(amount) > 1500"),
]

# ============================================================
# I. Multi-condition filters (8)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("sample_city_sample_category_count", f"how many {_SAMPLE_CATEGORY} orders came from customers in {_SAMPLE_CITY}?",
          f"SELECT COUNT(*) AS order_count FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.city = '{_SAMPLE_CITY}' AND o.category = '{_SAMPLE_CATEGORY}'"),
    _case("sample_city_revenue_sample_category", f"what is the total {_SAMPLE_CATEGORY} revenue from {_SAMPLE_CITY} customers?",
          f"SELECT SUM(o.amount) AS total_revenue FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
          f"WHERE c.city = '{_SAMPLE_CITY}' AND o.category = '{_SAMPLE_CATEGORY}'"),
    _case("high_value_sample_category_orders", f"how many {_SAMPLE_CATEGORY} orders were over 2000?",
          f"SELECT COUNT(*) AS order_count FROM orders WHERE category = '{_SAMPLE_CATEGORY}' AND amount > 2000"),
    _case("sample_city_customers_with_multiple_orders", f"which customers in {_SAMPLE_CITY} have placed more than 3 orders?",
          f"SELECT c.name, COUNT(o.order_id) AS order_count FROM customers c "
          f"JOIN orders o ON c.customer_id = o.customer_id WHERE c.city = '{_SAMPLE_CITY}' "
          f"GROUP BY c.customer_id HAVING COUNT(o.order_id) > 3"),
    _case("category_orders_after_date_sample", f"how many {_SAMPLE_CATEGORY} orders were placed after March 1, 2026?",
          f"SELECT COUNT(*) AS order_count FROM orders WHERE category = '{_SAMPLE_CATEGORY}' "
          f"AND order_date > '2026-03-01'"),
    _case("top_customer_in_sample_city", f"who is the top spender among customers in {_SAMPLE_CITY}?",
          f"SELECT c.name, SUM(o.amount) AS total_spent FROM customers c "
          f"JOIN orders o ON c.customer_id = o.customer_id WHERE c.city = '{_SAMPLE_CITY}' "
          f"GROUP BY c.customer_id ORDER BY total_spent DESC LIMIT 1"),
    _case("customers_sample_city_no_sample_category", f"which {_SAMPLE_CITY} customers have never ordered {_SAMPLE_CATEGORY}?",
          f"SELECT DISTINCT c.name FROM customers c WHERE c.city = '{_SAMPLE_CITY}' "
          f"AND c.customer_id NOT IN (SELECT customer_id FROM orders WHERE category = '{_SAMPLE_CATEGORY}')"),
    _case("count_two_categories_combined", f"how many orders were in either {_SAMPLE_CATEGORY} or {_SAMPLE_CATEGORY_2}?",
          f"SELECT COUNT(*) AS order_count FROM orders WHERE category IN "
          f"('{_SAMPLE_CATEGORY}', '{_SAMPLE_CATEGORY_2}')"),
]

# ============================================================
# J. Ordering / extremes phrased differently (6)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("most_expensive_item_overall", "what is the single most expensive order ever placed?",
          "SELECT item_name, amount FROM orders ORDER BY amount DESC LIMIT 1"),
    _case("cheapest_item_overall", "what is the cheapest single order ever placed?",
          "SELECT item_name, amount FROM orders ORDER BY amount ASC LIMIT 1"),
    _case("oldest_order_item", "what item was in the very first order ever placed?",
          "SELECT item_name, order_date FROM orders ORDER BY order_date ASC LIMIT 1"),
    _case("most_recent_order_item", "what item was in the most recent order?",
          "SELECT item_name, order_date FROM orders ORDER BY order_date DESC LIMIT 1"),
    _case("second_highest_order", "what is the second highest order amount?",
          "SELECT amount FROM orders ORDER BY amount DESC LIMIT 1 OFFSET 1"),
    _case("customer_with_widest_category_variety", "which customer has purchased from the most different categories?",
          "SELECT c.name, COUNT(DISTINCT o.category) AS category_variety FROM customers c "
          "JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id "
          "ORDER BY category_variety DESC LIMIT 1"),
]

# ============================================================
# K. Simple listings (6)
# ============================================================
EXECUTION_ACCURACY_CASES += [
    _case("list_all_customer_names", "list all customer names",
          "SELECT name FROM customers"),
    _case("list_all_items", "what items have been ordered at least once?",
          "SELECT DISTINCT item_name FROM orders"),
    _case("list_customers_and_cities", "show me each customer's name and city",
          "SELECT name, city FROM customers"),
    _case("list_orders_sample_category", f"list all orders in the {_SAMPLE_CATEGORY} category",
          f"SELECT order_id, item_name, amount FROM orders WHERE category = '{_SAMPLE_CATEGORY}'"),
    _case("list_customer_signup_dates", "show me every customer's signup date",
          "SELECT name, signup_date FROM customers"),
    _case("list_high_value_items", "list items that were ever sold for more than 4000",
          "SELECT DISTINCT item_name FROM orders WHERE amount > 4000"),
]

if __name__ == "__main__":
    print(f"Total execution-accuracy cases: {len(EXECUTION_ACCURACY_CASES)}")
    ids = [c["id"] for c in EXECUTION_ACCURACY_CASES]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        print(f"WARNING — duplicate case ids: {dupes}")
    else:
        print("No duplicate case ids.")