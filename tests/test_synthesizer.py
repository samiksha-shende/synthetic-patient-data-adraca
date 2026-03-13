import unittest
import pandas as pd
import numpy as np
from src.synthesizer import DataPreprocessor

class TestDataPreprocessor(unittest.TestCase):
    def setUp(self):
        """Prepare messy datasets to validate the resilience pipeline."""
        
        # Dataset with missing Numerical, String Object, and Datetime fields
        self.messy_data = pd.DataFrame({
            "Age": [25, np.nan, 45, np.nan, 60],
            "Income": [50000, 60000, np.nan, 100000, 110000],
            "Gender": ["M", "F", np.nan, "F", "Unknown"],
            "AdmissionDate": ["2023-01-01", np.nan, "2023-01-15", "Invalid", "2023-02-01"]
        })
        
        self.preprocessor = DataPreprocessor()

    def test_numerical_imputation(self):
        """Assert that missing numerics are imputed specifically with the median value, not dropped."""
        clean_df = self.preprocessor.fit_transform(self.messy_data)
        
        # Median of [25, 45, 60] is 45.0
        self.assertEqual(clean_df["Age"].isnull().sum(), 0, "Age column has leftover NaNs")
        self.assertEqual(clean_df["Age"].iloc[1], 45.0, "Importer failed to use Median strategy for Age!")
        
        # Median of [50000, 60000, 100000, 110000] is 80000.0
        self.assertEqual(clean_df["Income"].isnull().sum(), 0, "Income column has leftover NaNs")
        self.assertEqual(clean_df["Income"].iloc[2], 80000.0, "Importer failed to use Median strategy for Income!")

    def test_categorical_imputation(self):
        """Assert that missing string objects are imputed with the Mode frequency."""
        clean_df = self.preprocessor.fit_transform(self.messy_data)
        
        self.assertEqual(clean_df["Gender"].isnull().sum(), 0, "Gender column has leftover NaNs")
        
        # Mode of ["M", "F", "F", "Unknown"] is "F"
        self.assertEqual(clean_df["Gender"].iloc[2], "F", "Importer failed to use Mode strategy for Categorical String!")

    def test_datetime_standardization(self):
        """Assert that invalid and missing dates are coerced and back-filled with the minimum date."""
        clean_df = self.preprocessor.fit_transform(self.messy_data)
        
        self.assertEqual(clean_df["AdmissionDate"].isnull().sum(), 0, "AdmissionDate column has leftover NaNs")
        
        # Earliest date is "2023-01-01"
        self.assertEqual(str(clean_df["AdmissionDate"].iloc[1])[:10], "2023-01-01")
        self.assertEqual(str(clean_df["AdmissionDate"].iloc[3])[:10], "2023-01-01")

if __name__ == '__main__':
    unittest.main()
