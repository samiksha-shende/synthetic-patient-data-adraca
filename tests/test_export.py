import pytest
import pandas as pd
import sqlite3
import os
from src.export import export_to_sqlite

class TestSQLiteExportIntegration:
    """
    Test suite for validating the secure, air-gapped export of synthetic patients to an SQLite database.
    """

    @pytest.fixture
    def sample_data(self):
        """Creates a mock synthetic patient DataFrame."""
        return pd.DataFrame({
            "patient_id": [1, 2, 3],
            "age": [45, 62, 31],
            "diagnosis_code": ["E11", "I10", "J45"]
        })

    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Provides a temporary, isolated database path for safe testing without mutating production data."""
        return os.path.join(tmp_path, "synthetic_test.db")

    def test_successful_database_creation_and_insertion(self, sample_data, test_db_path):
        """
        Validates that export_to_sqlite gracefully creates the database file
        and correctly inserts all rows from the DataFrame.
        """
        table_name = "test_patients"
        
        # Execute the export pipeline
        success = export_to_sqlite(sample_data, test_db_path, table_name)
        
        # Assert the function returned True
        assert success is True
        
        # Assert the database file was physically generated on disk
        assert os.path.exists(test_db_path)
        
        # Connect to the SQLite DB and mathematically verify the payload
        conn = sqlite3.connect(test_db_path)
        result_df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        assert len(result_df) == 3
        assert list(result_df.columns) == ["patient_id", "age", "diagnosis_code"]
        assert result_df["diagnosis_code"].iloc[0] == "E11"

    def test_append_existing_table(self, sample_data, test_db_path):
        """
        Adracas generates continuous data batches. This test ensures the SQLite exporter
        safely 'appends' new batches to existing tables without dropping previous records.
        """
        table_name = "test_patients"
        
        # Run export twice
        export_to_sqlite(sample_data, test_db_path, table_name)
        success = export_to_sqlite(sample_data, test_db_path, table_name)
        
        assert success is True
        
        conn = sqlite3.connect(test_db_path)
        result_df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        # 3 initial rows + 3 appended rows = 6 total rows
        assert len(result_df) == 6
