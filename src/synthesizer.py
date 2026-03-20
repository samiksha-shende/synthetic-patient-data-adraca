import logging
import pandas as pd
import numpy as np
import warnings
from sdv.metadata import SingleTableMetadata
from sdv.single_table import GaussianCopulaSynthesizer

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataPreprocessor:
    """Handles missing values and complex datetimes to ensure model stability."""

    def __init__(self):
        self.numerical_imputers = {}
        self.categorical_imputers = {}

    def fit_transform(self, df):
        logging.info("Starting advanced data preprocessing...")
        df_clean = df.copy()

        for col in df_clean.columns:
            # 1. Handle Missing Numerical Values
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                if df_clean[col].isnull().any():
                    median_val = df_clean[col].median()
                    # Fallback to 0 if median is nan
                    if pd.isna(median_val):
                        median_val = 0
                    self.numerical_imputers[col] = median_val
                    df_clean[col] = df_clean[col].fillna(median_val)
                    logging.info(f"Imputed missing numericals in '{col}' with median: {median_val}")

            # 2. Handle Missing Categorical Strings
            else:
                if df_clean[col].isnull().any():
                    # Check if column looks like a datetime string
                    try:
                        parsed = pd.to_datetime(df_clean[col].dropna().head(10), errors='coerce')
                        # If more than half parse successfully, assume it is meant to be a date column
                        is_date = (parsed.notnull().mean() > 0.5)
                    except Exception:
                        is_date = False

                    if is_date:
                        # Attempt to parse dates uniformly
                        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
                        # Fill bad dates with earliest date
                        min_date = df_clean[col].min()
                        self.categorical_imputers[col] = min_date
                        df_clean[col] = df_clean[col].fillna(min_date)
                        logging.info(f"Standardized and imputed datetimes in '{col}' with min date.")
                    else:
                        mode_val = df_clean[col].mode()
                        if not mode_val.empty:
                            fill_val = mode_val[0]
                        else:
                            fill_val = "Unknown"

                        self.categorical_imputers[col] = fill_val
                        df_clean[col] = df_clean[col].fillna(fill_val)
                        logging.info(f"Imputed missing categoricals in '{col}' with mode: '{fill_val}'")

        logging.info("Data preprocessing completed successfully.")
        return df_clean

    def transform(self, df):
        """Apply the learned imputation map if evaluating a new holdout dataset."""
        df_clean = df.copy()
        for col, median_val in self.numerical_imputers.items():
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna(median_val)
        for col, fill_val in self.categorical_imputers.items():
            if col in df_clean.columns:
                if pd.api.types.is_datetime64_any_dtype(pd.Series([fill_val])):
                    df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce').fillna(fill_val)
                else:
                    df_clean[col] = df_clean[col].fillna(fill_val)
        return df_clean


class DataIngestor:
    """Handles data ingestion and metadata inference."""

    @staticmethod
    def load_data(file_path):
        logging.info(f"Ingesting data from {file_path}")
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith('.parquet'):
            return pd.read_parquet(file_path)
        else:
            raise ValueError("Unsupported format. Use CSV or Parquet.")

    @staticmethod
    def infer_metadata(data):
        logging.info("Inferring metadata for the dataset...")
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(data=data)
        # Quasi-identifier tagging could be manually added here based on columns
        return metadata


class AdracaSynthesizer:
    """Wraps SDV GaussianCopulaSynthesizer with Differential Privacy noise injection."""

    def __init__(self, metadata, epsilon=1.0):
        self.metadata = metadata
        self.epsilon = epsilon
        self.synthesizer = GaussianCopulaSynthesizer(self.metadata)

    def fit(self, data):
        logging.info("Training Gaussian Copula Synthesizer...")
        self.preprocessor = DataPreprocessor()
        clean_data = self.preprocessor.fit_transform(data)

        # We must re-infer metadata since preprocessing might have casted types
        self.metadata = DataIngestor.infer_metadata(clean_data)
        self.synthesizer = GaussianCopulaSynthesizer(self.metadata)

        self.synthesizer.fit(clean_data)
        self._inject_laplace_noise()

    def _inject_laplace_noise(self):
        """
        Injects Laplacian noise into the covariance matrix of the Gaussian Copula
        to ensure epsilon-Differential Privacy.
        """
        try:
            # The SDV synthesizer contains the fitted model under _model
            if hasattr(self.synthesizer, '_model') and self.synthesizer._model is not None:
                copula = self.synthesizer._model

                # Check for the covariance matrix
                if hasattr(copula, 'covariance'):
                    cov_matrix = copula.covariance
                    # DP calibration: add noise proportional to 1/epsilon
                    # Assuming bounded sensitivity.
                    noise_scale = 1.0 / (self.epsilon + 1e-6)
                    noise = np.random.laplace(loc=0.0, scale=noise_scale, size=cov_matrix.shape)
                    noisy_cov = cov_matrix + noise

                    # Ensure positive semi-definite and symmetric
                    noisy_cov = (noisy_cov + noisy_cov.T) / 2.0
                    eigvals, eigvecs = np.linalg.eigh(noisy_cov)
                    eigvals[eigvals < 0] = 1e-6
                    noisy_cov = eigvecs @ np.diag(eigvals) @ eigvecs.T

                    copula.covariance = noisy_cov
                    logging.info(f"Injected Laplacian noise into covariance matrix (epsilon={self.epsilon})")
                else:
                    logging.warning("Covariance matrix not directly accessible. DP noise skipped.")
            else:
                logging.warning("Synthesizer model not available. Fit might have failed.")
        except Exception as e:
            logging.error(f"Error injecting DP noise: {e}")

    def sample(self, num_rows):
        logging.info(f"Sampling {num_rows} synthetic records...")
        return self.synthesizer.sample(num_rows=num_rows)
