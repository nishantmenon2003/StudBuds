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
from flask_migrate import Migrate

# Load environment variables from the .env file
load_dotenv()

# Create the Flask app
app = Flask(__name__)

# Set up Flask app configuration using environment variables
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Initialize the database and Bcrypt
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

migrate = Migrate(app, db)

# User model for storing user information in the database
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    school = db.Column(db.String(100), nullable=True)
    major = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)

class StudySession(db.Model):
    __tablename__ = 'study_session'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    class_code = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    num_students = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    picture = db.Column(db.String(200), nullable=True)  # Save the file path for the uploaded picture
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Link to the user who posted

# Home route - displays the login and registration forms
@app.route('/')
def home():
    if 'user' not in session:  # Check if user is not in the session
        return redirect(url_for('login'))  # Redirect to the login page
    return redirect(url_for('login'))  # Redirect to find study sessions if logged in

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

@app.route('/view_listing/<int:listing_id>')
def view_listing(listing_id):
    listing = StudySession.query.get_or_404(listing_id)
    return render_template('view_listing.html', listing=listing)

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    user_listings = StudySession.query.filter_by(user_id=user['id']).all()
    return render_template('profile.html', user=user, listings=user_listings)

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
    response = requests.post(url, json=payload, headers=headers)
    tokens = response.json()

    user_url = f"https://{os.getenv('AUTH0_DOMAIN')}/userinfo"
    user_response = requests.get(user_url, headers={'Authorization': f"Bearer {tokens['access_token']}"})
    user_info = user_response.json()

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

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password=hashed_password)

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
            return redirect(url_for('profile'))

        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

# Logout route - logs the user out and redirects to the home page
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Route to find study sessions with search functionality
@app.route('/find_study_sessions', methods=['GET'])
def find_study_sessions():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    query = request.args.get('query', '')  # Get the search query from the request
    filtered_sessions = []

    # Query the database for study sessions
    study_sessions = StudySession.query.all()

    if query:
        filtered_sessions = [session for session in study_sessions if query.lower() in session.class_code.lower() or query.lower() in session.subject.lower()]
    else:
        filtered_sessions = study_sessions  # Show all sessions if no query is provided

    return render_template('find_study_sessions.html', study_sessions=filtered_sessions, query=query)

# Modify /post_study_sessions to handle file upload and database insertions
@app.route('/post_study_sessions', methods=['GET', 'POST'])
def post_study_sessions():
    if 'user' not in session:
        flash('You need to have an account to post or view Profile.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        location = request.form['location']
        class_code = request.form['class-code']
        subject = request.form['subject']
        time = request.form['time']
        num_students = request.form['num-students']
        description = request.form['description']
        picture = request.files['attach-picture']

        picture_path = None
        if picture:
            picture_path = os.path.join('static/uploads', picture.filename)
            picture.save(picture_path)

        new_session = StudySession(
            location=location,
            class_code=class_code,
            subject=subject,
            time=time,
            num_students=num_students,
            description=description,
            picture=picture_path,
            user_id=session['user']['id']
        )

        db.session.add(new_session)
        db.session.commit()

        flash('Study session posted successfully!', 'success')
        return redirect(url_for('find_study_sessions'))

    return render_template('post_study_sessions.html')

if __name__ == '__main__':
    app.run(debug=True)
