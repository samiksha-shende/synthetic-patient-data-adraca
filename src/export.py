import pandas as pd
import logging
from sqlalchemy import create_engine
import os


def export_to_sqlite(df: pd.DataFrame, db_path: str, table_name: str) -> bool:
    """
    Exports the generated synthetic DataFrame to a local, offline SQLite database.
    This maintains the strict network-isolated airgap while allowing relational querying.

    Args:
        df: The pandas DataFrame containing the synthetic patients.
        db_path: The absolute path to the SQLite database file (e.g. /app/data/synthetic_patients.db)
        table_name: The name of the table to insert the records into.

    Returns:
        True if the export succeeds, False otherwise.
    """
    try:
        # Create the directory if it doesn't already exist in the mounted volume
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize the SQLAlchemy SQLite engine
        engine = create_engine(f'sqlite:///{db_path}')

        # Push the DataFrame to the database (append if it exists, replace if needed)
        # Using 'append' allows continuous data generation batches to safely stack up
        df.to_sql(name=table_name, con=engine, if_exists='append', index=False)

        logging.info(f"Successfully exported {len(df)} rows to SQLite table '{table_name}' at {db_path}.")
        return True

    except Exception as e:
        logging.error(f"Failed to export data to SQLite database: {e}")
        return False
