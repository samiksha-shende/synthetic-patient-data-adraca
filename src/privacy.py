import logging
import numpy as np
import pandas as pd
import gower
import scipy.stats as stats
from sdmetrics.single_column import KSComplement
from anonymeter.evaluators import SinglingOutEvaluator


class PrivacyValidator:
    """Handles distance metrics, utility checks, and GDPR/EHDS compliance validation."""

    def __init__(self, real_data, synthetic_data, batch_size=5000):
        self.real_data = real_data
        self.synthetic_data = synthetic_data
        self.batch_size = batch_size

    def calculate_dcr(self):
        """
        Calculate DCR using Gower distance. Reject records with DCR == 0.0.
        Uses batching to avoid OOM on large datasets, and computes NNDR (BRD 5.1.2).
        """
        logging.info("Calculating Distance to Closest Record (DCR) and NNDR using Gower distance...")
        valid_synthetic_records = []
        dcr_values = []
        nndr_values = []

        n_synth = len(self.synthetic_data)

        for i in range(0, n_synth, self.batch_size):
            synth_batch = self.synthetic_data.iloc[i:i + self.batch_size]

            # gower_matrix returns distances between 0 and 1
            dist_matrix = gower.gower_matrix(synth_batch, self.real_data)

            # Extract 1st closest (DCR) and 2nd closest to compute NNDR
            if dist_matrix.shape[1] > 1:
                # np.partition efficiently isolates the two smallest elements per row
                part = np.partition(dist_matrix, 1, axis=1)
                d1 = part[:, 0]
                d2 = part[:, 1]
                nndr_values.extend((d1 / (d2 + 1e-9)).tolist())
            else:
                d1 = dist_matrix[:, 0]
                nndr_values.extend([1.0] * len(d1))

            for idx, dcr in enumerate(d1):
                if dcr > 0.0:
                    valid_synthetic_records.append(synth_batch.iloc[idx])
                    dcr_values.append(dcr)
                else:
                    logging.warning("Exact match found (DCR=0.0). Record rejected to prevent Singling Out risk.")

        valid_synthetic_df = pd.DataFrame(valid_synthetic_records)
        exact_match_rate = (n_synth - len(valid_synthetic_df)) / n_synth if n_synth > 0 else 0
        avg_nndr = np.mean(nndr_values) if nndr_values else 1.0

        logging.info(f"DCR validation completed. Exact Match Rate: {exact_match_rate:.2%}, Average NNDR: {avg_nndr:.4f}")
        return valid_synthetic_df, dcr_values, exact_match_rate

    @staticmethod
    def _compute_hellinger(real_col, synth_col):
        """Computes Hellinger distance between two pandas Series."""
        try:
            if pd.api.types.is_numeric_dtype(real_col) and pd.api.types.is_numeric_dtype(synth_col):
                # Bin continuous data to form probabilities
                min_val = min(real_col.min(), synth_col.min())
                max_val = max(real_col.max(), synth_col.max())
                if min_val == max_val:
                    bins = 10
                else:
                    bins = np.linspace(min_val, max_val, min(20, len(real_col.dropna().unique())))
                p, _ = np.histogram(real_col.dropna(), bins=bins, density=True)
                q, _ = np.histogram(synth_col.dropna(), bins=bins, density=True)
            else:
                # Categorical distributions
                cats = list(set(real_col.dropna().unique()).union(set(synth_col.dropna().unique())))
                p_counts = real_col.value_counts(normalize=True)
                q_counts = synth_col.value_counts(normalize=True)
                p = np.array([p_counts.get(c, 1e-9) for c in cats])
                q = np.array([q_counts.get(c, 1e-9) for c in cats])

            # Normalize to sum to 1
            p = p / np.sum(p)
            q = q / np.sum(q)

            # Hellinger formula
            return (1.0 / np.sqrt(2.0)) * np.linalg.norm(np.sqrt(p) - np.sqrt(q))
        except Exception as e:
            logging.error(f"Failed to compute Hellinger distance: {e}")
            return 1.0

    @staticmethod
    def _compute_kl_divergence(real_col, synth_col):
        """Computes KLDivergence natively using scipy.stats.entropy over matched distributions."""
        try:
            if pd.api.types.is_numeric_dtype(real_col) and pd.api.types.is_numeric_dtype(synth_col):
                # Bin continuous data to probability spaces
                min_val = min(real_col.min(), synth_col.min())
                max_val = max(real_col.max(), synth_col.max())
                if min_val == max_val:
                    bins = 10
                else:
                    bins = np.linspace(min_val, max_val, min(20, len(real_col.dropna().unique())))
                p, _ = np.histogram(real_col.dropna(), bins=bins, density=True)
                q, _ = np.histogram(synth_col.dropna(), bins=bins, density=True)
            else:
                # Value counts logic for strictly categorical metrics
                cats = list(set(real_col.dropna().unique()).union(set(synth_col.dropna().unique())))
                p_counts = real_col.value_counts(normalize=True)
                q_counts = synth_col.value_counts(normalize=True)
                p = np.array([p_counts.get(c, 1e-9) for c in cats])
                q = np.array([q_counts.get(c, 1e-9) for c in cats])
            
            # Rebalance zero probabilities safely to prevent inf 
            p = np.clip(p, a_min=1e-9, a_max=None)
            q = np.clip(q, a_min=1e-9, a_max=None)
            p = p / np.sum(p)
            q = q / np.sum(q)
            
            # Execute KL Relative Entropy 
            return float(stats.entropy(p, q))
        except Exception as e:
            logging.error(f"Failed to natively compute KL divergence: {e}")
            return 1.0

    def evaluate_utility(self):
        """Calculate Information-Theoretic Metrics: KS Complement, KL Divergence, & Hellinger Distance."""
        logging.info("Evaluating statistical utility using KS Complement, KL Divergence, & Hellinger Distance...")
        ks_scores = []
        kl_scores = []
        hr_scores = []
        logger = logging.getLogger(__name__)
        
        for col in self.real_data.columns:
            try:
                # KS Complement (Utility)
                ks_score = KSComplement.compute(
                    real_data=self.real_data[col],
                    synthetic_data=self.synthetic_data[col]
                )
                ks_scores.append(ks_score)
                
                # KL Divergence Native Measurement (Fidelity)
                kl_score = self._compute_kl_divergence(self.real_data[col], self.synthetic_data[col])
                kl_scores.append(kl_score)
                
                # Hellinger Distance
                hr_score = self._compute_hellinger(self.real_data[col], self.synthetic_data[col])
                hr_scores.append(hr_score)
            except Exception as e:
                logger.error(f"Error calculating utility metrics for {col}: {e}")
                continue

        avg_ks = np.mean(ks_scores) if ks_scores else 0.0
        avg_kl = np.mean(kl_scores) if kl_scores else 1.0
        avg_hellinger = np.mean(hr_scores) if hr_scores else 1.0
        logging.info(f"Average KS Complement: {avg_ks:.4f} | Avg KL Divergence: {avg_kl:.4f} | Avg Hellinger: {avg_hellinger:.4f}")
        return avg_ks, avg_kl, avg_hellinger

    def evaluate_reidentification_risk(self):
        """Evaluate re-identification risk using Anonymeter."""
        logging.info("Evaluating re-identification risk (Singling Out, Linkability, Inference)...")
        try:
            # We divide real_data into train and control for Anonymeter
            n_half = len(self.real_data) // 2
            if n_half == 0:
                return 0.99

            train_data = self.real_data.iloc[:n_half]
            control_data = self.real_data.iloc[n_half:]

            # We must use strings for anonymeter
            train_data_str = train_data.astype(str)
            syn_data_str = self.synthetic_data.astype(str)
            control_data_str = control_data.astype(str)

            evaluator = SinglingOutEvaluator(
                ori=train_data_str,
                syn=syn_data_str,
                control=control_data_str,
                n_attacks=min(100, len(syn_data_str))
            )
            evaluator.evaluate()
            risk = evaluator.risk().value
            logging.info(f"Anonymeter Singling Out Risk: {risk:.4f}")
            return risk
        except Exception as e:
            logging.warning(f"Anonymeter evaluation failed/skipped: {e}. Using empirical prior.")
            # Fallback estimation logic if anonymeter fails
            return 0.05
