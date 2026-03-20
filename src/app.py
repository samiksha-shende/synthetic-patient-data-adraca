from src.export import export_to_sqlite
from src.audit import AuditLogger
from src.main import create_pdf_report
from src.privacy import PrivacyValidator
from src.synthesizer import DataIngestor, AdracaSynthesizer
import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import io
import os
import sys
import json

# Ensure src modules are discoverable
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


# Page Configuration
st.set_page_config(
    page_title="Adraca Synthetic Patient Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Theme Styling (Minimalist Life Sciences)
st.markdown(
    """
    <style>
    .reportview-container {
        background: #F4F7F6;
    }
    .sidebar .sidebar-content {
        background: #E8F0FE;
    }
    h1 {
        color: #1A73E8;
        font-family: 'Helvetica Neue', sans-serif;
    }
    h2, h3 {
        color: #3C4043;
    }
    .stButton>button {
        background-color: #1A73E8;
        color: white;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🧬 Adraca Synthetic Patient Engine")
st.markdown("Zero-Trust Synthetic Patient Engine Control Panel")

# Initialize Session State
if 'real_data' not in st.session_state:
    st.session_state.real_data = None
if 'metadata' not in st.session_state:
    st.session_state.metadata = None
if 'synthetic_data' not in st.session_state:
    st.session_state.synthetic_data = None
if 'valid_synthetic_data' not in st.session_state:
    st.session_state.valid_synthetic_data = None
if 'risk_score' not in st.session_state:
    st.session_state.risk_score = None
if 'exact_match_rate' not in st.session_state:
    st.session_state.exact_match_rate = None
if 'avg_ks' not in st.session_state:
    st.session_state.avg_ks = None
if 'is_compliant' not in st.session_state:
    st.session_state.is_compliant = None

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Configuration")

    epsilon_val = st.slider(
        "ε-Differential Privacy Budget",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1,
        help="Lower values mean more privacy and noise, higher values mean less privacy but higher fidelity."
    )

    target_rows = st.number_input(
        "Target Row Count",
        min_value=10,
        max_value=100000,
        value=500,
        step=100
    )

    synthesizer_selection = st.selectbox(
        "Synthesizer Algorithm",
        ("Gaussian Copula (Default CPU)",)
    )

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["1. Ingestion", "2. Training", "3. Validation", "4. Export", "5. Observability & Drift"])

# =======================
# TAB 1: Ingestion
# =======================
with tab1:
    st.header("Ingest Patient Data")

    ingest_method = st.radio("Select Ingestion Method:", ["File Upload", "Local SQLite Database"])

    df = None

    if ingest_method == "File Upload":
        uploaded_file = st.file_uploader("Upload CSV or Parquet file", type=["csv", "parquet"])
        if uploaded_file is not None:
            try:
                # Read Data
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_parquet(uploaded_file)

                # Save to /data/input/ for tracking
                os.makedirs('./data/input/', exist_ok=True)
                input_path = f'./data/input/{uploaded_file.name}'
                if uploaded_file.name.endswith('.csv'):
                    df.to_csv(input_path, index=False)
                else:
                    df.to_parquet(input_path, index=False)
            except Exception as e:
                st.error(f"Error reading file: {e}")

    elif ingest_method == "Local SQLite Database":
        st.info("Ingest real patient data securely from a local Air-Gapped SQLite database.")
        db_path = st.text_input("SQLite Database Path", value="./data/real_patients.db")
        table_name = st.text_input("Source Table Name", value="real_patients")

        if st.button("Load from Database"):
            if not os.path.exists(db_path):
                st.error(f"Database file not found at {db_path}")
            elif not table_name:
                st.error("Please provide a valid table name.")
            else:
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_path)

                    allowed_tables = ["real_patients", "synthetic_patients"]
                    if table_name not in allowed_tables:
                        raise ValueError(f"Invalid table name: {table_name}")

                    query = " ".join(["SELECT", "*", "FROM", table_name])
                    df = pd.read_sql_query(query, conn)
                    conn.close()
                except Exception as e:
                    st.error(f"Error reading from database: {e}")

    # Process Data if successfully loaded
    if df is not None:
        st.session_state.real_data = df
        st.success(f"Successfully loaded {df.shape[0]} rows and {df.shape[1]} columns.")

        # Data Health Summary
        st.subheader("Data Health Summary")
        col1, col2 = st.columns(2)

        # Column Types
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        dt_cols = df.select_dtypes(include=['datetime']).columns.tolist()

        with col1:
            st.write("**Feature Types:**")
            st.write(f"- Categorical: {len(cat_cols)}")
            st.write(f"- Numerical: {len(num_cols)}")
            st.write(f"- Datetime: {len(dt_cols)}")

        # Missing Values
        with col2:
            missing_pct = df.isnull().mean() * 100
            st.write("**Missing Values:**")
            if missing_pct.sum() == 0:
                st.write("No missing values detected.")
            else:
                st.dataframe(missing_pct[missing_pct > 0].to_frame(name="% Missing"))

        # Show preview
        st.write("**Data Preview:**")
        st.dataframe(df.head())

# =======================
# TAB 2: Training
# =======================
with tab2:
    st.header("Synthetic Engine Execution")

    if st.session_state.real_data is None:
        st.info("Plese upload data in the Ingestion tab first.")
    else:
        st.write(f"**Selected Synthesizer:** {synthesizer_selection}")
        st.write(f"**Privacy Budget (ε):** {epsilon_val}")
        st.write(f"**Target Rows:** {target_rows}")

        start_btn = st.button("🚀 Start Engine")

        status_text = st.empty()
        progress_bar = st.progress(0)

        if start_btn:
            try:
                # Stage 1: Meta
                status_text.text("Status: Inferring Metadata...")
                progress_bar.progress(10)
                ingestor = DataIngestor()
                metadata = ingestor.infer_metadata(st.session_state.real_data)
                st.session_state.metadata = metadata

                # Stage 2: Engine
                status_text.text("Status: Fitting Marginal Distributions (Gaussian Copula)...")
                progress_bar.progress(30)
                synthesizer = AdracaSynthesizer(metadata=metadata, epsilon=epsilon_val)
                synthesizer.fit(st.session_state.real_data)

                status_text.text(f"Status: Injecting Laplacian Noise (ε={epsilon_val})...")
                progress_bar.progress(50)

                num_oversample = target_rows + int(target_rows * 0.1)
                raw_synthetic_data = synthesizer.sample(num_rows=num_oversample)

                # Stage 3: Validation
                status_text.text("Status: Calculating Gower Distance and evaluating Privacy...")
                progress_bar.progress(70)

                validator = PrivacyValidator(real_data=st.session_state.real_data, synthetic_data=raw_synthetic_data)
                valid_synthetic_data, dcr_values, exact_match_rate = validator.calculate_dcr()

                status_text.text("Status: Evaluating Statistical Utility...")
                progress_bar.progress(85)
                avg_ks = validator.evaluate_utility()
                risk_score = validator.evaluate_reidentification_risk()

                is_compliant = (risk_score <= 0.09) and (exact_match_rate == 0.0)

                # Store globally
                st.session_state.valid_synthetic_data = valid_synthetic_data.head(target_rows)
                st.session_state.risk_score = risk_score
                st.session_state.exact_match_rate = exact_match_rate
                st.session_state.avg_ks = avg_ks
                st.session_state.is_compliant = is_compliant

                # Write to the Persistent Audit Log
                status_text.text("Status: Writing Compliance Audit Log...")
                progress_bar.progress(95)
                logger = AuditLogger()
                logger.log_run(
                    epsilon=epsilon_val,
                    num_input_rows=st.session_state.real_data.shape[0],
                    num_input_cols=st.session_state.real_data.shape[1],
                    num_output_rows=target_rows,
                    singling_out_risk=risk_score,
                    exact_match_rate=exact_match_rate,
                    utility_score=avg_ks,
                    is_compliant=is_compliant
                )

                progress_bar.progress(100)
                status_text.text("Status: Generation & Validation Complete!")
                st.success("Engine Execution Finished and Audit Logged successfully. Please proceed to the Validation Tab.")

            except Exception as e:
                st.error(f"Engine failed: {e}")

# =======================
# TAB 3: Validation
# =======================
with tab3:
    st.header("Validation & Quality Check")

    if st.session_state.valid_synthetic_data is None:
        st.info("Please generate synthetic data in the Training tab first.")
    else:
        # Scorecards
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Privacy Scorecard")
            risk = st.session_state.risk_score
            dcr_match = st.session_state.exact_match_rate

            # Risk color
            if risk > 0.09:
                st.error(f"Re-identification Risk: {risk:.4f} (Violates Threshold > 0.09)")
            else:
                st.success(f"Re-identification Risk: {risk:.4f} (Pass)")

            if dcr_match > 0.0:
                st.error(f"Exact Match Rate: {dcr_match:.2%} (Singling Out Risk Detected)")
            else:
                st.success(f"Exact Match Rate: {dcr_match:.2%} (Pass)")

        with col2:
            st.subheader("Fidelity Scorecard")
            st.info(f"Average KS Complement (Utility): {st.session_state.avg_ks:.4f}")
            st.write("Higher values (closer to 1.0) indicate better preservation of statistical properties.")

        # Correlation Matrices
        st.subheader("Correlation Matrix Comparison")
        st.write("Comparing feature dependencies between Real and Synthetic datasets.")

        # Only compute corr for numeric columns
        numeric_real = st.session_state.real_data.select_dtypes(include=[np.number])
        numeric_syn = st.session_state.valid_synthetic_data.select_dtypes(include=[np.number])

        if not numeric_real.empty:
            corr_real = numeric_real.corr()
            corr_syn = numeric_syn.corr()

            fig, ax = plt.subplots(1, 2, figsize=(14, 5))
            sns.heatmap(corr_real, ax=ax[0], cmap="coolwarm", annot=False, cbar=False)
            ax[0].set_title("Real Data Correlation")

            sns.heatmap(corr_syn, ax=ax[1], cmap="coolwarm", annot=False, cbar=False)
            ax[1].set_title("Synthetic Data Correlation")

            st.pyplot(fig)
        else:
            st.warning("Not enough numeric columns to generate a correlation matrix.")

        # PCA Scatter Plot (Fidelity overlay)
        st.subheader("Principal Component Analysis (PCA) Overlay")
        st.write("Visualizing high-dimensional numerical distributions on a 2D plane. High fidelity is achieved when the Synthetic data smoothly overlaps the Real data.")

        if not numeric_real.empty and numeric_real.shape[1] >= 2:
            try:
                # 1. Standardize and reduce original Real data
                scaler = StandardScaler()
                real_scaled = scaler.fit_transform(numeric_real.dropna())

                pca = PCA(n_components=2)
                real_pca = pca.fit_transform(real_scaled)

                # 2. Standardize and reduce Synthetic data (using the same learned PCA basis)
                syn_scaled = scaler.transform(numeric_syn.dropna())
                syn_pca = pca.transform(syn_scaled)

                # Assemble Dataframes for Seaborn
                pca_real_df = pd.DataFrame(real_pca, columns=['PC1', 'PC2'])
                pca_real_df['Dataset'] = 'Real Data'

                pca_syn_df = pd.DataFrame(syn_pca, columns=['PC1', 'PC2'])
                pca_syn_df['Dataset'] = 'Synthetic Data'

                pca_df = pd.concat([pca_real_df, pca_syn_df], axis=0)

                # Plot
                fig_pca, ax_pca = plt.subplots(figsize=(10, 6))
                sns.scatterplot(
                    data=pca_df,
                    x='PC1',
                    y='PC2',
                    hue='Dataset',
                    palette={'Real Data': '#1A73E8', 'Synthetic Data': '#F29900'},
                    alpha=0.6,
                    edgecolor=None,
                    ax=ax_pca
                )
                ax_pca.set_title("Real vs. Synthetic Data Representation (PCA)")
                st.pyplot(fig_pca)

            except Exception as e:
                st.warning(f"Failed to generate PCA scatter plot: {e}")
        else:
            st.warning("PCA requires at least two continuous numerical columns in the dataset.")

# =======================
# TAB 4: Export
# =======================
with tab4:
    st.header("Export Data & Compliance Certificate")

    if st.session_state.valid_synthetic_data is None:
        st.info("Please generate synthetic data in the Training tab first.")
    else:
        df_export = st.session_state.valid_synthetic_data

        st.subheader("1. Download Synthetic Dataset")

        col_csv, col_parquet = st.columns(2)

        with col_csv:
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name='synthetic_patient_data.csv',
                mime='text/csv',
            )

        with col_parquet:
            # Save to buffer for parquet
            buffer = io.BytesIO()
            df_export.to_parquet(buffer, index=False)
            st.download_button(
                label="📥 Download Parquet",
                data=buffer.getvalue(),
                file_name='synthetic_patient_data.parquet',
                mime='application/octet-stream',
            )

        st.markdown("---")
        st.subheader("2. Export to SQLite Database")
        st.write("Safely pipe these synthetic patients directly into an offline database without downloading local files.")

        table_name = st.text_input("Target Database Table Name", value="synthetic_patients")

        if st.button("Push to Local Database"):
            if not table_name:
                st.error("Please provide a valid table name.")
            else:
                db_path = "./data/synthetic_patients.db"  # Path inside the mounted docker volume
                success = export_to_sqlite(df_export, db_path, table_name)

                if success:
                    st.success(
                        f"Successfully piped {
                            len(df_export)} rows to the `{table_name}` table in the offline database!")
                    st.toast("Export Complete!")
                else:
                    st.error("Fatal Error occurred during database execution. Check internal logs.")

        st.subheader("3. Certificate of Anonymity")
        st.write("Generate the PDF certificate proving compliance with EMA Policy 0070.")

        if st.button("📄 Generate Certificate"):
            os.makedirs('./reports/', exist_ok=True)
            report_path = "./reports/output_certificate.pdf"

            create_pdf_report(
                report_path=report_path,
                risk_score=st.session_state.risk_score,
                dcr_exact_rate=st.session_state.exact_match_rate,
                avg_ks=st.session_state.avg_ks,
                is_compliant=st.session_state.is_compliant
            )

            with open(report_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download PDF Certificate",
                    data=pdf_file,
                    file_name="Certificate_of_Anonymity.pdf",
                    mime="application/pdf"
                )

            st.success(f"Certificate saved to {report_path}")

# =======================
# TAB 5: Observability & Drift
# =======================
with tab5:
    st.header("📈 Observability & Drift Monitoring")
    st.markdown("Track the historical degradation or improvement of the generating engine. Monitor specific statutory metrics over the entire enterprise lifetime.")

    log_path = "./logs/audit.jsonl"

    if not os.path.exists(log_path):
        st.info("No historical logs detected. Execute the engine in the Training tab to begin tracking telemetry.")
    else:
        # 1. Parse JSONL History
        history = []
        try:
            with open(log_path, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        history.append(
                            {
                                "Run Timestamp (UTC)": record.get(
                                    "timestamp_utc", "Unknown"), "Privacy Budget (ε)": record.get(
                                    "parameters", {}).get(
                                    "epsilon_privacy_budget", np.nan), "KS Complement (Utility)": record.get(
                                    "metrics", {}).get(
                                    "utility_score_ks_complement", np.nan), "Singling Out Risk": record.get(
                                    "metrics", {}).get(
                                    "singling_out_risk", np.nan), "Exact Match Rate": record.get(
                                        "metrics", {}).get(
                                            "exact_match_rate_pct", np.nan), "Passed 0070": record.get(
                                                "compliance", {}).get(
                                                    "passed_ema_policy_0070", False)})

            df_history = pd.DataFrame(history)

            # 2. Active Alerting Engine (Evaluates the *latest* run)
            st.subheader("Active Engine Health Status")
            if not df_history.empty:
                latest_run = df_history.iloc[-1]

                col1, col2, col3 = st.columns(3)

                with col1:
                    latest_utility = latest_run['KS Complement (Utility)']
                    if latest_utility < 0.80:
                        st.error(f"🚨 Model Drift Warning! Utility dropped to {latest_utility:.2f}")
                    else:
                        st.success(f"✅ Fidelity Stable: {latest_utility:.2f}")

                with col2:
                    latest_risk = latest_run['Singling Out Risk']
                    if latest_risk > 0.09:
                        st.error(f"🚨 Severe Privacy Violation! Risk jumped to {latest_risk:.4f}")
                    else:
                        st.success(f"✅ Re-ID Risk Guarded: {latest_risk:.4f}")

                with col3:
                    latest_compliance = latest_run['Passed 0070']
                    if not latest_compliance:
                        st.error("🚨 Statutory Policy 0070 Breach Detected.")
                    else:
                        st.success("✅ Fully Regulatory Compliant.")

            st.markdown("---")
            st.subheader("Historical Telemetry View")
            st.dataframe(df_history, use_container_width=True)

            # 3. Time Series Plotting
            if len(df_history) >= 2:
                st.subheader("📉 Time-Series: Fidelity Drift (Utility Score)")
                st.write("Tracks the statistical preservation of complex datasets over time. Values drifting sharply downward indicate the engine is failing to learn changing real-world logic.")
                st.line_chart(df_history["KS Complement (Utility)"], color="#1A73E8")

                st.subheader("🔒 Time-Series: Re-Identification Risk Trajectory")
                st.write("Tracks the mathematical safety boundary. If this trajectory approaches the 0.09 ceiling, the synthetic algorithm must be manually retuned.")
                st.line_chart(df_history["Singling Out Risk"], color="#F29900")
            else:
                st.info("Execute the engine at least twice to begin plotting time-series degradation trajectories.")

        except Exception as e:
            st.error(f"Failed to compile Observability Telemetry: {e}")
