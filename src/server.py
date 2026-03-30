import os
import json
import logging
import sqlite3
import pandas as pd
import numpy as np
import io

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.export import export_to_sqlite
from src.audit import AuditLogger
from src.main import create_pdf_report
from src.privacy import PrivacyValidator
from src.synthesizer import DataIngestor, AdracaSynthesizer

app = FastAPI(title="Adraca Synthetic Patient Engine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory state to replace Streamlit session state
# (In a production environment without single-user constraints, this would be a Redis or DB cache)
GLOBAL_STATE = {
    "real_data": None,
    "synthetic_data": None,
    "metrics": {}
}

os.makedirs('./data/input/', exist_ok=True)
os.makedirs('./reports/', exist_ok=True)
os.makedirs('./logs/', exist_ok=True)


@app.post("/api/ingest/upload")
async def ingest_upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        file_path = f'./data/input/{file.filename}'
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
            df.to_csv(file_path, index=False)
        else:
            df = pd.read_parquet(io.BytesIO(content))
            df.to_parquet(file_path, index=False)
        
        GLOBAL_STATE["real_data"] = df
        
        return JSONResponse({
            "status": "success", 
            "message": f"Loaded {df.shape[0]} rows and {df.shape[1]} columns.",
            "shape": {"rows": df.shape[0], "columns": df.shape[1]}
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ingest/sqlite")
async def ingest_sqlite(db_path: str = Form(...), table_name: str = Form(...)):
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found.")
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        GLOBAL_STATE["real_data"] = df
        return JSONResponse({"status": "success", "rows": df.shape[0], "columns": df.shape[1]})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/generate")
async def generate_synthetic_data(epsilon: float = Form(...), target_rows: int = Form(...)):
    if GLOBAL_STATE["real_data"] is None:
        raise HTTPException(status_code=400, detail="No real data loaded.")
        
    try:
        df_real = GLOBAL_STATE["real_data"]
        
        # Meta Inference
        ingestor = DataIngestor()
        metadata = ingestor.infer_metadata(df_real)
        
        # Synthesizer
        synthesizer = AdracaSynthesizer(metadata=metadata, epsilon=epsilon)
        synthesizer.fit(df_real)
        num_oversample = target_rows + int(target_rows * 0.1)
        raw_synthetic_data = synthesizer.sample(num_rows=num_oversample)
        
        # Validation
        validator = PrivacyValidator(real_data=df_real, synthetic_data=raw_synthetic_data)
        valid_synthetic_data, dcr_values, exact_match_rate = validator.calculate_dcr()
        
        avg_ks, avg_kl, avg_hellinger = validator.evaluate_utility()
        risk_score = validator.evaluate_reidentification_risk()
        is_compliant = (risk_score <= 0.09) and (exact_match_rate == 0.0)
        
        # Build PCA for frontend charts securely
        pca_payload = []
        corr_payload = {}
        numeric_real = df_real.select_dtypes(include=[np.number])
        numeric_syn = valid_synthetic_data.select_dtypes(include=[np.number])
        
        if not numeric_real.empty and numeric_real.shape[1] >= 2:
            scaler = StandardScaler()
            real_scaled = scaler.fit_transform(numeric_real.dropna())
            pca = PCA(n_components=2)
            real_pca = pca.fit_transform(real_scaled)
            syn_scaled = scaler.transform(numeric_syn.dropna())
            syn_pca = pca.transform(syn_scaled)
            
            for i in range(len(real_pca)):
                pca_payload.append({"PC1": float(real_pca[i][0]), "PC2": float(real_pca[i][1]), "Dataset": "Real"})
            for i in range(min(len(syn_pca), target_rows)):
                pca_payload.append({"PC1": float(syn_pca[i][0]), "PC2": float(syn_pca[i][1]), "Dataset": "Synthetic"})
        
        # Correlation Matrices handling
        if not numeric_real.empty:
            corr_payload["real"] = numeric_real.corr().fillna(0).to_dict()
            corr_payload["synthetic"] = numeric_syn.corr().fillna(0).to_dict()

        # Update Session State globally
        GLOBAL_STATE["synthetic_data"] = valid_synthetic_data.head(target_rows)
        GLOBAL_STATE["metrics"] = {
            "risk_score": float(risk_score),
            "exact_match_rate": float(exact_match_rate),
            "avg_ks": float(avg_ks),
            "avg_kl": float(avg_kl),
            "avg_hellinger": float(avg_hellinger),
            "is_compliant": bool(is_compliant)
        }
        
        # Immutable Audit Trail
        logger = AuditLogger()
        logger.log_run(
            epsilon=epsilon,
            num_input_rows=df_real.shape[0],
            num_input_cols=df_real.shape[1],
            num_output_rows=target_rows,
            singling_out_risk=risk_score,
            exact_match_rate=exact_match_rate,
            utility_score_ks=avg_ks,
            utility_score_kl=avg_kl,
            utility_score_hellinger=avg_hellinger,
            is_compliant=is_compliant
        )

        return JSONResponse({
            "status": "success",
            "metrics": GLOBAL_STATE["metrics"],
            "pca": pca_payload,
            "correlation": corr_payload
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/sqlite")
async def push_sqlite(table_name: str = Form(...)):
    if GLOBAL_STATE["synthetic_data"] is None:
        raise HTTPException(status_code=400, detail="No synthetic data generated.")
    try:
        db_path = "./data/synthetic_patients.db" 
        success = export_to_sqlite(GLOBAL_STATE["synthetic_data"], db_path, table_name)
        if success:
            return {"status": "success"}
        raise HTTPException(status_code=500, detail="SQLite export encountered an error.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/pdf")
async def generate_pdf():
    if not GLOBAL_STATE["metrics"]:
        raise HTTPException(status_code=400, detail="No metrics available.")
    try:
        report_path = "./reports/output_certificate.pdf"
        m = GLOBAL_STATE["metrics"]
        create_pdf_report(
            report_path=report_path,
            risk_score=m["risk_score"],
            dcr_exact_rate=m["exact_match_rate"],
            avg_ks=m["avg_ks"],
            avg_kl=m["avg_kl"],
            avg_hellinger=m["avg_hellinger"],
            is_compliant=m["is_compliant"]
        )
        return FileResponse(report_path, media_type="application/pdf", filename="Certificate_of_Anonymity.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/observability")
async def get_observability():
    log_path = "./logs/audit.jsonl"
    if not os.path.exists(log_path):
        return {"history": []}
    
    history = []
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    history.append({
                        "timestamp": record.get("timestamp_utc", ""),
                        "epsilon": record.get("parameters", {}).get("epsilon_privacy_budget", 0),
                        "ks_utility": record.get("metrics", {}).get("utility_score_ks_complement", 0),
                        "risk": record.get("metrics", {}).get("singling_out_risk", 0),
                        "exact_match": record.get("metrics", {}).get("exact_match_rate_pct", 0),
                        "compliant": record.get("compliance", {}).get("passed_ema_policy_0070", False)
                    })
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mount React build
if os.path.exists("./frontend/dist"):
    app.mount("/", StaticFiles(directory="./frontend/dist", html=True), name="frontend")
