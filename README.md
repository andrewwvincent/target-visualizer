# College Map Visualizer

An interactive web application that visualizes college locations in high-income ZIP codes across the United States.

## Features

- Interactive map showing colleges and ZIP code boundaries
- Filtering by income and population buckets
- Business category filtering
- Detailed college information in a searchable table
- Merged visualization of adjacent ZIP codes

## Deployment Instructions

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the database setup:
   ```bash
   python database_setup.py
   python get_zip_boundaries.py
   ```
4. Start the Flask application:
   ```bash
   python app.py
   ```

### Deploying to PythonAnywhere

1. Sign up for a free account at [PythonAnywhere](https://www.pythonanywhere.com)
2. From the Dashboard, go to Web Apps and create a new web app
3. Choose Manual Configuration and Python 3.9
4. In the Files section:
   - Upload your project files
   - Upload your database file (education_demographics.db)
5. In the Virtualenv section:
   - Create a new virtualenv with Python 3.9
   - Install requirements:
     ```bash
     pip install -r requirements.txt
     ```
6. Configure the WSGI file:
   - Click on the WSGI configuration file link
   - Replace the contents with:
     ```python
     import sys
     path = '/home/YOUR_USERNAME/your-project-directory'
     if path not in sys.path:
         sys.path.append(path)
     
     from app import app as application
     ```
7. Reload your web app

Your application will be available at: `http://yourusername.pythonanywhere.com`

## Data Sources

- College data from Department of Education
- ZIP code boundaries from US Census Bureau
- Demographic data from Census Bureau
