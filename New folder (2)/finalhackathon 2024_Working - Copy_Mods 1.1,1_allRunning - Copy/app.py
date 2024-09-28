from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import requests
import json
import re
import psycopg2
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key for session management
bcrypt = Bcrypt(app)

# Database connection parameters
DB_HOST = 'localhost'  # Replace with your DB host
DB_NAME = 'postgres'  # Replace with your DB name
DB_USER = 'postgres'  # Replace with your DB user
DB_PASSWORD = 'pass@123'  # Replace with your DB password

# Function to connect to the PostgreSQL database
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# Function to generate chatbot response using Gemini API and extract bullet points
def generate_text(input_text):
    api_key = "AIzaSyBGEykAPgVXExWRmhROIYJIeisXudF9nfA"  # Replace with your actual API key
    endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'

    body = json.dumps({
        "contents": [{
            "parts": [{
                "text": input_text
            }]
        }]
    })

    try:
        response = requests.post(endpoint, headers={'Content-Type': 'application/json'}, data=body)
        response_data = response.json()
        full_response_text = response_data['candidates'][0]['content']['parts'][0]['text']

        # Remove asterisks from the response text
        full_response_text = re.sub(r'\*', '', full_response_text)

        # Regex to extract numbered points
        pattern = r'(\d+)\.\s(.*?)(?=\s*\d+\.|$)'
        matches = re.findall(pattern, full_response_text, re.DOTALL)

        # Sort the matches by the first capturing group (the number)
        sorted_points = sorted(matches, key=lambda x: int(x[0]))

        # Format the sorted points for display
        formatted_points = [f"{number}. {point.strip()}" for number, point in sorted_points]

        # Join the formatted points into a single string
        return "\n".join(formatted_points)
    except Exception as e:
        print("Error:", e)
        return "Error communicating with the Gemini API."

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    
    if user_message:
        # Call the Gemini API to get chatbot response and extract bullet points
        response_text = generate_text(user_message + " Give answer in numbered points and limit to 5 points and only give response for the Health and greeting related prompts ")
        return jsonify({'response': response_text})

    return jsonify({'response': "No message received"}), 400

@app.route('/login_button')  # Adjusted route
def login():
    return render_template('login.html')  # This serves the login.html page

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['upUsername']
    password = request.form['upPassword']
    confirm_password = request.form['confirmUpPassword']

    if password != confirm_password:
        return render_template('login.html', message="Passwords do not match", status="error")
    
    try:
        # Establish a connection to the PostgreSQL database
        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if the username already exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
        user_exists = cursor.fetchone()[0]

        if user_exists:
            return render_template('login.html', message="Username already taken", status="error")

        # Call the user_signup procedure using CALL
        cursor.execute("CALL user_signup(%s, %s, %s)", (username, password, confirm_password))

        connection.commit()
        cursor.close()
        connection.close()
        
        message = 'Signup successful'
        success = 'success'
        print("Stored procedure successfully called.")
        return render_template('login.html', message=message, status=success)

    except Exception as e:
        print("Error:", e)
        message = 'Error during signup'
        status = 'error'
        return render_template('login.html', message=message, status=status)

@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username']
    password = request.form['password']

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the user_login procedure using CALL
        cur.execute("CALL user_login(%s, %s)", (username, password))

        conn.commit()
        cur.close()
        conn.close()

        # Store the username in the session
        session['username'] = username

        message = 'Login successful'
        success = 'success'
        print("Stored procedure successfully called.")
        return redirect(url_for('my_profile'))  # Redirect to profile page

    except Exception as e:
        print("Error:", e)
        message = 'Error during login'
        status = 'error'
        return render_template('login.html', message=message, status=status)

@app.route('/profile')
def profile():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    return render_template('profile.html', username=username)  # Pass username to the profile template

@app.route('/myprofile', methods=['GET', 'POST'])
def my_profile():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if request.method == 'POST':
        # Get form data
        first_name = request.form['first_name']
        surname = request.form['surname']
        mobile_no = request.form['mobile_no']
        age = request.form['age']
        gender = request.form['gender']
        medical_history = request.form['medical_history']
        goals = request.form['goals']

        # Call the insert or update procedure
        insert_or_update_user_profile(first_name, surname, mobile_no, age, gender, medical_history, goals, username)

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('my_profile'))

    return render_template('myprofilenew.html', username=username)  # Pass username to the profile template

@app.route('/community')
def community():
    username = session.get('username')  # Check if user is logged in
    if not username:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    return render_template('community.html')  # Render community page if logged in

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove the username from the session
    return redirect(url_for('index'))  # Redirect to the index page or wherever you want



# Function to insert or update user profile
def insert_or_update_user_profile(first_name, surname, mobile_no, age, gender, medical_history, goals, username):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CALL insert_or_update_user_profile(%s, %s, %s, %s, %s, %s, %s, %s);
            """, (first_name, surname, mobile_no, age, gender, medical_history, goals, username))
            conn.commit()
    finally:
        conn.close()

@app.route('/save_profile', methods=['POST'])
def save_profile():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    # Retrieve data from the form
    first_name = request.form['first_name']
    surname = request.form['surname']
    mobile_no = request.form['mobile_no']
    age = request.form['age']
    gender = request.form['gender']
    medical_history = request.form['medical_history']
    goals = request.form['goals']

    try:
        # Establish a connection to the PostgreSQL database
        connection = get_db_connection()
        cursor = connection.cursor()

        # Call the stored procedure to insert or update the user profile
        cursor.execute("CALL insert_or_update_user_profile(%s, %s, %s, %s, %s, %s, %s, %s)", 
                       (first_name, surname, mobile_no, age, gender, medical_history, goals, username))

        connection.commit()
        cursor.close()
        connection.close()

        message = 'Profile saved successfully'
        success = 'success'
        return render_template('myprofilenew.html', message=message, status=success, username=username)

    except Exception as e:
        print("Error:", e)
        message = 'Error saving profile'
        status = 'error'
        return render_template('myprofilenew.html', message=message, status=status, username=username)


@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Use cur.execute to call the stored procedure
        cursor.execute("CALL insert_contact(%s, %s, %s)", (name, email, message))

        # Commit the transaction
        connection.commit()
        cursor.close()
        connection.close()

        # Set success message
        return render_template('index.html', message="Your message has been sent successfully.", status="success")
    except Exception as e:
        print("Error:", e)
        return render_template('index.html', message="Error sending your message. Please try again.", status="error")





if __name__ == "__main__":
    app.run(debug=True)
