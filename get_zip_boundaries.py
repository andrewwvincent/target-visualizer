import geopandas as gpd
import pandas as pd
import sqlite3
import requests
import zipfile
import io
import os
from datetime import datetime
from shapely.geometry import shape, mapping
import json

def log_progress(message):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def download_and_extract_zcta_shapefile():
    """Download and extract ZCTA shapefile from Census TIGER/Line"""
    log_progress("Downloading ZCTA shapefile from Census...")
    
    # 2023 ZCTA shapefile URL
    url = "https://www2.census.gov/geo/tiger/TIGER2023/ZCTA520/tl_2023_us_zcta520.zip"
    
    try:
        # Download the zip file
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to download shapefile: {response.status_code}")
        
        import shutil
        
        # Force remove temp directory if it exists
        if os.path.exists('temp'):
            shutil.rmtree('temp', ignore_errors=True)
        
        # Create a temporary directory for the files
        os.makedirs('temp', exist_ok=True)
        
        # Save and extract the zip file
        zip_path = 'temp/zcta.zip'
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Extract the files
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall('temp')
        
        log_progress("Successfully downloaded and extracted ZCTA shapefile")
        return 'temp/tl_2023_us_zcta520.shp'
    
    except Exception as e:
        log_progress(f"Error downloading shapefile: {str(e)}")
        return None

def create_zip_boundaries_table():
    """Create a table with ZIP code boundary data"""
    conn = None
    try:
        # Download and read the shapefile
        shapefile_path = download_and_extract_zcta_shapefile()
        if not shapefile_path:
            return
        
        log_progress("Reading shapefile...")
        # Use GeoPandas to read the shapefile
        gdf = gpd.read_file(shapefile_path, engine='pyogrio')
        
        # Connect to the database
        conn = sqlite3.connect('education_demographics.db')
        
        # Get existing ZIP codes from demographics and coordinates tables
        log_progress("Getting existing ZIP codes from database...")
        existing_zips_df = pd.read_sql_query("""
            SELECT DISTINCT d.zip_code, c.latitude, c.longitude
            FROM zip_demographics d
            JOIN zip_coordinates c ON d.zip_code = c.zip_code
            WHERE d.income_bucket != 'Under $100k'
        """, conn)
        
        # Filter the geodataframe to only include our ZIP codes
        log_progress("Filtering boundaries to match our ZIP codes...")
        gdf['ZCTA5CE20'] = gdf['ZCTA5CE20'].astype(str).str.zfill(5)
        filtered_gdf = gdf[gdf['ZCTA5CE20'].isin(existing_zips_df['zip_code'])]
        
        # Create a new table for the boundaries
        log_progress("Creating ZIP boundaries table...")
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS zip_boundaries (
            zip_code TEXT PRIMARY KEY,
            geometry TEXT,  -- GeoJSON format
            area_sq_meters REAL,
            perimeter_meters REAL
        )
        ''')
        
        # Create an index on zip_code if it doesn't exist
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_zip_boundaries_zip ON zip_boundaries(zip_code)')
        
        # Convert geometries to GeoJSON and calculate area/perimeter
        log_progress(f"Processing {len(filtered_gdf)} ZIP code boundaries...")
        records = []
        for idx, row in filtered_gdf.iterrows():
            # Convert geometry to GeoJSON
            geojson = json.dumps(mapping(row.geometry))
            # Calculate area and perimeter
            area = row.geometry.area
            perimeter = row.geometry.length
            records.append((row['ZCTA5CE20'], geojson, area, perimeter))
        
        # Insert the data
        cursor.executemany(
            'INSERT OR REPLACE INTO zip_boundaries (zip_code, geometry, area_sq_meters, perimeter_meters) VALUES (?, ?, ?, ?)',
            records
        )
        
        conn.commit()
        log_progress(f"Successfully added {len(records)} ZIP code boundaries to database")
        
    except Exception as e:
        log_progress(f"Error creating boundaries table: {str(e)}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()
        # Clean up temporary files
        if os.path.exists('temp'):
            import shutil
            shutil.rmtree('temp')
            log_progress("Cleaned up temporary files")

if __name__ == '__main__':
    create_zip_boundaries_table()
