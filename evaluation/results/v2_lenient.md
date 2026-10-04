# Execution Accuracy — v2_lenient

- **Run at:** 2026-10-03 18:45
- **Scoring mode:** lenient
- **Cases:** 90 · **Repeats per case:** 1 · **Total runs:** 90
- **Passed:** 81 · **Failed:** 9
- **Time:** 910.3s

## >>> EXECUTION ACCURACY: 90.0% (81/90) <<<

## 9 case(s) with at least one failing run

### [0/1] `newest_5_customers`
- **query:** who are the 5 most recently signed up customers?
- **reason:** mismatch — got [('Nikhil Nair',), ('Naina Joshi',), ('Arjun Kumar',)]..., expected [('Nikhil Nair', '2026-02-04'), ('Naina Joshi', '2026-02-01'), ('Arjun Kumar', '2026-01-18')]...
- **pipeline's SQL:**

```sql
SELECT name FROM customers ORDER BY signup_date DESC LIMIT 5
```

### [0/1] `customers_with_more_than_5_orders`
- **query:** which customers have placed more than 5 orders?
- **reason:** mismatch — got [(1, 'Krishna Sharma', 'krishna.sharma1@example.com', 9362950628, 'Lucknow', '2025-09-18'), (2, 'Kavya Kumar', 'kavya.kumar2@example.com', 9826600539, 'Lucknow', '2025-12-15'), (3, 'Dev Gupta', 'dev.gupta3@example.com', 9134126396, 'Ahmedabad', '2025-07-04')]..., expected [('Krishna Sharma', 9), ('Kavya Kumar', 12), ('Dev Gupta', 14)]...
- **pipeline's SQL:**

```sql
SELECT c.customer_id, c.name, c.email, c.phone, c.city, c.signup_date FROM customers AS c WHERE c.customer_id IN (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5) LIMIT 100
```

### [0/1] `customers_with_no_orders`
- **query:** are there any customers who have never placed an order?
- **reason:** mismatch — got []..., expected [(0,)]...
- **pipeline's SQL:**

```sql
SELECT * FROM customers AS c WHERE NOT EXISTS(SELECT 1 FROM orders AS o WHERE o.customer_id = c.customer_id) LIMIT 100
```

### [0/1] `customers_below_average_spend`
- **query:** how many customers spent below the average total spend?
- **reason:** expected a result, got type='error': That query didn't pass safety checks: Unknown table(s) referenced: {'avg_total', 'customer_totals'}

### [0/1] `sample_city_customers_with_multiple_orders`
- **query:** which customers in Lucknow have placed more than 3 orders?
- **reason:** mismatch — got [('Krishna Sharma', 'krishna.sharma1@example.com', 9362950628, 'Lucknow'), ('Kavya Kumar', 'kavya.kumar2@example.com', 9826600539, 'Lucknow'), ('Sai Gupta', 'sai.gupta38@example.com', 9976198296, 'Lucknow')]..., expected [('Krishna Sharma', 9), ('Kavya Kumar', 12), ('Sai Gupta', 14)]...
- **pipeline's SQL:**

```sql
SELECT c.name, c.email, c.phone, c.city FROM customers AS c JOIN orders AS o ON c.customer_id = o.customer_id WHERE c.city = 'Lucknow' GROUP BY c.customer_id HAVING COUNT(o.order_id) > 3 LIMIT 100
```

### [0/1] `oldest_order_item`
- **query:** what item was in the very first order ever placed?
- **reason:** mismatch — got [('Perfume',)]..., expected [('Perfume', '2025-08-24')]...
- **pipeline's SQL:**

```sql
SELECT item_name FROM orders ORDER BY order_date ASC LIMIT 1
```

### [0/1] `most_recent_order_item`
- **query:** what item was in the most recent order?
- **reason:** mismatch — got [('Kids Story Set',)]..., expected [('Kids Story Set', '2026-08-23')]...
- **pipeline's SQL:**

```sql
SELECT item_name FROM orders ORDER BY order_date DESC LIMIT 1
```

### [0/1] `list_orders_sample_category`
- **query:** list all orders in the Books category
- **reason:** mismatch — got [(1, 1, 'Kids Story Set', 'Books', 1, 1056.43, 'Credit Card', '2026-05-01'), (8, 1, 'Cookbook', 'Books', 3, 555.98, 'Net Banking', '2026-03-07'), (9, 1, 'Fiction Novel', 'Books', 2, 573.89, 'UPI', '2025-12-07')]..., expected [(1, 'Kids Story Set', 1056.43), (8, 'Cookbook', 555.98), (9, 'Fiction Novel', 573.89)]...
- **pipeline's SQL:**

```sql
SELECT * FROM orders WHERE category = 'Books' LIMIT 100
```

### [0/1] `list_high_value_items`
- **query:** list items that were ever sold for more than 4000
- **reason:** mismatch — got [('Sports Sneakers',), ('Sports Sneakers',), ('Smartwatch',)]..., expected [('Sports Sneakers',), ('Smartwatch',), ('Running Shoes',)]...
- **pipeline's SQL:**

```sql
SELECT item_name FROM orders WHERE amount > 4000 LIMIT 100
```
