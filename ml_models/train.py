import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_models.features.feature_engineering import load_features, get_feature_columns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (accuracy_score, roc_auc_score,
                             mean_absolute_error, r2_score,
                             classification_report)
import warnings
warnings.filterwarnings('ignore')

# ── MLflow setup ─────────────────────────────────────────────────────────────
mlflow.set_tracking_uri("file:./mlruns")
EXPERIMENT_NAME = "cruise_revenue_ai"
mlflow.set_experiment(EXPERIMENT_NAME)

FEATURES = get_feature_columns()


# ── Model 1: Cancellation Risk ───────────────────────────────────────────────
def train_cancellation_model(df):
    print("\n── Model 1: Cancellation Risk Classifier ──")

    X = df[FEATURES].fillna(0)
    y = df['is_cancelled'].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    with mlflow.start_run(run_name="cancellation_risk"):
        params = {
            "n_estimators":   200,
            "max_depth":      4,
            "learning_rate":  0.05,
            "subsample":      0.8,
            "random_state":   42
        }
        model = GradientBoostingClassifier(**params)
        model.fit(X_train, y_train)

        y_pred  = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)
        auc      = roc_auc_score(y_test, y_proba)

        mlflow.log_params(params)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("auc_roc",  auc)
        mlflow.log_metric("train_rows", len(X_train))
        mlflow.log_metric("test_rows",  len(X_test))
        mlflow.sklearn.log_model(model, "cancellation_risk_model")

        # Feature importance
        importance_df = pd.DataFrame({
            'feature':   FEATURES,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"  Accuracy : {accuracy:.4f}")
        print(f"  AUC-ROC  : {auc:.4f}")
        print(f"\n  Top 5 features:")
        print(importance_df.head(5).to_string(index=False))

    return model


# ── Model 2: Revenue per Night Predictor ─────────────────────────────────────
def train_revenue_model(df):
    print("\n── Model 2: Revenue per Night Regressor ──")

    active = df[df['is_cancelled'] == False].copy()
    active['revenue_per_night'] = (
        active['total_guest_value_usd'] / active['nights'].replace(0, np.nan)
    ).fillna(0)

    X = active[FEATURES].fillna(0)
    y = active['revenue_per_night']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    with mlflow.start_run(run_name="revenue_per_night"):
        params = {
            "n_estimators":  200,
            "max_depth":     5,
            "learning_rate": 0.05,
            "subsample":     0.8,
            "random_state":  42
        }
        model = GradientBoostingRegressor(**params)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        mae    = mean_absolute_error(y_test, y_pred)
        r2     = r2_score(y_test, y_pred)

        mlflow.log_params(params)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2",  r2)
        mlflow.log_metric("train_rows", len(X_train))
        mlflow.log_metric("test_rows",  len(X_test))
        mlflow.sklearn.log_model(model, "revenue_model")

        importance_df = pd.DataFrame({
            'feature':    FEATURES,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"  MAE : ${mae:,.2f}")
        print(f"  R²  : {r2:.4f}")
        print(f"\n  Top 5 features:")
        print(importance_df.head(5).to_string(index=False))

    return model


# ── Model 3: Upsell Propensity ────────────────────────────────────────────────
def train_upsell_model(df):
    print("\n── Model 3: Upsell Propensity Classifier ──")

    active = df[df['is_cancelled'] == False].copy()
    median_spend = active['total_onboard_spend_usd'].median()
    active['high_spender'] = (
        active['total_onboard_spend_usd'] > median_spend
    ).astype(int)

    X = active[FEATURES].fillna(0)
    y = active['high_spender']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    with mlflow.start_run(run_name="upsell_propensity"):
        params = {
            "n_estimators":  150,
            "max_depth":     4,
            "learning_rate": 0.08,
            "subsample":     0.8,
            "random_state":  42
        }
        model = GradientBoostingClassifier(**params)
        model.fit(X_train, y_train)

        y_pred  = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)
        auc      = roc_auc_score(y_test, y_proba)

        mlflow.log_params(params)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("auc_roc",  auc)
        mlflow.log_metric("train_rows", len(X_train))
        mlflow.log_metric("test_rows",  len(X_test))
        mlflow.sklearn.log_model(model, "upsell_model")

        importance_df = pd.DataFrame({
            'feature':    FEATURES,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"  Accuracy : {accuracy:.4f}")
        print(f"  AUC-ROC  : {auc:.4f}")
        print(f"\n  Top 5 features:")
        print(importance_df.head(5).to_string(index=False))

    return model


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Loading features from Snowflake...")
    df = load_features()

    print(f"\nDataset shape: {df.shape}")
    print(f"Cancellation rate: {df['is_cancelled'].mean():.2%}")

    model_cancel  = train_cancellation_model(df)
    model_revenue = train_revenue_model(df)
    model_upsell  = train_upsell_model(df)

    print("\nAll models trained successfully.")
    print("Run 'mlflow ui' to view experiment dashboard.")