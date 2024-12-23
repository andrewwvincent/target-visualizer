from flask import Flask, render_template, jsonify
import sqlite3
import pandas as pd
import os
import time

app = Flask(__name__)

def get_db_connection():
    db_path = 'education_demographics.db'
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at {db_path}")
    return sqlite3.connect(db_path)

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get income buckets
        cursor.execute("""
            SELECT DISTINCT income_bucket 
            FROM zip_demographics 
            WHERE income_bucket != 'Under $100k'
            ORDER BY income_bucket
        """)
        income_buckets = [row[0] for row in cursor.fetchall()]
        
        # Get population buckets in ascending order
        cursor.execute("""
            SELECT DISTINCT population_bucket 
            FROM zip_demographics 
            ORDER BY 
                CASE population_bucket
                    WHEN 'Under 1,000' THEN 1
                    WHEN '1,000-5,000' THEN 2
                    WHEN '5,000-10,000' THEN 3
                    WHEN '10,000-25,000' THEN 4
                    WHEN '25,000-40,000' THEN 5
                    WHEN '40,000+' THEN 6
                END
        """)
        population_buckets = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return render_template('index.html', income_buckets=income_buckets, population_buckets=population_buckets)
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/get_colleges')
def get_colleges():
    try:
        conn = get_db_connection()
        
        # Get college data without boundaries
        query = """
        SELECT 
            c.*,
            zc.latitude,
            zc.longitude,
            zd.income_bucket,
            zd.population_bucket
        FROM colleges c
        JOIN zip_demographics zd ON c.ZIP = zd.zip_code
        JOIN zip_coordinates zc ON c.ZIP = zc.zip_code
        WHERE zd.income_bucket != 'Under $100k'
        ORDER BY c.NAME
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return jsonify(df.to_dict(orient='records'))
        
    except Exception as e:
        print(f"Error in get_colleges: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_boundaries')
def get_boundaries():
    try:
        conn = get_db_connection()
        
        # Get unique ZIP boundaries for high-income areas
        query = """
        SELECT DISTINCT 
            zb.zip_code,
            zb.geometry,
            zd.income_bucket,
            zd.population_bucket
        FROM zip_boundaries zb
        JOIN zip_demographics zd ON zb.zip_code = zd.zip_code
        WHERE zd.income_bucket != 'Under $100k'
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return jsonify(df.to_dict(orient='records'))
        
    except Exception as e:
        print(f"Error in get_boundaries: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
