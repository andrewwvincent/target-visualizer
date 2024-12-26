import mysql.connector
import sqlite3
import pandas as pd
import json
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_mysql_connection():
    print("Connecting with following parameters:")
    print(f"Host: {os.getenv('MYSQL_HOST')}")
    print(f"User: {os.getenv('MYSQL_USER')}")
    print(f"Database: {os.getenv('MYSQL_DATABASE')}")
    
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE'),
        allow_local_infile=True
    )

def create_tables(mysql_conn):
    cursor = mysql_conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colleges (
            id INT AUTO_INCREMENT PRIMARY KEY,
            NAME VARCHAR(255),
            ADDRESS VARCHAR(255),
            CITY VARCHAR(100),
            STATE VARCHAR(2),
            ZIP VARCHAR(10),
            TELEPHONE VARCHAR(20),
            POPULATION INT,
            COUNTY VARCHAR(100),
            COUNTYFIPS VARCHAR(10),
            WEBSITE VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zip_demographics (
            zip_code VARCHAR(10) PRIMARY KEY,
            median_household_income INT,
            population INT,
            income_bucket VARCHAR(50),
            population_bucket VARCHAR(50)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zip_coordinates (
            zip_code VARCHAR(10) PRIMARY KEY,
            city VARCHAR(100),
            state VARCHAR(2),
            latitude DECIMAL(10, 6),
            longitude DECIMAL(10, 6)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zip_boundaries (
            zip_code VARCHAR(10) PRIMARY KEY,
            geometry TEXT,
            perimeter_meters DECIMAL(10, 6)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_colleges_zip ON colleges(ZIP)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zip_demographics_income ON zip_demographics(income_bucket)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zip_demographics_population ON zip_demographics(population_bucket)")
    
    mysql_conn.commit()

def migrate_data():
    print("Starting data migration...")
    # Connect to both databases
    sqlite_conn = sqlite3.connect('education_demographics.db')
    mysql_conn = get_mysql_connection()
    
    try:
        # Create tables in MySQL
        create_tables(mysql_conn)
        
        # Migrate data from SQLite to MySQL
        tables = ['colleges', 'zip_demographics', 'zip_coordinates', 'zip_boundaries']
        
        for table in tables:
            print(f"Migrating {table}...")
            
            # Read data from SQLite
            df = pd.read_sql_query(f"SELECT * FROM {table}", sqlite_conn)
            print(f"Read {len(df)} rows from SQLite")
            
            if len(df) == 0:
                print(f"No data found in {table}, skipping...")
                continue
                
            # Prepare MySQL cursor
            mysql_cursor = mysql_conn.cursor()
            
            # Generate placeholders for the INSERT statement
            placeholders = ', '.join(['%s'] * len(df.columns))
            columns = ', '.join(f"`{col}`" for col in df.columns)
            
            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i + batch_size]
                values = [tuple(row) for row in batch.values]
                
                try:
                    mysql_cursor.executemany(
                        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                        values
                    )
                    mysql_conn.commit()
                    print(f"Inserted batch of {len(batch)} rows into {table}")
                except Exception as e:
                    print(f"Error inserting batch into {table}: {str(e)}")
                    mysql_conn.rollback()
            
            print(f"Completed migration of {table}")
            
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        print("Closing connections...")
        sqlite_conn.close()
        mysql_conn.close()

if __name__ == "__main__":
    migrate_data()
