import os
import openai
#  import OpenAI
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
from werkzeug.utils import secure_filename
import test_key as tk

# Configuration
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xls', 'xlsx'}
app.secret_key = 'secret key here'

# OpenAI API key is kept in a separate file that is not uploaded
openai.api_key = str(tk.secret_key)

# Check for allowed file extensions
def allowed_file(filename):
    print("file name")
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
# Function to generate SQL from CSV/Excel data and text input using GPT-4o mini
def generate_sql_with_gpt(df, text_input):
    # 1. Prepare Data for Prompt; get column names and data types
    column_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        # Basic data type mapping for SQL (you might need to refine this)
        if 'int' in dtype:
            sql_dtype = 'INTEGER'
        elif 'float' in dtype:
            sql_dtype = 'REAL'  # Or NUMERIC
        elif 'datetime' in dtype or 'date' in dtype:
            sql_dtype = 'DATE'  # Or TIMESTAMP
        elif 'bool' in dtype:
            sql_dtype = 'BOOLEAN'
        else:
            sql_dtype = 'TEXT'
        column_info.append(f"{col} ({sql_dtype})")

    # 2. Construct the Prompt
    prompt = f"""
                You are a helpful assistant that generates SQL code to create a database table based on the user's input instructions and uploaded file of data.
                Not only should you provide SQL code to create a table but you should provide code that will insert all rows and columns of provided data in the file.
                Additionally, if there is any missing data then refer to SQL best practices when managing different types of missing data.

                Here is information about the table's columns and their data types:
                {', '.join(column_info)}

                Here is the first row of data from the table for context:
                {df.iloc[0].to_dict()}

                The user has provided the following additional instructions or context:
                {text_input}

                Generate the appropriate SQL 'CREATE TABLE' statement, inferring the best suited SQL data types:
        """

    # 3. Call OpenAI API
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""You are a helpful assistant that generates SQL code to create a database table based on the user's input instructions and uploaded file of data.
                Not only should you provide SQL code to create a table but you should provide code that will insert all rows and columns of provided data in the file.
                Additionally, if there is any missing data then refer to SQL best practices when managing different types of missing data."""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Adjust for creativity as needed
            max_tokens=3000  # Set a reasonable limit
        )

        # 4. Extract SQL Code from Response
        sql_code = response.choices[0].message.content.strip()
        return sql_code

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

# Home route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle text input
        text_input = request.form['text_input']

        # Handle file upload
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)


        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process file
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filepath)
                else:  # Assume Excel
                    df = pd.read_excel(filepath)


                # Generate SQL using GPT-4o
                sql_code = generate_sql_with_gpt(df, text_input)

                if sql_code:
                    # Display the SQL code to the user
                    return render_template('result.html', sql_code=sql_code)
                else:
                    flash("Failed to generate SQL code.")

            except Exception as e:
                flash(f"Error processing file: {e}")

            return redirect(url_for('index'))

    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
