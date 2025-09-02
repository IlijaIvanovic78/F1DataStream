"""
MLaaS - Machine Learning as a Service for F1 Lap Time Prediction
Uses FastAPI to provide REST endpoints for training and prediction
"""

import os
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import joblib
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


app = FastAPI(
    title="MLaaS - F1 Lap Time Prediction",
    description="Machine Learning service for predicting F1 lap times based on telemetry data",
    version="1.0.0"
)


model = None
scaler = None
model_info = {
    "status": "not_trained",
    "last_trained": None,
    "metrics": {},
    "feature_importance": {}
}


DATA_PATH = os.getenv("DATA_PATH", "/data/f1_telemetry_wide.csv")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/lap_time_predictor.pkl")
SCALER_PATH = os.getenv("SCALER_PATH", "/app/models/scaler.pkl")


class PredictionRequest(BaseModel):
    driver: str
    lap_number: int
    speed: float
    throttle: float
    brake: bool
    n_gear: int
    rpm: float
    drs: bool
    x: float
    y: float


class PredictionResponse(BaseModel):
    predicted_lap_time: float
    confidence_interval: Dict[str, float]
    model_version: str
    timestamp: str


class TrainingResponse(BaseModel):
    status: str
    message: str
    metrics: Dict[str, float]
    timestamp: str


class ModelInfoResponse(BaseModel):
    status: str
    last_trained: Optional[str]
    metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    total_predictions: int


def load_and_prepare_data(file_path: str) -> pd.DataFrame:
    """Load and prepare F1 telemetry data for training with advanced features"""
    
    try:
        df = pd.read_csv(file_path)
        

        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce')
        df = df.dropna(subset=['timestamp'])  
        df = df.sort_values(['driver', 'LapNumber', 'timestamp'])
        
        lap_times = []
        for driver in df['driver'].unique():
            driver_data = df[df['driver'] == driver]
            
            for lap in driver_data['LapNumber'].unique():
                lap_data = driver_data[driver_data['LapNumber'] == lap]
                if len(lap_data) > 0:
                    lap_time = (lap_data['timestamp'].max() - lap_data['timestamp'].min()).total_seconds()
                    lap_times.append({
                        'driver': driver,
                        'lap_number': lap,
                        'lap_time': lap_time
                    })
        
        lap_times_df = pd.DataFrame(lap_times)
        
        agg_features = {
            'Speed': ['mean', 'max', 'std', 'min', 'median'],
            'Throttle': ['mean', 'max', 'std', 'min'],
            'Brake': ['sum', 'mean', 'count'], 
            'nGear': ['mean', 'max', 'std', 'min'],
            'RPM': ['mean', 'max', 'std', 'min', 'median'],
            'DRS': ['sum', 'mean', 'count'],  
            'X': ['std', 'mean', 'max', 'min'],  
            'Y': ['std', 'mean', 'max', 'min']  
        }
        
        lap_features = df.groupby(['driver', 'LapNumber']).agg(agg_features)
        lap_features.columns = ['_'.join(col).strip() for col in lap_features.columns.values]
        lap_features = lap_features.reset_index()
        

        lap_features = lap_features.rename(columns={'LapNumber': 'lap_number'})

        lap_features['speed_range'] = lap_features['Speed_max'] - lap_features['Speed_min']
        lap_features['rpm_range'] = lap_features['RPM_max'] - lap_features['RPM_min']
        lap_features['throttle_range'] = lap_features['Throttle_max'] - lap_features['Throttle_min']
        lap_features['gear_range'] = lap_features['nGear_max'] - lap_features['nGear_min']

        lap_features['speed_efficiency'] = lap_features['Speed_mean'] / (lap_features['RPM_mean'] + 1)
        lap_features['throttle_efficiency'] = lap_features['Speed_mean'] / (lap_features['Throttle_mean'] + 0.1)
        

        lap_features['speed_consistency'] = 1 / (lap_features['Speed_std'] + 1)
        lap_features['rpm_consistency'] = 1 / (lap_features['RPM_std'] + 1)
        

        driver_stats = lap_features.groupby('driver').agg({
            'Speed_mean': ['mean', 'std'],
            'RPM_mean': ['mean', 'std'],
            'Throttle_mean': ['mean', 'std']
        }).reset_index()
        driver_stats.columns = ['driver', 'driver_speed_mean', 'driver_speed_std', 
                               'driver_rpm_mean', 'driver_rpm_std',
                               'driver_throttle_mean', 'driver_throttle_std']
        

        lap_features = pd.merge(lap_features, driver_stats, on='driver')

        lap_features['speed_vs_driver_avg'] = lap_features['Speed_mean'] - lap_features['driver_speed_mean']
        lap_features['rpm_vs_driver_avg'] = lap_features['RPM_mean'] - lap_features['driver_rpm_mean']
        lap_features['throttle_vs_driver_avg'] = lap_features['Throttle_mean'] - lap_features['driver_throttle_mean']
        

        final_df = pd.merge(lap_features, lap_times_df, on=['driver', 'lap_number'])
        

        final_df = final_df[(final_df['lap_time'] > 60) & (final_df['lap_time'] < 200)]
        
        return final_df
        
    except Exception as e:
        raise


def train_model(df: pd.DataFrame) -> Dict[str, Any]:
    """Train the lap time prediction model"""
    global model, scaler, model_info
    

    feature_columns = [col for col in df.columns if col not in ['driver', 'lap_number', 'lap_time']]
    X = df[feature_columns]
    y = df['lap_time']
    

    driver_dummies = pd.get_dummies(df['driver'], prefix='driver')
    X = pd.concat([X, driver_dummies], axis=1)
    

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=3,
        min_samples_leaf=1,
        max_features='sqrt',
        bootstrap=True,
        oob_score=True,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train_scaled, y_train)
    

    y_pred = model.predict(X_test_scaled)
    
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    

    feature_importance = dict(zip(X.columns, model.feature_importances_))

    top_features = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10])

    model_info = {
        "status": "trained",
        "last_trained": datetime.now().isoformat(),
        "metrics": {
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2),
            "test_samples": len(y_test)
        },
        "feature_importance": top_features
    }
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(X.columns.tolist(), os.path.join(os.path.dirname(MODEL_PATH), "feature_names.pkl"))
    
    return model_info


@app.on_event("startup")
async def startup_event():
    """Load model on startup if available"""
    global model, scaler
    
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            scaler = joblib.load(SCALER_PATH)
            model_info["status"] = "loaded"
        except Exception as e:
            pass


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "MLaaS - F1 Lap Time Prediction",
        "status": "running",
        "model_status": model_info["status"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": model is not None}


@app.post("/train", response_model=TrainingResponse)
async def train_model_endpoint(background_tasks: BackgroundTasks):
    """Train the lap time prediction model"""
    try:
        if not os.path.exists(DATA_PATH):
            raise HTTPException(status_code=404, detail=f"Data file not found at {DATA_PATH}")
        
        df = load_and_prepare_data(DATA_PATH)
        
        metrics = train_model(df)
        
        return TrainingResponse(
            status="success",
            message="Model trained successfully",
            metrics=metrics["metrics"],
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict", response_model=PredictionResponse)
async def predict_lap_time(request: PredictionRequest):
    """Predict lap time based on telemetry features"""
    if model is None or scaler is None:
        raise HTTPException(
            status_code=503, 
            detail="Model not trained. Please train the model first using /train endpoint"
        )
    
    try:

        feature_names = joblib.load(os.path.join(os.path.dirname(MODEL_PATH), "feature_names.pkl"))
        
        speed_max = request.speed * 1.15
        speed_min = request.speed * 0.85
        rpm_max = request.rpm * 1.1
        rpm_min = request.rpm * 0.9
        throttle_max = min(request.throttle * 1.1, 1.0)
        throttle_min = max(request.throttle * 0.9, 0.0)
        
        features = pd.DataFrame([{
            'Speed_mean': request.speed,
            'Speed_max': speed_max,
            'Speed_std': (speed_max - speed_min) / 4,  
            'Speed_min': speed_min,
            'Speed_median': request.speed,
            
            'Throttle_mean': request.throttle,
            'Throttle_max': throttle_max,
            'Throttle_std': (throttle_max - throttle_min) / 4,
            'Throttle_min': throttle_min,
            
            'Brake_sum': 1 if request.brake else 0,
            'Brake_mean': 1 if request.brake else 0,
            'Brake_count': 1 if request.brake else 0,
            
            'nGear_mean': request.n_gear,
            'nGear_max': request.n_gear,
            'nGear_std': 0.5,  
            'nGear_min': max(request.n_gear - 1, 1),
            
            'RPM_mean': request.rpm,
            'RPM_max': rpm_max,
            'RPM_std': (rpm_max - rpm_min) / 4,
            'RPM_min': rpm_min,
            'RPM_median': request.rpm,
            
            'DRS_sum': 1 if request.drs else 0,
            'DRS_mean': 1 if request.drs else 0,
            'DRS_count': 1 if request.drs else 0,
            
            'X_std': abs(request.x) * 0.02,
            'X_mean': request.x,
            'X_max': request.x + abs(request.x) * 0.1,
            'X_min': request.x - abs(request.x) * 0.1,
            
            'Y_std': abs(request.y) * 0.02,
            'Y_mean': request.y,
            'Y_max': request.y + abs(request.y) * 0.1,
            'Y_min': request.y - abs(request.y) * 0.1,
            
            'speed_range': speed_max - speed_min,
            'rpm_range': rpm_max - rpm_min,
            'throttle_range': throttle_max - throttle_min,
            'gear_range': 1,
            
            'speed_efficiency': request.speed / (request.rpm + 1),
            'throttle_efficiency': request.speed / (request.throttle + 0.1),
            
            'speed_consistency': 1 / ((speed_max - speed_min) / 4 + 1),
            'rpm_consistency': 1 / ((rpm_max - rpm_min) / 4 + 1),
            
            'driver_speed_mean': 0,
            'driver_speed_std': 0,
            'driver_rpm_mean': 0,
            'driver_rpm_std': 0,
            'driver_throttle_mean': 0,
            'driver_throttle_std': 0,
            
            'speed_vs_driver_avg': 0,
            'rpm_vs_driver_avg': 0,
            'throttle_vs_driver_avg': 0
        }])
        
        for col in feature_names:
            if col.startswith('driver_'):
                features[col] = 1 if col == f'driver_{request.driver}' else 0
        
        features = features.reindex(columns=feature_names, fill_value=0)
        
        features_scaled = scaler.transform(features)
        
        prediction = model.predict(features_scaled)[0]
        
        tree_predictions = np.array([tree.predict(features_scaled) for tree in model.estimators_])
        std_prediction = np.std(tree_predictions)
        
        prediction_variation = np.random.normal(0, std_prediction * 0.1)
        final_prediction = prediction + prediction_variation

        final_prediction = max(60, min(200, final_prediction))
        
        return PredictionResponse(
            predicted_lap_time=float(final_prediction),
            confidence_interval={
                "lower": float(final_prediction - 1.5 * std_prediction),
                "upper": float(final_prediction + 1.5 * std_prediction)
            },
            model_version="2.0.0",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info():
    """Get information about the current model"""
    return ModelInfoResponse(
        status=model_info["status"],
        last_trained=model_info.get("last_trained"),
        metrics=model_info.get("metrics", {}),
        feature_importance=model_info.get("feature_importance", {}),
        total_predictions=0  
    )


@app.post("/upload-data")
async def upload_training_data(file: UploadFile = File(...)):
    """Upload new training data"""
    try:
        file_path = f"/tmp/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            pd.read_csv(file_path, nrows=5)
        except:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="Invalid CSV file")
        
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        os.rename(file_path, DATA_PATH)
        
        return {"message": "Data uploaded successfully", "path": DATA_PATH}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
