# Adraca Synthetic Patient Engine 🧬

A highly secure, zero-trust tabular synthetic data generation engine tailored for sensitive healthcare and life sciences data. 

Built to comply explicitly with **GDPR Recital 26** and **EMA Policy 0070** guidelines, this engine provides guaranteed privacy preservation via strict $\epsilon$-Differential Privacy and automated distance metric guardrails.

## Features Let Down
1. **100% Air-Gapped / Offline-Ready:** All dependencies are securely packaged in the local `./wheels/` directory. No external CDNs, pip repos, or telemetry are needed.
2. **Modular Zero-Trust Architecture:** Processing steps are firmly isolated under the `/src/` source code.
3. **Multi-Stage Pipeline:**
   - **Ingestion:** Secure data loads from `/data/input/`.
   - **Engine:** `GaussianCopulaSynthesizer` with bounded Laplace noise injection.
   - **Validation:** automated checks enforcing Re-identification Risk $< \text{0.09}$ and Exact Match Rate $== \text{0.0\%}$ using `anonymeter` and `gower`.
   - **Certification:** Outputs synthetic data to `/data/output/` alongside a traceable PDF Certificate of Anonymity in `/reports/`.
4. **Interactive Dashboard:** Full pipeline operability via a Streamlit UI.

---

## 🚀 Quickstart Guide

This system supports both strict offline deployment environments: standalone Linux (Python virtual environment) or Docker.

### Option A: Running via Docker (Recommended)
If your deployment environment has Docker installed, building the engine takes a single command. The Dockerfile installs dependencies completely off-grid.

```bash
docker compose up --build -d
```
Access the application dashboard at **http://localhost:8501**. 
*(Note: Ensure your source files and reports are mapped correctly in the volume bindings if you modify the `docker-compose.yml`.)*

### Option B: Running Locally (Linux shell)
If Docker isn't available, use the provided wrapper script to automatically provision a python virtual environment, unpack the wheels, and boot the server without internet.

1. Make the script executable:
```bash
chmod +x run.sh
```
2. Launch the Streamlit application:
```bash
./run.sh
```

### Option C: Source Control Initialization (Offline)
If you are staging this codebase for an offline transfer (via USB or private intranet), a robust `.gitignore` is included to ensure no sensitive cache, virtual environments, or data are synced.
Once transferred to the secure air-gapped host, run:
```bash
git init
git branch -M main
git add .
git commit -m "chore: initial commit of zero-trust synthetic engine"
```

---

## 📂 Project Structure

```text
adraca-synthetic-engine/
│
├── src/                    # Proprietary Backend Code
│   ├── app.py              # Streamlit Web User Interface
│   ├── main.py             # CLI Pipeline execution 
│   ├── synthesizer.py      # Core SDV Gaussian Copula Engine
│   ├── validation.py       # Metrics Evaluation Definitions
│   └── privacy.py          # Strict Privacy Guardrail rules
│
├── data/
│   ├── input/              # Secure raw data drop (.csv, .parquet)
│   └── output/             # Authorized synthetic data retrieval
│
├── models/                 # Persistent serialization of Copulas (.pkl)
├── reports/                # Generated Certificates of Anonymity (.pdf)
│
├── wheels/                 # Pre-built PyPI wheels for fully offline installs
├── requirements.txt        # Pinned strict dependencies 
├── docker-compose.yml      # Container orchestration
└── Dockerfile              # Container building instruction
```
