from flask import Flask, render_template, jsonify, request
import json
import pandas as pd
try:
    import mysql.connector as mysql
except ImportError:
    import MySQLdb as mysql
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
    if 'mysql.connector' in str(mysql):
        # Using mysql-connector-python
        return mysql.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
    else:
        # Using MySQLdb
        return mysql.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            passwd=os.getenv('MYSQL_PASSWORD'),
            db=os.getenv('MYSQL_DATABASE')
        )

@lru_cache(maxsize=1)
def get_buckets():
    """Get income and population buckets with caching"""
    logger.info("Loading buckets...")
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get income buckets
        cursor.execute("""
            SELECT DISTINCT income_bucket 
            FROM zip_demographics 
            WHERE income_bucket IS NOT NULL 
            ORDER BY income_bucket
        """)
        income_buckets = [row['income_bucket'] for row in cursor.fetchall()]
        
        # Get population buckets
        cursor.execute("""
            SELECT DISTINCT population_bucket 
            FROM zip_demographics 
            WHERE population_bucket IS NOT NULL 
            ORDER BY population_bucket
        """)
        population_buckets = [row['population_bucket'] for row in cursor.fetchall()]
        
        return {
            'income_buckets': income_buckets,
            'population_buckets': population_buckets
        }
        
    except Exception as e:
        logger.error(f"Error getting buckets: {str(e)}")
        return {'income_buckets': [], 'population_buckets': []}
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/')
def home():
    try:
        buckets = get_buckets()
        return render_template('index.html', 
                            income_buckets=buckets['income_buckets'],
                            population_buckets=buckets['population_buckets'])
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
                try:
                    college['geometry'] = json.loads(college['geometry'])
                except:
                    college['geometry'] = None
            colleges.append(college)
            
        return jsonify(colleges)
        
    except Exception as e:
        logger.error(f"Error getting colleges: {str(e)}")
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
            WHERE median_household_income IS NOT NULL
            AND population IS NOT NULL
        """)
        result = cursor.fetchone()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting demographics: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
