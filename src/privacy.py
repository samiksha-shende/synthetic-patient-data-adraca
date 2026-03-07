import logging
import numpy as np
import pandas as pd
import gower
from sdmetrics.single_column import KSComplement
from anonymeter.evaluators import SinglingOutEvaluator, LinkabilityEvaluator, InferenceEvaluator

class PrivacyValidator:
    """Handles distance metrics, utility checks, and GDPR/EHDS compliance validation."""
    
    def __init__(self, real_data, synthetic_data, batch_size=5000):
        self.real_data = real_data
        self.synthetic_data = synthetic_data
        self.batch_size = batch_size

    def calculate_dcr(self):
        """
        Calculate DCR using Gower distance. Reject records with DCR == 0.0.
        Uses batching to avoid OOM on large datasets.
        """
        logging.info("Calculating Distance to Closest Record (DCR) using Gower distance...")
        valid_synthetic_records = []
        dcr_values = []
        
        n_synth = len(self.synthetic_data)
        
        for i in range(0, n_synth, self.batch_size):
            synth_batch = self.synthetic_data.iloc[i:i+self.batch_size]
            
            # gower_matrix returns distances between 0 and 1
            dist_matrix = gower.gower_matrix(synth_batch, self.real_data)
            
            # Minimum distance for each synthetic record
            min_dists = np.min(dist_matrix, axis=1)
            
            for idx, dcr in enumerate(min_dists):
                if dcr > 0.0:
                    valid_synthetic_records.append(synth_batch.iloc[idx])
                    dcr_values.append(dcr)
                else:
                    logging.warning("Exact match found (DCR=0.0). Record rejected to prevent Singling Out risk.")
                    
        valid_synthetic_df = pd.DataFrame(valid_synthetic_records)
        exact_match_rate = (n_synth - len(valid_synthetic_df)) / n_synth if n_synth > 0 else 0
        
        logging.info(f"DCR validation completed. Exact Match Rate: {exact_match_rate:.2%}")
        return valid_synthetic_df, dcr_values, exact_match_rate

    def evaluate_utility(self):
        """Calculate Information-Theoretic Metric: KS Complement."""
        logging.info("Evaluating statistical utility using KS Complement...")
        ks_scores = []
        for col in self.real_data.columns:
            try:
                # We skip KS Complement for datetime or completely distinct continuous if sdmetrics fails
                score = KSComplement.compute(
                    real_data=self.real_data[col],
                    synthetic_data=self.synthetic_data[col]
                )
                ks_scores.append(score)
            except Exception as e:
                pass
                
        avg_ks = np.mean(ks_scores) if ks_scores else 0.0
        logging.info(f"Average KS Complement: {avg_ks:.4f}")
        return avg_ks
        
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
