from flask import Flask, render_template, jsonify
import sqlite3
import pandas as pd
import os
import time
from functools import lru_cache
import json

app = Flask(__name__)

# Global cache for expensive computations
_cache = {}

def get_db_connection():
    db_path = 'education_demographics.db'
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

def init_cache():
    """Initialize cache with expensive computations"""
    try:
        conn = get_db_connection()
        
        # Cache income and population buckets
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT income_bucket 
            FROM zip_demographics 
            WHERE income_bucket != 'Under $100k'
            ORDER BY income_bucket
        """)
        _cache['income_buckets'] = [row[0] for row in cursor.fetchall()]
        
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
        _cache['population_buckets'] = [row[0] for row in cursor.fetchall()]
        
        # Cache boundaries data
        cursor.execute("""
            SELECT zb.zip_code, zb.geometry, zd.income_bucket, zd.population_bucket
            FROM zip_boundaries zb
            JOIN zip_demographics zd ON zb.zip_code = zd.zip_code
            WHERE zd.income_bucket != 'Under $100k'
        """)
        _cache['boundaries'] = [
            {
                'zip_code': row[0],
                'geometry': row[1],
                'income_bucket': row[2],
                'population_bucket': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        # Cache college data
        cursor.execute("""
            SELECT 
                c.NAME, c.ZIP,
                zc.latitude, zc.longitude,
                zd.income_bucket, zd.population_bucket
            FROM colleges c
            JOIN zip_coordinates zc ON c.ZIP = zc.zip_code
            JOIN zip_demographics zd ON c.ZIP = zd.zip_code
            WHERE zd.income_bucket != 'Under $100k'
        """)
        _cache['colleges'] = [dict(row) for row in cursor.fetchall()]
        
    finally:
        if 'conn' in locals():
            conn.close()

@app.before_first_request
def setup():
    """Initialize the cache before the first request"""
    init_cache()

@app.route('/')
def index():
    try:
        return render_template(
            'index.html',
            income_buckets=_cache.get('income_buckets', []),
            population_buckets=_cache.get('population_buckets', [])
        )
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/get_colleges')
def get_colleges():
    try:
        return jsonify(_cache.get('colleges', []))
    except Exception as e:
        print(f"Error in get_colleges: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/get_boundaries')
def get_boundaries():
    try:
        return jsonify(_cache.get('boundaries', []))
    except Exception as e:
        print(f"Error in get_boundaries: {str(e)}")
        return f"An error occurred: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
