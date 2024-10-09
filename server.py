from flask import Flask, redirect, url_for, session, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Create the Flask app
app = Flask(__name__)

# Set up Flask app configuration using environment variables
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@hostname:port/dbname')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and Bcrypt
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User model for storing user information in the database
class User(db.Model):
    __tablename__ = 'user'  # Explicitly set the table name to 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)


# Home route - displays the login and registration forms
@app.route('/')
def home():
    return render_template('login.html')

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
        return redirect(url_for('login'))  # Redirect to the login page

    return render_template('register.html')


# Login route - allows users to log in to their account
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to the base/dashboard page

        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')


# Dashboard route - displays a welcome message for the logged-in user
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    
    return render_template('base.html')


# Logout route - logs the user out and redirects to the home page
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
