import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('education_demographics.db')

# Check income bucket distribution
print("\nIncome bucket distribution:")
df = pd.read_sql_query("SELECT income_bucket, COUNT(*) as count FROM zip_demographics GROUP BY income_bucket", conn)
print(df)

print("\nPopulation bucket distribution:")
df = pd.read_sql_query("SELECT population_bucket, COUNT(*) as count FROM zip_demographics GROUP BY population_bucket", conn)
print(df)

# Check if we're missing any ZIP codes
print("\nChecking for missing ZIP codes:")
df = pd.read_sql_query("""
    SELECT COUNT(DISTINCT zc.zip_code) as total_zips,
           COUNT(DISTINCT zd.zip_code) as zips_with_demographics
    FROM zip_coordinates zc
    LEFT JOIN zip_demographics zd ON zc.zip_code = zd.zip_code
""", conn)
print(df)

conn.close()
