import sqlite3
import pandas as pd

def execute_query(query):
    """Execute an SQL query and return results as a pandas DataFrame."""
    conn = sqlite3.connect('education_demographics.db')
    try:
        # Execute query and convert to DataFrame for nice display
        df = pd.read_sql_query(query, conn)
        print("\nQuery Results:")
        print(df)
        print(f"\nTotal rows: {len(df)}")
        return df
    finally:
        conn.close()

# Example queries to explore the database
queries = {
    "show_tables": """
        SELECT name FROM sqlite_master 
        WHERE type='table';
    """,
    "sample_zip_demographics": """
        SELECT * FROM zip_demographics 
        LIMIT 5;
    """,
    "sample_colleges": """
        SELECT * FROM colleges 
        LIMIT 5;
    """,
    "sample_zip_boundaries": """
        SELECT * FROM zip_boundaries 
        LIMIT 5;
    """,
    "sample_zip_coordinates": """
        SELECT * FROM zip_coordinates 
        LIMIT 5;
    """
}

if __name__ == "__main__":
    print("Available tables in the database:")
    execute_query(queries["show_tables"])
    
    print("\nSample data from each table:")
    for query_name in ["sample_zip_demographics", "sample_colleges", "sample_zip_boundaries", "sample_zip_coordinates"]:
        print(f"\n{query_name.replace('_', ' ').title()}:")
        execute_query(queries[query_name])
