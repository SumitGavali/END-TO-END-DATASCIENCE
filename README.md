# Gymshark End-End Data Project
## [data engineering + data analysis + data scientist + MLOPS ]

This repository contains a complete, end-to-end data ecosystem built to analyze the Gymshark product catalog and predict inventory STOCK-OUTS

Instead of just building a dashboard, I wanted to simulate what a modern data team actually does: scrape raw data, build a scalable data warehouse, visualize business insights, train a machine learning model, and deploy it using MLOps best practices (A/B testing and API serving).

##  Architecture & Tech Stack
*   **Data Ingestion:** Python, Requests, AWS S3
*   **Data Warehouse & Transformation:** DuckDB, SQL, Parquet
*   **Business Intelligence:** Power BI, DAX
*   **Machine Learning:** Scikit-Learn, XGBoost, Pandas
*   **MLOps:** MLflow, FastAPI, Joblib


##  Step-by-Step Implementation

### Phase 1: Data Engineering (The "Bronze" & "Silver" Layers)
**Why:** I needed a reliable source of truth. Scraping HTML is messy, so I tapped into Shopify's public JSON endpoint (`/products.json`).

1.  **Ingestion (`ingest.py`):** I wrote a Python script to paginate through all ~9,900 Gymshark products and upload the raw JSON files into an **AWS S3 bucket**. I used Hive-style date partitioning (`raw/shopify/dt=YYYY-MM-DD/`) so that if I run this daily, I build a historical snapshot of the catalog without ever overwriting yesterday's data.
2.  **Transformation (`transform.py`):** Raw JSON is nested and hard to query. I used **DuckDB** (an in-process OLAP database) to read the JSON directly from S3. I used SQL `UNNEST` to explode the nested `variants` array into a flat table. 
3.  **The "Gold" Layer:** I saved the cleaned data as **Parquet files** (highly compressed, columnar format) which serve as the single source of truth for both Power BI and the ML models.

### Phase 2: Data Analytics (Power BI)
**Why:** Business stakeholders need to understand the health of the catalog. I built a 4-page interactive dashboard.
*   **Page 1 (Executive Summary):** KPI cards, Gender Split, and Top Product Types.
*   <img width="1450" height="810" alt="image" src="https://github.com/user-attachments/assets/4f0a39e6-1bb3-4f5f-a205-9d16439a2f72" />

*   **Page 2 & 3 (Pricing & Discounts):** Scatter plots and bar charts identifying which categories are being heavily discounted (e.g., Dresses at 70%).
*   <img width="1447" height="810" alt="image" src="https://github.com/user-attachments/assets/dfc46012-7dbd-4485-8bc9-7028704932e6" />
    <img width="1458" height="816" alt="image" src="https://github.com/user-attachments/assets/c44e5387-f5a6-4a69-92c8-1af7b5e8209e" />
    
*   **Page 4 (AI Predictions):** Visualizing the output of the Machine Learning model.
*   <img width="1460" height="813" alt="image" src="https://github.com/user-attachments/assets/ec1c134c-5e1b-4227-94e4-5aeb40057c9b" />


### Phase 3: Data Science (The ML Model)
**Why:** A dashboard tells you what happened yesterday. A machine learning model tells you what will happen tomorrow.
*   **The Problem:** Can we predict if a product is likely to go out of stock?
*   **Feature Engineering:** Created features like `product_age_days`, `Discount%`, and parsed `Gender` from the product titles.
*   **Handling Text:** Used `LabelEncoder` to convert text (e.g., "Men", "Large") into numbers XGBoost can understand.
*   **The Model:** Trained an **XGBoost Classifier**. 
*   **The Results:** Achieved **92.17% Accuracy** and **96% Recall** on the out-of-stock class. Recall was prioritized because missing a stockout costs the business money, while a false alarm just means holding a little extra safety stock.

### Phase 4: MLOps (The Production Layer)
**Why:** A model in a Jupyter Notebook is useless to a software engineer. It needs to be tracked, tested, and served.

1.  **Experiment Tracking (`train_mlflow.py`):** Used **MLflow** to track hyperparameters (n_estimators, max_depth) and metrics. This ensures that if I train 10 different models, I know exactly which one performed best and why.
2.  **A/B Testing (`ab_test.py`):** Built a Champion/Challenger evaluation script. When a new model is trained, it acts as the "Challenger." It is only promoted to the "Champion" (Production) slot if it beats the existing model's ROC-AUC score by at least 2%. This prevents bad models from breaking the website.
3.  **Model Serving (`api.py`):** Built a **FastAPI** endpoint. Software engineers can send a POST request with product details (price, size, category), and the API will return a real-time stockout risk probability.
4.  **Predictive Scoring (`generate_predictions.py`):** I used the final Champion model to score the *entire* live inventory (filtering out items that are already out of stock) and exported the results to a CSV, which connects directly into Power BI Page 5.
![alt text](mlfow1.PNG)

##  Key Business Insights Discovered
1.  **Unisex Dominance:** 78% of the catalog is classified as "Unisex," heavily skewing towards T-Shirts and Shorts.
2.  **Discount Strategy:** The brand is applying massive discounts (up to 70%) on low-ticket items like Dresses and Accessories, likely to clear old inventory.
3.  **Predictive Risk:** The ML model successfully identified 2,782 specific SKUs (24% of live inventory) at high risk of selling out. The highest risk categories are T-Shirts and Leggings.

