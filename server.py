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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://hw1_surveyapp_user:D3EESygMjs2f8dixuaPnChQDwspArG1t@dpg-cs1nhrjtq21c73erm4bg-a.oregon-postgres.render.com/hw1_surveyapp')
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
    # Fetch the listing from the database using the listing_id
    listing = StudySession.query.get_or_404(listing_id)
    
    # Render a template to view the listing
    return render_template('view_listing.html', listing=listing)


@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Query user listings and user info from the session
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

    # Exchange authorization code for access token
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        flash("Failed to log in with Auth0.", "danger")
        return redirect(url_for('login'))

    tokens = response.json()

    # Get user info from Auth0
    user_url = f"https://{os.getenv('AUTH0_DOMAIN')}/userinfo"
    user_response = requests.get(user_url, headers={'Authorization': f"Bearer {tokens['access_token']}"})
    if user_response.status_code != 200:
        flash("Failed to get user info from Auth0.", "danger")
        return redirect(url_for('login'))

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
            return redirect(url_for('profile'))

        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')



# Logout route - logs the user out and redirects to the home page
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# Modify /find_study_sessions to pass sessions to the template
@app.route('/find_study_sessions')
def find_study_sessions():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    is_logged_in = 'user' in session
    study_sessions = StudySession.query.all()  # Fetch all study sessions
    return render_template('find_study_sessions.html', is_logged_in=is_logged_in, study_sessions=study_sessions)

# Modify /post_study_sessions to handle file upload and database insertions
@app.route('/post_study_sessions', methods=['GET', 'POST'])
def post_study_sessions():
    if 'user' not in session:
        flash('You need to have an account to post or view Profile.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        print("Form submitted")  # Check if this gets printed
        location = request.form['location']
        class_code = request.form['class-code']
        subject = request.form['subject']
        time = request.form['time']
        num_students = request.form['num-students']
        description = request.form['description']
        picture = request.files['attach-picture']
        
        # Handle file upload (save it to a directory and store the file path in the database)
        picture_path = None
        if picture:
            picture_path = os.path.join('static/uploads', picture.filename)
            picture.save(picture_path)

        # Create a new study session
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

        # Add to the database
        db.session.add(new_session)
        db.session.commit()

        flash('Study session posted successfully!', 'success')
        return redirect(url_for('find_study_sessions'))

    return render_template('post_study_sessions.html')


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
