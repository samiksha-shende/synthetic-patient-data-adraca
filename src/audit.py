import json
import os
from datetime import datetime
import logging


class AuditLogger:
    """Handles HIPAA/GDPR compliance audit trailing for the Sythetic Engine."""

    def __init__(self, log_dir="./logs"):
        self.log_dir = log_dir
        self.log_file = os.path.join(self.log_dir, "audit.jsonl")

        # Ensure log directory exists natively (or inside container)
        os.makedirs(self.log_dir, exist_ok=True)

    def log_run(self, epsilon, num_input_rows, num_input_cols, num_output_rows,
                singling_out_risk, exact_match_rate, utility_score_ks, utility_score_kl, utility_score_hellinger, is_compliant):
        """Append a JSON record with privacy metrics to the audit log."""

        record = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "parameters": {
                "epsilon_privacy_budget": epsilon,
                "input_dataset_shape": [num_input_rows, num_input_cols],
                "target_output_rows": num_output_rows
            },
            "metrics": {
                "singling_out_risk": round(singling_out_risk, 5),
                "exact_match_rate_pct": exact_match_rate,
                "utility_score_ks_complement": round(utility_score_ks, 5),
                "utility_score_kl_divergence": round(utility_score_kl, 5),
                "utility_score_hellinger": round(utility_score_hellinger, 5)
            },
            "compliance": {
                "passed_ema_policy_0070": is_compliant
            }
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
            logging.info(f"Audit log securely written to {self.log_file}")
        except Exception as e:
            logging.error(f"Failed to write audit log: {e}")
