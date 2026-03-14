# Adraca Synthetic Patient Data Engine: Automation & CI/CD Hub

Welcome to the **Automation Branch** of the Adraca Synthetic Patient Data Engine repository! This branch is strictly dedicated to hosting, configuring, and testing the complex Continuous Integration / Continuous Deployment (CI/CD) pipelines and regression testing suites.

While the `main` branch holds the stable enterprise releases of the Dockerized engine, this branch tracks the active developments of mathematical guardrails (like testing EMA Policy 0070 restrictions) and the GitHub Actions automation layers.

## Core Automations Overview

1. **GitHub Actions Workflow**
   - **Location:** `.github/workflows/ci.yml`
   - **Trigger:** Configured to trigger upon every `push` to `main` as well as any `pull_request` attempting to merge into it.
   - **Action:** Provisions an isolated `ubuntu-latest` Linux runner. It installs Python 3.11, grabs the latest exact dependencies defined in our native `requirements.txt` file (bypassing the heavy offline-Docker containers), and completely isolates the backend algorithm into an agile testing environment.
2. **Pytest Regression Suite**
   - **Location:** `tests/` directory
   - **Purpose:** We designed a rigorous array of hardcoded Unit Tests. Instead of simply asserting that functions "run without crashing", these tests forcefully feed explicit privacy violations into the `PrivacyValidator` (such as identical real & synthetic row collisions and singling-out metrics intentionally pushed beyond 0.09 probabilities).
   - **Verification:** The Pytest suite must catch and flag 100% of these hardcoded violations accurately. Total testing success is the only way a build is permitted to merge into the codebase.
3. **Air-Gapped Embedded SQLite Integrations**
   - **Location:** `src/export.py` & Ingestion UI
   - **Purpose:** Because the enterprise environment is strictly mathematically air-gapped, we cannot securely pipe patient data to AWS S3 or a hosted PostgreSQL server. 
   - **Feature:** We engineered a local SQLAlchemy pipeline that can bi-directionally read real patient data from, and systematically append safe synthetic patient data to, a serverless local SQLite `.db` file bound to the `./data/` docker mount.
4. **Multi-Stage Docker Optimization**
   - **Location:** `Dockerfile`
   - **Purpose:** To radically reduce cloud image storage costs and eliminate the security attack surface of shipping C++ compilers inside a production container.
   - **Feature:** The container utilizes an ephemeral Builder stage to compile heavy deep learning algorithms from source, then drops the compilers and injects *only* the finished binaries into a minimalistic Runner production stage.

## Testing Architecture

If you are developing new AI layers or tightening the regulatory math in the backend `src/` modules, you must execute the suite identically to how the cloud Action server will evaluate it.

### Local Simulation Initialization

Instead of deploying the full Streamlit UI or starting Docker, execute this workflow on your local host:

```bash
# 1. Create and isolate a formal Python execution environment
python3 -m venv test_env
source test_env/bin/activate

# 2. Upgrade pip and install the direct repository requirements 
# (This step pulls complex ML libraries natively like 'sdv' and custom forks like statice's 'anonymeter')
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Mount the engine source to the Python Path and trigger Pytest verbosely
PYTHONPATH=. pytest tests/ -v
```

## Maintenance & Contributions

When introducing new Python dependencies into the core engine architecture, ensure they are actively documented inside `requirements.txt`. Complex deep-learning modules (like `torch` and `numba`) must be explicitly version-bound to prevent future unprompted compatibility failures in the automated GitHub build log.
