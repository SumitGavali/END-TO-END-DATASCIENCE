import duckdb
import os

print("Starting DuckDB transformation...")

DB_FILE = "gymshark.duckdb"
con = duckdb.connect(DB_FILE)

con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

# 🔑 Critical fix: create secret explicitly
con.execute("""
    CREATE OR REPLACE SECRET gymshark_s3 (
        TYPE s3,
    # Credentials are loaded automatically by boto3 from the ~/.aws/credentials file
        REGION 'ap-southeast-2'
    );
""")

S3_PATH = "s3://gymshark-data-lake-sumit-07/raw/shopify/dt=2026-10-18/*.json"

print(f"Reading raw JSON from: {S3_PATH}")

con.execute(f"""
    CREATE OR REPLACE TABLE raw_products AS 
    SELECT * FROM read_json_auto('{S3_PATH}');
""")

count = con.execute("SELECT COUNT(*) FROM raw_products").fetchone()[0]
print(f"Successfully loaded {count} raw products.")

# 5. TRANSFORM: FLATTEN THE VARIANTS (Silver Layer)
con.execute("""
    CREATE OR REPLACE TABLE stg_variants AS
    SELECT 
        raw_products.id AS product_id,
        raw_products.title AS product_title,
        raw_products.product_type,
        v.id AS variant_id,
        v.title AS variant_title,
        v.sku AS sku,
        CAST(v.price AS FLOAT) AS price,
        CAST(v.compare_at_price AS FLOAT) AS compare_at_price,
        v.available AS is_available
    FROM raw_products,
    UNNEST(variants) AS v;
""")

# Check how many variants we have now.
variant_count = con.execute("SELECT COUNT(*) FROM stg_variants").fetchone()[0]
print(f"Successfully flattened into {variant_count} individual variants.")

# 6. SAVE AS PARQUET (Gold Layer)
import os
os.makedirs("gold_data", exist_ok=True)

# Save Products
con.execute("""
    COPY (
        SELECT id AS product_id, title, vendor, product_type, created_at 
        FROM raw_products
    ) TO 'gold_data/dim_products.parquet' (FORMAT PARQUET);
""")

# Save Variants
con.execute("""
    COPY stg_variants TO 'gold_data/fct_variants.parquet' (FORMAT PARQUET);
""")

print("✅ Transformation complete! Data saved to 'gold_data/' folder.")
con.close()