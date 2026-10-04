# Execution Accuracy — v1_strict

- **Run at:** 2026-10-03 19:20
- **Scoring mode:** strict
- **Cases:** 90 · **Repeats per case:** 1 · **Total runs:** 90
- **Passed:** 69 · **Failed:** 21
- **Time:** 886.7s

## >>> EXECUTION ACCURACY: 76.7% (69/90) <<<

## 21 case(s) with at least one failing run

### [0/1] `customers_from_sample_city`
- **query:** list the customers from Lucknow
- **reason:** mismatch — got [(1, 'Krishna Sharma', 'krishna.sharma1@example.com', 9362950628, 'Lucknow', '2025-09-18'), (2, 'Kavya Kumar', 'kavya.kumar2@example.com', 9826600539, 'Lucknow', '2025-12-15'), (21, 'Aadhya Pillai', 'aadhya.pillai21@example.com', 9328306011, 'Lucknow', '2025-08-28')]..., expected [('Krishna Sharma', 'Lucknow'), ('Kavya Kumar', 'Lucknow'), ('Aadhya Pillai', 'Lucknow')]...
- **pipeline's SQL:**

```sql
SELECT * FROM customers WHERE city = 'Lucknow' LIMIT 100
```

### [0/1] `top_3_customers_by_orders`
- **query:** who are the top 3 customers by number of orders?
- **reason:** mismatch — got [(77, 'Ishaan Nair', 15), (72, 'Aarav Rao', 15), (64, 'Aryan Das', 15)]..., expected [('Ishaan Nair', 15), ('Aarav Rao', 15), ('Aryan Das', 15)]...
- **pipeline's SQL:**

```sql
SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_count FROM customers AS c JOIN orders AS o ON c.customer_id = o.customer_id GROUP BY c.customer_id ORDER BY order_count DESC LIMIT 3
```

### [0/1] `best_customer_by_revenue`
- **query:** who is the customer with the highest total spend?
- **reason:** mismatch — got [('Sai Gupta', 'sai.gupta38@example.com', 9976198296, 'Lucknow', 35705.38)]..., expected [('Sai Gupta', 35705.38)]...
- **pipeline's SQL:**

```sql
SELECT c.name, c.email, c.phone, c.city, SUM(o.amount) AS total_spend FROM customers AS c JOIN orders AS o ON c.customer_id = o.customer_id GROUP BY c.customer_id ORDER BY total_spend DESC LIMIT 1
```

### [0/1] `top_10_orders_by_amount`
- **query:** what are the 10 largest individual orders?
- **reason:** expected a result, got type='clarify': 

### [0/1] `top_3_items_by_frequency`
- **query:** what are the 3 most frequently ordered items?
- **reason:** expected a result, got type='clarify': 

### [0/1] `newest_5_customers`
- **query:** who are the 5 most recently signed up customers?
- **reason:** mismatch — got [('Nikhil Nair',), ('Naina Joshi',), ('Arjun Kumar',)]..., expected [('Nikhil Nair', '2026-02-04'), ('Naina Joshi', '2026-02-01'), ('Arjun Kumar', '2026-01-18')]...
- **pipeline's SQL:**

```sql
SELECT name FROM customers ORDER BY signup_date DESC LIMIT 5
```

### [0/1] `most_recent_5_orders`
- **query:** what are the 5 most recent orders?
- **reason:** mismatch — got [(528, 59, 'Kids Story Set', 'Books', 3, 1029.62, 'Credit Card', '2026-08-23'), (745, 86, 'Grocery Basket - Weekly', 'Grocery', 3, 1411.56, 'Debit Card', '2026-08-23'), (377, 41, 'Scented Candle Set', 'Home Decor', 1, 688.56, 'UPI', '2026-08-21')]..., expected [(528, 'Kids Story Set', '2026-08-23'), (745, 'Grocery Basket - Weekly', '2026-08-23'), (377, 'Scented Candle Set', '2026-08-21')]...
- **pipeline's SQL:**

```sql
SELECT order_id, customer_id, item_name, category, quantity, amount, payment_method, order_date FROM orders ORDER BY order_date DESC LIMIT 5
```

### [0/1] `orders_from_sample_customer`
- **query:** show me all orders from Krishna Sharma
- **reason:** mismatch — got [(1, 1, 'Kids Story Set', 'Books', 1, 1056.43, 'Credit Card', '2026-05-01'), (2, 1, 'Sports Sneakers', 'Footwear', 1, 3648.92, 'UPI', '2026-04-03'), (3, 1, 'Hair Care Combo', 'Beauty', 3, 1179.52, 'Credit Card', '2026-03-07')]..., expected [(1, 'Kids Story Set', 1056.43, '2026-05-01'), (2, 'Sports Sneakers', 3648.92, '2026-04-03'), (3, 'Hair Care Combo', 1179.52, '2026-03-07')]...
- **pipeline's SQL:**

```sql
SELECT o.* FROM orders AS o JOIN customers AS c ON o.customer_id = c.customer_id WHERE c.name = 'Krishna Sharma' LIMIT 100
```

### [0/1] `avg_order_amount_sample_customer`
- **query:** what is Krishna Sharma's average order amount?
- **reason:** mismatch — got [('Krishna Sharma', 1280.0677777777778)]..., expected [(1280.0677777777778,)]...
- **pipeline's SQL:**

```sql
SELECT c.name, AVG(o.amount) AS avg_order_amount FROM customers AS c JOIN orders AS o ON c.customer_id = o.customer_id WHERE c.name = 'Krishna Sharma' GROUP BY c.customer_id LIMIT 100
```

### [0/1] `most_expensive_order_sample_customer`
- **query:** what is the most expensive order Krishna Sharma placed?
- **reason:** mismatch — got [(2, 1, 'Sports Sneakers', 'Footwear', 1, 3648.92, 'UPI', '2026-04-03')]..., expected [('Sports Sneakers', 3648.92)]...
- **pipeline's SQL:**

```sql
SELECT o.order_id, o.customer_id, o.item_name, o.category, o.quantity, o.amount, o.payment_method, o.order_date FROM customers AS c JOIN orders AS o ON c.customer_id = o.customer_id WHERE c.name = 'Krishna Sharma' ORDER BY o.amount DESC LIMIT 1
```

### [0/1] `customers_spent_over_10000`
- **query:** which customers have spent over 10000 in total?
- **reason:** mismatch — got [(1, 'Krishna Sharma', 'krishna.sharma1@example.com', 'Lucknow', 11520.61), (2, 'Kavya Kumar', 'kavya.kumar2@example.com', 'Lucknow', 20140.09), (3, 'Dev Gupta', 'dev.gupta3@example.com', 'Ahmedabad', 27633.57)]..., expected [('Krishna Sharma', 11520.61), ('Kavya Kumar', 20140.09), ('Dev Gupta', 27633.57)]...
- **pipeline's SQL:**

```sql
SELECT c.customer_id, c.name, c.email, c.city, SUM(o.amount) AS total_spent FROM customers AS c JOIN orders AS o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name, c.email, c.city HAVING total_spent > 10000 LIMIT 100
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

### [0/1] `sample_city_customers_with_multiple_orders`
- **query:** which customers in Lucknow have placed more than 3 orders?
- **reason:** mismatch — got [(1, 'Krishna Sharma', 'krishna.sharma1@example.com', 9362950628, 'Lucknow'), (2, 'Kavya Kumar', 'kavya.kumar2@example.com', 9826600539, 'Lucknow'), (38, 'Sai Gupta', 'sai.gupta38@example.com', 9976198296, 'Lucknow')]..., expected [('Krishna Sharma', 9), ('Kavya Kumar', 12), ('Sai Gupta', 14)]...
- **pipeline's SQL:**

```sql
SELECT c.customer_id, c.name, c.email, c.phone, c.city FROM customers AS c JOIN orders AS o ON c.customer_id = o.customer_id WHERE c.city = 'Lucknow' GROUP BY c.customer_id HAVING COUNT(o.order_id) > 3 LIMIT 100
```

### [0/1] `customers_sample_city_no_sample_category`
- **query:** which Lucknow customers have never ordered Books?
- **reason:** mismatch — got [('Aadhya Pillai', 'aadhya.pillai21@example.com', 9328306011, 'Lucknow'), ('Dev Nair', 'dev.nair24@example.com', 9560027313, 'Lucknow'), ('Vivaan Patel', 'vivaan.patel88@example.com', 9940081098, 'Lucknow')]..., expected [('Aadhya Pillai',), ('Dev Nair',), ('Vivaan Patel',)]...
- **pipeline's SQL:**

```sql
SELECT c.name, c.email, c.phone, c.city FROM customers AS c WHERE c.city = 'Lucknow' AND NOT EXISTS(SELECT 1 FROM orders AS o WHERE o.customer_id = c.customer_id AND o.category = 'Books') LIMIT 100
```

### [0/1] `most_expensive_item_overall`
- **query:** what is the single most expensive order ever placed?
- **reason:** mismatch — got [(128, 15, 'Smartwatch', 'Electronics', 1, 7977.6, 'Debit Card', '2026-07-05')]..., expected [('Smartwatch', 7977.6)]...
- **pipeline's SQL:**

```sql
SELECT * FROM orders ORDER BY amount DESC LIMIT 1
```

### [0/1] `cheapest_item_overall`
- **query:** what is the cheapest single order ever placed?
- **reason:** mismatch — got [(72, 9, 'Coffee & Snack', 'Food Court', 2, 158.16, 'UPI', '2025-08-27')]..., expected [('Coffee & Snack', 158.16)]...
- **pipeline's SQL:**

```sql
SELECT * FROM orders ORDER BY amount ASC LIMIT 1
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

### [0/1] `list_customer_signup_dates`
- **query:** show me every customer's signup date
- **reason:** mismatch — got [(1, 'Krishna Sharma', '2025-09-18'), (2, 'Kavya Kumar', '2025-12-15'), (3, 'Dev Gupta', '2025-07-04')]..., expected [('Krishna Sharma', '2025-09-18'), ('Kavya Kumar', '2025-12-15'), ('Dev Gupta', '2025-07-04')]...
- **pipeline's SQL:**

```sql
SELECT customer_id, name, signup_date FROM customers LIMIT 100
```
