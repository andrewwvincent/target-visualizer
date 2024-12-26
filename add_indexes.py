import sqlite3

conn = sqlite3.connect('education_demographics.db')
cursor = conn.cursor()

# Add indexes for commonly queried columns
print("Adding indexes...")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_zip_demographics_income ON zip_demographics(income_bucket)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_zip_demographics_population ON zip_demographics(population_bucket)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_zip_demographics_zip ON zip_demographics(zip_code)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_zip_coordinates_zip ON zip_coordinates(zip_code)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_zip_boundaries_zip ON zip_boundaries(zip_code)")

conn.commit()
conn.close()
print("Indexes created successfully!")
