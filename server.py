from flask import Flask, redirect, url_for, session, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_session import Session
from auth0.authentication import GetToken, Users  # Update this line
from urllib.parse import urlencode
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Create the Flask app
app = Flask(__name__)

# Set up Flask app configuration using environment variables
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://hw1_surveyapp_user:D3EESygMjs2f8dixuaPnChQDwspArG1t@dpg-cs1nhrjtq21c73erm4bg-a.oregon-postgres.render.com/hw1_surveyapp')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Initialize the database and Bcrypt
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User model for storing user information in the database
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

# Home route - displays the login and registration forms
@app.route('/')
def home():
    return render_template('login.html')

# Auth0 Login route - redirects to Auth0 login page
@app.route('/auth0-login')
def auth0_login():
    auth0_url = f"https://{os.getenv('AUTH0_DOMAIN')}/authorize"
    params = {
        "audience": os.getenv('AUTH0_AUDIENCE'),
        "response_type": "code",
        "client_id": os.getenv('AUTH0_CLIENT_ID'),
        "redirect_uri": os.getenv('AUTH0_CALLBACK_URL'),
        "scope": "openid profile email"
    }
    return redirect(f"{auth0_url}?{urlencode(params)}")

@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth0_login'))

    return render_template('profile.html')  # Ensure you create a profile.html template.

# Auth0 Callback route - handles the response from Auth0
@app.route('/callback')
def callback_handling():
    code = request.args.get('code')
    url = f"https://{os.getenv('AUTH0_DOMAIN')}/oauth/token"
    headers = {'content-type': 'application/json'}
    payload = {
        'grant_type': 'authorization_code',
        'client_id': os.getenv('AUTH0_CLIENT_ID'),
        'client_secret': os.getenv('AUTH0_CLIENT_SECRET'),
        'code': code,
        'redirect_uri': os.getenv('AUTH0_CALLBACK_URL')
    }

    # Exchange authorization code for access token
    response = requests.post(url, json=payload, headers=headers)
    tokens = response.json()

    # Get user info from Auth0
    user_url = f"https://{os.getenv('AUTH0_DOMAIN')}/userinfo"
    user_response = requests.get(user_url, headers={'Authorization': f"Bearer {tokens['access_token']}"})
    user_info = user_response.json()

    # Store user info in session
    session['user'] = user_info
    return redirect(url_for('dashboard'))

# Dashboard route - displays a welcome message for the logged-in user
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth0_login'))

    return render_template('base.html', user=session['user'])

# Registration route - allows users to create an account
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        # Hash the password before storing it in the database
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password=hashed_password)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login route - allows users to log in to their account
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user'] = {
                'id': user.id,
                'email': user.email
            }
            flash('Login successful!', 'success')
            return redirect(url_for('find_study_sessions'))  # Corrected this line

        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

# Logout route - logs the user out and redirects to the home page
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/find_study_sessions')
def find_study_sessions():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth0_login'))

    return render_template('find_study_sessions.html') 

@app.route('/post_study_sessions')
def post_study_sessions():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth0_login'))

    return render_template('post_study_sessions.html') 
# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
