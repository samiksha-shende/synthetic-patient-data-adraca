import unittest
import pandas as pd
from src.privacy import PrivacyValidator


class TestPrivacyValidator(unittest.TestCase):
    def setUp(self):
        """Prepare sample datasets for privacy testing."""
        # Simple sample dataset
        self.raw_data = pd.DataFrame({
            "Age": [25, 30, 45, 60],
            "Income": [50000, 60000, 80000, 100000],
            "Gender": ["M", "F", "M", "F"]
        })

    def test_exact_match_detected(self):
        """If the synthetic data is identical to the real data, the match rate must be 1.0 (100%)."""

        # Identical synthetic dataset
        synth_data = self.raw_data.copy()

        validator = PrivacyValidator(self.raw_data, synth_data)
        clean_synth, dcrs, exact_match_rate = validator.calculate_dcr()

        # The penalty for a perfect match is that exact_match_rate must equal 1.0 (100% overlap)
        self.assertEqual(exact_match_rate, 1.0, "Exact match rate should be 1.0 for identical datasets!")

        # The privacy engine must drop ALL exact matching rows, meaning clean_synth is completely empty
        self.assertEqual(len(clean_synth), 0, "Validator failed to drop exact matching rows from the synthetic output!")

    def test_reidentification_risk_calculation(self):
        """Test the singling out probability risk."""
        # A semi-anonymized dataset with some slight variance
        synth_data = pd.DataFrame({
            "Age": [26, 31, 44, 59],
            "Income": [50100, 60200, 79000, 99000],
            "Gender": ["M", "F", "M", "F"]
        })

        validator = PrivacyValidator(self.raw_data, synth_data)
        _, dcrs, _ = validator.calculate_dcr()

        risk_score = validator.evaluate_reidentification_risk()

        # For completely distinct, small 4-row datasets, risk score is a
        # deterministic probability based on EMA Policy 0070
        self.assertIsInstance(risk_score, float)
        self.assertGreaterEqual(risk_score, 0.0)
        self.assertLessEqual(risk_score, 1.0)

    def test_utility_score_format(self):
        """Test the Kolmogorov-Smirnov statistical feature validation."""
        synth_data = self.raw_data.copy()
        # Change 1 value to ensure it's not dropped by exact match
        synth_data.at[0, "Age"] = 26

        validator = PrivacyValidator(self.raw_data, synth_data)

        utility = validator.evaluate_utility()

        # KS Complement utility must be between 0.0 (total failure) and 1.0 (perfect statistical match)
        self.assertIsInstance(utility, float)
        self.assertGreaterEqual(utility, 0.0)
        self.assertLessEqual(utility, 1.0)


if __name__ == '__main__':
    unittest.main()
