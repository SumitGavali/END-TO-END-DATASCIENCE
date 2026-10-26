from fastapi import FastAPI
from pydantic import BaseModel #means that we are importing the BaseModel class from the pydantic library, which is used for data validation and settings management in FastAPI applications.
import joblib 
import pandas as pd

app=FastAPI(title="Gymshark stockout api")
model=joblib.load("ml_models/stockout_xgboost.pkl")
le_dict = joblib.load('ml_models/label_encoders.pkl')

#defining what data the api expects to receive

class ProductInput(BaseModel):
    price: float
    discount_percent: float
    product_age_days: int
    product_type: str
    gender: str
    size: str

@app.post("/predict")
def predict_stockout(data: ProductInput):
    # --- 1. Handle unknown categories safely ---
    def safe_encode(encoder, value):
        try:
            return encoder.transform([value])[0]
        except ValueError:
            return -1 # Return -1 if the model hasn't seen this category

    p_type = safe_encode(le_dict['Product_Type'], data.product_type)
    gender = safe_encode(le_dict['Gender'], data.gender)
    size = safe_encode(le_dict['variant_title'], data.size)

    # --- 2. Feature Engineering for the API ---
    # We need to simulate the missing 3 features. Since the API doesn't have 
    # a real release date, we'll set it to 'today' for a brand new product.
    # (In a real app, the user would send the release date in the JSON).
    release_year = 2026
    release_month = 10
    is_holiday_release = 0 # 0 = False

    # --- 3. Build the input DataFrame (All 9 features!) ---
    input_df = pd.DataFrame([{
        'price': data.price,
        'Discount%': data.discount_percent,
        'product_age_days': data.product_age_days,
        'Product_Type': p_type,
        'Gender': gender,
        'variant_title': size,
        'release_year': release_year,             # NEW
        'release_month': release_month,           # NEW
        'is_holiday_release': is_holiday_release  # NEW
    }])

    # --- 4. Predict ---
    prediction = model.predict(input_df)[0]
    probability = model.predict_proba(input_df)[0][1]

    return {
        "out_of_stock_risk": "HIGH" if prediction == 1 else "LOW",
        "risk_probability": round(float(probability), 2)
    }
