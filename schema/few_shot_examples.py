"""
Few-shot NL -> SQL examples. This is the corpus the RAG layer retrieves
from — instead of stuffing ALL examples into every prompt, we embed
each example and pull only the top-k most relevant ones per query.

Add more examples here as you find failure cases — this list IS your
retrieval-augmented "training data" for the generator.
"""

FEW_SHOT_EXAMPLES = [
    {
        "question": "who is the best customer by revenue?",
        "sql": "SELECT c.name, SUM(o.amount) AS total_revenue FROM customers c "
               "JOIN orders o ON c.customer_id = o.customer_id "
               "GROUP BY c.customer_id ORDER BY total_revenue DESC LIMIT 100",
    },
    {
        "question": "which customer placed the most orders?",
        "sql": "SELECT c.name, COUNT(o.order_id) AS order_count FROM customers c "
               "JOIN orders o ON c.customer_id = o.customer_id "
               "GROUP BY c.customer_id ORDER BY order_count DESC LIMIT 100",
    },
    {
        "question": "show me all orders from a specific customer",
        "sql": "SELECT o.order_id, o.amount, o.order_date FROM orders o "
               "JOIN customers c ON o.customer_id = c.customer_id "
               "WHERE c.name LIKE '%{customer_name}%' LIMIT 100",
    },
    {
        "question": "list customers from a specific city",
        "sql": "SELECT name, city FROM customers WHERE city = '{city}' LIMIT 100",
    },
    {
        "question": "what is the total revenue this month?",
        "sql": "SELECT SUM(amount) AS total_revenue FROM orders "
               "WHERE order_date >= date('now', 'start of month') LIMIT 100",
    },
    {
        "question": "who signed up most recently?",
        "sql": "SELECT name, signup_date FROM customers ORDER BY signup_date DESC LIMIT 10",
    },
    {
        "question": "average order amount per customer",
        "sql": "SELECT c.name, AVG(o.amount) AS avg_order_amount FROM customers c "
               "JOIN orders o ON c.customer_id = o.customer_id "
               "GROUP BY c.customer_id LIMIT 100",
    },
    {
        "question": "how many customers are there in total?",
        "sql": "SELECT COUNT(*) AS customer_count FROM customers LIMIT 100",
    },
    {
        "question": "how many orders have been placed in total?",
        "sql": "SELECT COUNT(*) AS order_count FROM orders LIMIT 100",
    },
]