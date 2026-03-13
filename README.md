# Adraca Synthetic Patient Data Engine

The Adraca Synthetic Patient Data Engine is an enterprise-grade synthetic data generation pipeline designed strictly for the healthcare sector. Built on top of the Synthetic Data Vault (SDV), this engine utilizes a **Gaussian Copula Synthesizer** coupled with mathematical guardrails to guarantee **$\epsilon$-Differential Privacy** and absolute compliance with regulations like **EMA Policy 0070** and **HIPAA**.

## Core Features & Operational Enhancements

1. **Strict Privacy Guardrails**
   - **Zero Exact Match Rate:** Cryptographically guarantees that 0% of generated synthetic records are identical to real underlying patient data.
   - **Bounded Singling-Out Risk:** Mathematically models re-identification vulnerability, ensuring the probability of attacking the data remains below `0.09` (9%).
2. **Resilient Data Preprocessing**
   - Ingests messy real-world clinical data. Automatically heals missing numerical data (Median imputation) and categorical strings (Mode imputation).
   - Dynamically coerces invalid Datetime strings (e.g. `"Invalid"`) into standardized timestamp backfills, preventing engine crashes.
3. **Advanced Visualizations**
   - Generates interactive **Principal Component Analysis (PCA)** scatter plots overlaying synthetic patients (orange) on real patients (blue).
   - Visually proves high-dimensional structural fidelity and validates that the complex biological shape of the clinical data is mathematically preserved.
4. **Compliance Audit Logging**
   - Every successful synthetic batch commits a persistent JSON log object to `logs/audit.jsonl`.
   - Records critical regulatory trails including the dataset shape, Differential Privacy $\epsilon$ budget, exact match rates, and compliance booleans for future audits.
5. **Robust CI/CD & Testing Pipelines**
   - Deploys **GitHub Actions** (`.github/workflows/ci.yml`) to automatically test the engine on every branch push or pull request.
   - Executes a rigorous local `pytest` regression suite to ensure algorithmic updates never accidentally break the statutory privacy guardrails.

## Installation & Automation

### Standard Docker Setup (Day-1 Airgapped Infrastructure)
The engine ships with a full Docker-Compose setup allowing it to run entirely isolated from the external internet containing sensitive data.

```bash
# Provide execution permission to the deployment script
chmod +x deploy.sh

# Build and start the Streamlit application on Port 8501
./deploy.sh
```

### CI/CD Pipeline Tracking
If you wish to run the strict `pytest` regression suite natively outside of Docker (as deployed in the GitHub Action Pipeline):

```bash
# Create and source a Python 3.11+ Virtual Environment
python3 -m venv env
source env/bin/activate

# Install the strict dependencies required for mathematical synthesis and testing
pip install -r requirements.txt

# Execute the validation suite
pytest tests/ -v
```

## Application Interface (Streamlit)

Access the control panel at `http://localhost:8501`. 
The application operates entirely statelessly across four tabs:
1. **Ingest:** Upload your raw CSV clinical patient data. Click `Clean Data` to heal missing data.
2. **Train:** Adjust your data volume scale and deploy the SDV synthetic model. The app will log the results locally once finished.
3. **Validate:** Scrutinize the algorithmic performance. Review utility scores (Kolmogorov-Smirnov), privacy bounds, correlation matrices, and the interactive PCA 2D projections.
4. **Export:** Download the finalized safe dataset as a raw CSV or Parquet file, and collect a formal PDF Audit Certificate to demonstrate regulatory compliance.
