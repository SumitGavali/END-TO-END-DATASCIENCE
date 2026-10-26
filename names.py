import duckdb
import pandas as pd

# 1. Connect to DuckDB and read the Gold Layer Parquet file
con = duckdb.connect()
df = con.execute("SELECT product_title FROM 'gold_data/fct_variants.parquet'").df()

# 2. Gymshark titles look like "Gymshark Apollo T-Shirt - Smokey Grey".
# Let's split by the hyphen and keep ONLY the first part (the product name).
# We use .str.split(' - ').str[0] to remove the colors.
df['base_name'] = df['product_title'].str.split(' - ').str[0]

# 3. Now let's find all the UNIQUE base names and count how many variants each has.
unique_products = df['base_name'].value_counts().reset_index()
unique_products.columns = ['Product_Name', 'Variant_Count']

# 4. Print the top 100 unique products. 
# (9,995 products -> maybe 500 unique base names)
print(f"Found {len(unique_products)} unique product names.")
print("\n--- Top 100 Unique Products ---")
print(unique_products.head(100).to_string(index=False))

# 5. Save the full list to a CSV file so you can open it in Excel and read it!
unique_products.to_csv("unique_products.csv", index=False)
print("\n✅ Saved full list to 'unique_products.csv'")