import sqlite3
import pandas as pd
import requests
import json
import sys
import time
from datetime import datetime

def log_progress(message):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

# Create database connection
conn = sqlite3.connect('education_demographics.db')
cursor = conn.cursor()

def create_colleges_table():
    log_progress("Creating colleges table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS colleges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        zip TEXT,
        telephone TEXT,
        population INTEGER,
        county TEXT,
        countyfips TEXT,
        country TEXT,
        latitude REAL,
        longitude REAL,
        website TEXT
    )
    ''')
    
    # Read CSV file
    log_progress("Reading college data from CSV...")
    df = pd.read_csv('all-college-data.csv')
    
    # Insert data into the table
    log_progress(f"Inserting {len(df)} college records into database...")
    df.to_sql('colleges', conn, if_exists='replace', index=False)
    log_progress("College data import complete")

def create_zip_coordinates_table():
    log_progress("Creating ZIP coordinates table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS zip_coordinates (
        zip_code TEXT PRIMARY KEY,
        city TEXT,
        state TEXT,
        latitude REAL,
        longitude REAL
    )
    ''')
    
    # Read ZIP coordinates CSV file
    log_progress("Reading ZIP coordinates from CSV...")
    df = pd.read_csv('ZIP-lat-long.csv')
    
    # Rename columns and select needed ones
    df = df.rename(columns={
        'STD_ZIP5': 'zip_code',
        'USPS_ZIP_PREF_CITY': 'city',
        'USPS_ZIP_PREF_STATE': 'state',
        'LATITUDE': 'latitude',
        'LONGITUDE': 'longitude'
    })
    
    # Ensure ZIP codes have leading zeros
    df['zip_code'] = df['zip_code'].astype(str).str.zfill(5)
    
    # Select only the columns we want
    df = df[['zip_code', 'city', 'state', 'latitude', 'longitude']]
    
    # Insert data into the table
    log_progress(f"Inserting {len(df)} ZIP coordinate records into database...")
    df.to_sql('zip_coordinates', conn, if_exists='replace', index=False)
    log_progress("ZIP coordinates import complete")

def download_census_data(api_key):
    """Download complete Census dataset for all ZIP codes"""
    start_time = time.time()
    log_progress("Starting Census data download...")
    
    base_url = "https://api.census.gov/data/2021/acs/acs5"
    params = {
        "get": "B19013_001E,B01003_001E,NAME", # Median income, Population, Name
        "for": "zip code tabulation area:*",
        "key": api_key
    }
    
    try:
        log_progress("Requesting demographic data from Census API...")
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            log_progress(f"Error downloading Census data: {response.status_code}")
            log_progress(f"Response: {response.text}")
            return None
            
        data = response.json()
        log_progress(f"Received data for {len(data)-1} ZIP codes")
        
        # Convert to DataFrame
        log_progress("Converting Census data to DataFrame...")
        columns = ['median_household_income', 'population', 'name', 'zip_code']
        df = pd.DataFrame(data[1:], columns=columns)
        
        # Extract ZIP code and ensure 5 digits with leading zeros
        df['zip_code'] = df['zip_code'].str.zfill(5)
        
        # Convert data types
        log_progress("Converting data types...")
        df['median_household_income'] = pd.to_numeric(df['median_household_income'], errors='coerce')
        df['population'] = pd.to_numeric(df['population'], errors='coerce')
        
        # Select final columns
        result_df = df[['zip_code', 'median_household_income', 'population']]
        
        elapsed_time = time.time() - start_time
        log_progress(f"Data collection completed in {elapsed_time:.1f} seconds")
        
        return result_df
        
    except Exception as e:
        log_progress(f"Error downloading Census data: {str(e)}")
        return None

def get_income_bucket(income):
    """Categorize income into buckets"""
    if pd.isna(income):
        return 'Unknown'
    elif income < 100000:
        return 'Under $100k'
    elif income < 125000:
        return '$100k-$125k'
    elif income < 150000:
        return '$125k-$150k'
    elif income < 175000:
        return '$150k-$175k'
    elif income < 200000:
        return '$175k-$200k'
    elif income < 250000:
        return '$200k-$250k'
    else:
        return '$250k+'

def get_population_bucket(population):
    """Categorize population into buckets"""
    if pd.isna(population):
        return 'Unknown'
    elif population < 1000:
        return 'Under 1,000'
    elif population < 5000:
        return '1,000-5,000'
    elif population < 10000:
        return '5,000-10,000'
    elif population < 25000:
        return '10,000-25,000'
    elif population < 40000:
        return '25,000-40,000'
    else:
        return '40,000+'

def create_zip_demographics_table(census_api_key):
    log_progress("Creating ZIP demographics table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS zip_demographics (
        zip_code TEXT PRIMARY KEY,
        median_household_income INTEGER,
        population INTEGER,
        income_bucket TEXT,
        population_bucket TEXT
    )
    ''')
    
    # Download complete Census dataset
    df = download_census_data(census_api_key)
    if df is None:
        log_progress("Failed to download Census data")
        return
        
    log_progress(f"Processing {len(df)} ZIP codes...")
    
    # Add bucketed columns
    log_progress("Creating income and population buckets...")
    df['income_bucket'] = df['median_household_income'].apply(get_income_bucket)
    df['population_bucket'] = df['population'].apply(get_population_bucket)
    
    # Insert data into the table
    start_time = time.time()
    log_progress("Inserting data into database...")
    df.to_sql('zip_demographics', conn, if_exists='replace', index=False)
    elapsed_time = time.time() - start_time
    log_progress(f"Database insert completed in {elapsed_time:.1f} seconds")
    log_progress("ZIP demographics table created successfully!")
    
    # Print bucket distribution
    log_progress("\nIncome Bucket Distribution:")
    income_dist = df['income_bucket'].value_counts()
    for bucket, count in income_dist.items():
        log_progress(f"- {bucket}: {count:,} ZIP codes ({count/len(df)*100:.1f}%)")
        
    log_progress("\nPopulation Bucket Distribution:")
    pop_dist = df['population_bucket'].value_counts()
    for bucket, count in pop_dist.items():
        log_progress(f"- {bucket}: {count:,} ZIP codes ({count/len(df)*100:.1f}%)")

def summarize_database():
    """Print summary of all tables in the database"""
    log_progress("\nDatabase Summary:")
    
    # Get colleges table info
    cursor.execute("SELECT COUNT(*) FROM colleges")
    college_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA table_info(colleges)")
    college_fields = [field[1] for field in cursor.fetchall()]
    log_progress(f"\nColleges Table:")
    log_progress(f"- {college_count} rows")
    log_progress(f"- Fields: {', '.join(college_fields)}")
    
    # Get ZIP demographics table info
    cursor.execute("SELECT COUNT(*) FROM zip_demographics")
    demographics_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA table_info(zip_demographics)")
    demographics_fields = [field[1] for field in cursor.fetchall()]
    log_progress(f"\nZIP Demographics Table:")
    log_progress(f"- {demographics_count} rows")
    log_progress(f"- Fields: {', '.join(demographics_fields)}")
    
    # Get ZIP coordinates table info
    cursor.execute("SELECT COUNT(*) FROM zip_coordinates")
    coordinates_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA table_info(zip_coordinates)")
    coordinates_fields = [field[1] for field in cursor.fetchall()]
    log_progress(f"\nZIP Coordinates Table:")
    log_progress(f"- {coordinates_count} rows")
    log_progress(f"- Fields: {', '.join(coordinates_fields)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python database_setup.py <census_api_key>")
        sys.exit(1)
        
    census_api_key = sys.argv[1]
    
    total_start_time = time.time()
    log_progress("Starting database setup...")
    
    # Create all tables
    create_colleges_table()
    create_zip_coordinates_table()
    create_zip_demographics_table(census_api_key)
    
    # Print database summary
    summarize_database()
    
    total_elapsed_time = time.time() - total_start_time
    log_progress(f"\nDatabase setup completed in {total_elapsed_time:.1f} seconds")
    conn.close()
