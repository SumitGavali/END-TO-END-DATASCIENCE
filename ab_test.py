# ab_test.py
import pandas as pd
import joblib
from sklearn.metrics import roc_auc_score

# --- 1. CONFIGURATION ---
CHAMPION_PATH = 'ml_models/champion_model.pkl'
CHALLENGER_PATH = 'ml_models/stockout_xgboost.pkl'
TEST_DATA_PATH = 'gold_data/test_set.parquet'
MINIMUM_IMPROVEMENT = 0.02 

print("Starting A/B Test (Champion vs Challenger)...")

# --- 2. LOAD THE MODELS ---
try:
    champion = joblib.load(CHAMPION_PATH)
    print(" Loaded Champion model.")
except FileNotFoundError:
    print("No Champion found. Promoting the Challenger to be the first Champion...")
    challenger = joblib.load(CHALLENGER_PATH)
    joblib.dump(challenger, CHAMPION_PATH)
    champion = challenger

challenger = joblib.load(CHALLENGER_PATH)
print(" Loaded Challenger model.")

# --- 3. LOAD THE TEST DATA ---
# Because your train_mlflow.py already engineered all the features and 
# encoded the text columns BEFORE saving, we don't need to do anything else!
print("Loading test data...")
df_test = pd.read_parquet(TEST_DATA_PATH)

# The saved file contains 'is_out_of_stock' as the target.
y_test = df_test['is_out_of_stock']

# The saved file contains the exact 6 columns your model was trained on.
# We drop the target column to get our X_test.
X_test = df_test.drop(columns=['is_out_of_stock'])

# --- 4. EVALUATE BOTH MODELS ---
champion_probs = champion.predict_proba(X_test)[:, 1]
challenger_probs = challenger.predict_proba(X_test)[:, 1]

champion_auc = roc_auc_score(y_test, champion_probs)
challenger_auc = roc_auc_score(y_test, challenger_probs)

print(f"\nChampion ROC-AUC:  {champion_auc:.4f}")
print(f" Challenger ROC-AUC: {challenger_auc:.4f}")

# --- 5. THE PROMOTION LOGIC ---
if challenger_auc > (champion_auc + MINIMUM_IMPROVEMENT):
    print("\n CHALLENGER WINS! Promoting to Production...")
    joblib.dump(challenger, CHAMPION_PATH)
    print("New model saved as Champion.")
else:
    print("\n CHAMPION WINS. The challenger did not improve enough.")