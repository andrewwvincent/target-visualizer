import sqlite3

# Connect to the database
conn = sqlite3.connect('education_demographics.db')
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    table_name = table[0]
    print(f"\n{table_name}:")
    
    # Get table info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    # Print column information
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  Total rows: {count}")

conn.close()
