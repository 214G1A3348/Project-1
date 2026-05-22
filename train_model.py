"""
train_model.py — trains a RandomForest risk classifier on a realistic synthetic dataset.
Run once:  python train_model.py
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import joblib

RANDOM_STATE = 42
N_SAMPLES = 5000
MODEL_DIR = os.path.join(os.path.dirname(__file__), "trained_model")
os.makedirs(MODEL_DIR, exist_ok=True)

np.random.seed(RANDOM_STATE)


def generate_dataset(n: int) -> pd.DataFrame:
    """
    Simulate realistic return-fraud data using the exact 5 requested features.
    """
    # Base features
    total_orders_count  = np.random.poisson(lam=15, size=n).clip(1, 200)
    total_returns_count = (total_orders_count * np.random.beta(a=1, b=6, size=n)).astype(int)
    account_age         = np.random.lognormal(mean=5.5, sigma=1.2, size=n).clip(1, 3650).astype(int)
    average_return_time = np.random.exponential(scale=14, size=n).clip(0, 90).astype(int)
    fraud_history_flag  = (np.random.rand(n) < 0.08).astype(int)  # 8% of users have prior fraud

    # Non-linear realistic risk calculation
    fraud_prob = np.zeros(n)
    
    for i in range(n):
        risk = 0.1  # base risk
        
        # 1. Return ratio penalty
        ratio = total_returns_count[i] / total_orders_count[i] if total_orders_count[i] > 0 else 0
        if ratio > 0.5 and total_orders_count[i] > 3:
            risk += 0.4
        elif ratio > 0.3:
            risk += 0.15
            
        # 2. Account Age Trust factor
        if account_age[i] > 730:      # 2+ years
            risk -= 0.15
        elif account_age[i] < 30:     # < 1 month
            risk += 0.2
            
        # 3. Return time
        if average_return_time[i] > 20: # taking very long to return is sketchy
            risk += 0.15
            
        # 4. Fraud history is a massive red flag
        if fraud_history_flag[i] == 1:
            risk += 0.6
            
        # 5. Absolute volume penalty
        if total_returns_count[i] > 5 and ratio > 0.2:
            risk += 0.15
            
        fraud_prob[i] = risk

    # Add some irreducible noise (human randomness)
    noise = np.random.normal(0, 0.12, size=n)
    fraud_prob = np.clip(fraud_prob + noise, 0, 1)
    
    # A transaction is 'high risk' ground truth if prob > 0.6
    is_high_risk = (fraud_prob > 0.6).astype(int)

    df = pd.DataFrame({
        "total_orders_count":   total_orders_count,
        "total_returns_count":  total_returns_count,
        "account_age":          account_age,
        "average_return_time":  average_return_time,
        "fraud_history_flag":   fraud_history_flag,
        "is_high_risk":         is_high_risk,
    })
    return df


def main():
    print("[*] Generating realistic dataset with new features...")
    df = generate_dataset(N_SAMPLES)

    feature_cols = [c for c in df.columns if c != "is_high_risk"]
    X = df[feature_cols].values
    y = df["is_high_risk"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    print("[*] Training RandomForest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train_s, y_train)

    print("\n[*] Classification Report (test set):")
    print(classification_report(y_test, model.predict(X_test_s)))

    joblib.dump(model,  os.path.join(MODEL_DIR, "rf_model.joblib"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.joblib"))
    print(f"\n[OK] Model saved -> {MODEL_DIR}")


if __name__ == "__main__":
    main()
