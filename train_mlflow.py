# train_mlflow.py
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

# 1. Setup MLflow (It will create a local database called mlflow.db)
mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("Gymshark_Stockout_Prediction")

print("Loading and Engineering Data...")
df_variants = pd.read_parquet('gold_data/fct_variants.parquet')
df_products = pd.read_parquet('gold_data/dim_products.parquet')
df = df_variants.merge(df_products, on='product_id', suffixes=('_var', '_prod'))

# Feature Engineering (Same as notebook)
df['is_out_of_stock'] = np.where(df['is_available'] == False, 1, 0)
df['created_at'] = pd.to_datetime(df['created_at'], utc=True).dt.tz_localize(None)
df['product_age_days'] = (pd.Timestamp.now() - df['created_at']).dt.days
df['compare_at_price'] = pd.to_numeric(df['compare_at_price'], errors='coerce').fillna(0)
df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
df['Discount%'] = np.where(df['compare_at_price'] > df['price'], 
                           (df['compare_at_price'] - df['price']) / df['compare_at_price'], 0)

def assign_gender(title):
    title=str(title).lower()

    if 'bra' in title or 'legging' in title or 'crop' in title or 'skort' in title or 'dress' in title or 'bikini' in title or 'cami' in title or 'bandeau' in title : return 'Women'
    if 'men' in title or 'stinger' in title or 'boxer' in title: return 'Men'
    return 'Unisex'



df['Gender'] = df['product_title'].apply(assign_gender)
pt_cols = [col for col in df.columns if col.startswith('product_type')]
df['Product_Type'] = df[pt_cols[0]].fillna('Unknown') if pt_cols else 'Unknown'

#  FIX: Add the time features to match the model!
df['release_year'] = df['created_at'].dt.year.fillna(2026)
df['release_month'] = df['created_at'].dt.month.fillna(1)
df['is_holiday_release'] = np.where(df['release_month'].isin([11, 12]), 1, 0)

# 2. Features and Target (Now with all 9 features!)
features = ['price', 'Discount%', 'product_age_days', 'Product_Type', 'Gender', 'variant_title', 
            'release_year', 'release_month', 'is_holiday_release']
X = df[features].copy()
y = df['is_out_of_stock']

# 3. Encode text
le_dict = {}
for col in ['Product_Type', 'Gender', 'variant_title']:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    le_dict[col] = le

# 4. Split Data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# --- THIS IS THE NEW MLOPS PART ---
# Save the test set so our A/B testing script can use it later!
test_df = X_test.copy()
test_df['is_out_of_stock'] = y_test
test_df.to_parquet('gold_data/test_set.parquet')
print(" Saved Test Set to gold_data/test_set.parquet")

# 5. Train Model with MLflow Tracking
print("Training Model with MLflow...")
with mlflow.start_run(run_name="XGBoost_Production_v1"):
    params = {
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.1,
        "objective": "binary:logistic"
    }
    
    model = XGBClassifier(**params, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    # Log to MLflow Dashboard
    mlflow.log_params(params)
    mlflow.log_metric("accuracy", accuracy)
    
    # Save the model into the MLflow Registry
    import mlflow.xgboost
    mlflow.xgboost.log_model(model, "model")
    
    print(f" Model Trained! Accuracy: {accuracy * 100:.2f}%")
    print("Run 'mlflow ui' to view the dashboard.")