# analysis.py
import duckdb
import pandas as pd

# 1. Connect to DuckDB (in-memory is fine here)
con = duckdb.connect()

# 2. Load the Parquet files we just created
# DuckDB can query Parquet files directly and instantly!
con.execute("CREATE VIEW variants AS SELECT * FROM 'gold_data/fct_variants.parquet';")
con.execute("CREATE VIEW products AS SELECT * FROM 'gold_data/dim_products.parquet';")

# 3. Let's ask our first business questions!

print("--- 1. Top 5 Most Expensive Variants ---")
q1 = """
    SELECT product_title, variant_title, price 
    FROM variants 
    ORDER BY price DESC 
    LIMIT 5;
"""
print(con.execute(q1).df().to_string(index=False))
print("\n")

print("--- 2. Average Price by Product Type ---")
q2 = """
    SELECT product_type, ROUND(AVG(price), 2) as avg_price, COUNT(*) as variant_count
    FROM variants
    GROUP BY product_type
    ORDER BY avg_price DESC
    LIMIT 5;
"""
print(con.execute(q2).df().to_string(index=False))
print("\n")

print("--- 3. How many variants are out of stock? ---")
q3 = """
    SELECT 
        is_available, 
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM variants), 2) as percentage
    FROM variants
    GROUP BY is_available;
"""
print(con.execute(q3).df().to_string(index=False))
print("\n")

print("--- 4. Top 5 Most Discounted Items (Where compare_at_price is higher than price) ---")
q4 = """
    SELECT 
        product_title, 
        variant_title, 
        price, 
        compare_at_price,
        ROUND((compare_at_price - price) / compare_at_price * 100, 2) as discount_percentage
    FROM variants
    WHERE compare_at_price > price
    ORDER BY discount_percentage DESC
    LIMIT 5;
"""
print(con.execute(q4).df().to_string(index=False))