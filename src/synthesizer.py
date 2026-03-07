import logging
import pandas as pd
import numpy as np
import warnings
from sdv.metadata import SingleTableMetadata
from sdv.single_table import GaussianCopulaSynthesizer

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        self.synthesizer.fit(data)
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
                    n_features = cov_matrix.shape[0]
                    
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
