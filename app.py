from flask import Flask, render_template, jsonify, request
import json
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import os
import logging
from functools import lru_cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_mysql_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
    except mysql.connector.Error as e:
        logger.error(f"Error connecting to MySQL database: {e}")
        raise

@lru_cache(maxsize=1)
def get_buckets():
    """Get income and population buckets with caching"""
    logger.info("Loading buckets...")
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        # Get income buckets
        cursor.execute("""
            SELECT DISTINCT income_bucket 
            FROM zip_demographics 
            WHERE income_bucket != 'Under $100k'
            ORDER BY income_bucket
        """)
        income_buckets = [row[0] for row in cursor.fetchall()]
        
        # Get population buckets
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
        
        return income_buckets, population_buckets
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/')
def index():
    try:
        income_buckets, population_buckets = get_buckets()
        return render_template(
            'index.html',
            income_buckets=income_buckets,
            population_buckets=population_buckets
        )
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/api/colleges')
def get_colleges():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get query parameters
        min_income = request.args.get('min_income', type=int)
        max_income = request.args.get('max_income', type=int)
        min_population = request.args.get('min_population', type=int)
        max_population = request.args.get('max_population', type=int)
        
        # Build the query dynamically
        query = """
            SELECT 
                c.*,
                d.median_household_income,
                d.population as zip_population,
                coord.latitude,
                coord.longitude,
                b.geometry
            FROM colleges c
            LEFT JOIN zip_demographics d ON c.ZIP = d.zip_code
            LEFT JOIN zip_coordinates coord ON c.ZIP = coord.zip_code
            LEFT JOIN zip_boundaries b ON c.ZIP = b.zip_code
            WHERE 1=1
        """
        params = []
        
        if min_income is not None:
            query += " AND d.median_household_income >= %s"
            params.append(min_income)
        if max_income is not None:
            query += " AND d.median_household_income <= %s"
            params.append(max_income)
        if min_population is not None:
            query += " AND d.population >= %s"
            params.append(min_population)
        if max_population is not None:
            query += " AND d.population <= %s"
            params.append(max_population)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convert to list of dicts
        colleges = []
        for row in results:
            college = dict(row)
            # Convert geometry to JSON if it exists
            if college.get('geometry'):
                college['geometry'] = json.loads(college['geometry'])
            colleges.append(college)
            
        return jsonify(colleges)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/demographics')
def get_demographics():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                MIN(median_household_income) as min_income,
                MAX(median_household_income) as max_income,
                MIN(population) as min_population,
                MAX(population) as max_population
            FROM zip_demographics
        """)
        result = cursor.fetchone()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_boundaries')
def get_boundaries():
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT zb.zip_code, zb.geometry, zd.income_bucket, zd.population_bucket
            FROM zip_boundaries zb
            JOIN zip_demographics zd ON zb.zip_code = zd.zip_code
            WHERE zd.income_bucket != 'Under $100k'
        """)
        
        boundaries = [
            {
                'zip_code': row[0],
                'geometry': row[1],
                'income_bucket': row[2],
                'population_bucket': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        return jsonify(boundaries)
    except Exception as e:
        logger.error(f"Error in get_boundaries: {str(e)}")
        return f"An error occurred: {str(e)}", 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
