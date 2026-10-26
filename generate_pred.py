# generate_predictions.py
import pandas as pd
import numpy as np
import joblib

print("Loading data and models...")

# Load the data
df_variants = pd.read_parquet('gold_data/fct_variants.parquet')
df_products = pd.read_parquet('gold_data/dim_products.parquet')
df = df_variants.merge(df_products, on='product_id', suffixes=('_var', '_prod'))

# Load the model and encoders
model = joblib.load('ml_models/stockout_xgboost.pkl')
le_dict = joblib.load('ml_models/label_encoders.pkl')

print("Engineering features...")
# Replicate the notebook feature engineering
df['created_at'] = pd.to_datetime(df['created_at'], utc=True).dt.tz_localize(None)
df['product_age_days'] = (pd.Timestamp.now() - df['created_at']).dt.days
df['compare_at_price'] = pd.to_numeric(df['compare_at_price'], errors='coerce').fillna(0)
df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
df['Discount%'] = np.where(df['compare_at_price'] > df['price'], 
                           (df['compare_at_price'] - df['price']) / df['compare_at_price'], 0)

def assign_gender(title):
    title = str(title).lower()
    if 'bra' in title or 'legging' in title or 'crop' in title or 'women' in title: return 'Women'
    if 'men' in title: return 'Men'
    return 'Unisex'
df['Gender'] = df['product_title'].apply(assign_gender)

pt_cols = [col for col in df.columns if col.startswith('product_type')]
df['Product_Type'] = df[pt_cols[0]].fillna('Unknown') if pt_cols else 'Unknown'

# Recreate the 3 missing features you found in the API error
df['release_year'] = df['created_at'].dt.year.fillna(2026)
df['release_month'] = df['created_at'].dt.month.fillna(1)
df['is_holiday_release'] = np.where(df['release_month'].isin([11, 12]), 1, 0)

# Encode text columns
features = ['price', 'Discount%', 'product_age_days', 'Product_Type', 'Gender', 'variant_title', 
            'release_year', 'release_month', 'is_holiday_release']
X = df[features].copy()

for col in ['Product_Type', 'Gender', 'variant_title']:
    classes = set(le_dict[col].classes_)
    X[col] = X[col].astype(str).apply(lambda x: le_dict[col].transform([x])[0] if x in classes else -1)

print("Filtering for IN-STOCK items only...")
# A model shouldn't predict stockouts for items that are ALREADY out of stock!
in_stock_df = df[df['is_available'] == True].copy()

# Make sure we only pass the features for these in-stock items
X_in_stock = in_stock_df[features].copy()

# Re-apply the encoding (since we created a new dataframe)
for col in ['Product_Type', 'Gender', 'variant_title']:
    classes = set(le_dict[col].classes_)
    X_in_stock[col] = X_in_stock[col].astype(str).apply(lambda x: le_dict[col].transform([x])[0] if x in classes else -1)

# Generate predictions ONLY for in-stock items
in_stock_df['Predicted_Stockout_Risk'] = model.predict(X_in_stock)
in_stock_df['Risk_Probability'] = model.predict_proba(X_in_stock)[:, 1]

# Save to CSV
output_cols = ['product_id', 'variant_id', 'product_title', 'variant_title', 'Product_Type', 
               'Gender', 'price', 'Discount%', 'Predicted_Stockout_Risk', 'Risk_Probability']
in_stock_df[output_cols].to_csv('gold_data/ml_predictions.csv', index=False)

print(f"✅ Saved {len(in_stock_df)} in-stock predictions to gold_data/ml_predictions.csv!")