from flask import Flask, redirect, url_for, session, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask import has_request_context
from auth0.authentication import GetToken, Users
from datetime import timedelta
from urllib.parse import urlencode
from math import radians, sin, cos, sqrt, atan2
import os
import json
import requests
from dotenv import load_dotenv
from flask_migrate import Migrate
import base64
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError
import psycopg2


load_dotenv()

app = Flask(__name__)

app = Flask(__name__, static_url_path='/static')


app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
Session(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

migrate = Migrate(app, db)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    school = db.Column(db.String(100), nullable=True)
    major = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.LargeBinary, nullable=True)
    
attendees_table = db.Table('attendees',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('session_id', db.Integer, db.ForeignKey('study_session.id'))
)

class StudySession(db.Model):
    __tablename__ = 'study_session'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(255), nullable=False)
    class_code = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    num_students = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    listing_picture = db.Column(db.LargeBinary, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    attendees = db.relationship('User', secondary=attendees_table, backref='sessions', cascade='all, delete')

@app.template_filter('b64encode')
def b64encode_filter(data):
    if data is None:
        return ''
    return base64.b64encode(data).decode('utf-8')

@app.route('/')
def home():
    return redirect(url_for('find_study_sessions'))

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

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(id=session['user']['id']).first()

    if request.method == 'POST':

        user.name = request.form['name']
        user.email = request.form['email']
        user.school = request.form['school']
        user.major = request.form['major']
        user.bio = request.form['bio']

        if 'profile_picture' in request.files:
            picture = request.files['profile_picture']
            if picture:
                user.profile_picture = picture.read()

        db.session.commit()
        session['user']['email'] = user.email
        session['user']['name'] = user.name
        flash('Profile updated successfully.', 'success')

    user_listings = StudySession.query.filter_by(user_id=user.id).all()
    return render_template('profile.html', user=user, listings=user_listings)

@app.route('/delete_listing/<int:listing_id>', methods=['POST'])
def delete_listing(listing_id):
    session_item = StudySession.query.get_or_404(listing_id)
    
    print(f"Attempting to delete session: {session_item.subject}")

    try:
        session_item.attendees.clear()
        db.session.commit()

        db.session.delete(session_item)
        db.session.commit()

        flash('Study session deleted successfully!', 'success')
        return redirect(url_for('find_study_sessions'))

    except StaleDataError:
        db.session.rollback()  
        flash('Error while deleting the study session. Please try again.', 'danger')
        return redirect(url_for('find_study_sessions'))


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

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth0_login'))
    return render_template('base.html', user=session['user'])

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  

    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c  

@app.route('/find_study_sessions', methods=['GET'])
def find_study_sessions():
    query = request.args.get('query', '')
    radius = request.args.get('radius', '50')  
    user_lat = request.args.get('user_lat', None)
    user_lon = request.args.get('user_lon', None)

    user = None
    try:
        if 'user' in session:
            user = User.query.filter_by(id=session['user']['id']).first()
    except Exception as e:
        print(f"Error accessing session: {e}")
    
    try:
        radius_km = float(radius) * 1.60934  
    except ValueError:
        radius_km = 50 * 1.60934  

    if query:
        study_sessions = StudySession.query.filter(
            StudySession.class_code.contains(query) | 
            StudySession.subject.contains(query)
        ).all()
    else:
        study_sessions = StudySession.query.all()

    filtered_sessions = []
    if user_lat and user_lon:
        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
        except ValueError:
            user_lat = None
            user_lon = None

        if user_lat is not None and user_lon is not None:
            for session in study_sessions:
                session_lat = session.latitude
                session_lon = session.longitude

                if session_lat is not None and session_lon is not None:
                    distance = calculate_distance(user_lat, user_lon, session_lat, session_lon)

                    if distance <= radius_km:
                        session_data = {
                            'id': session.id,
                            'location': session.location,
                            'class_code': session.class_code,
                            'subject': session.subject,
                            'time': session.time,
                            'num_students': session.num_students,
                            'latitude': session.latitude,
                            'longitude': session.longitude,
                            'listing_picture': base64.b64encode(session.listing_picture).decode('utf-8') if session.listing_picture else None,
                            'rsvpd': user in session.attendees if user else False  # Check if the user has RSVP'd
                        }
                        filtered_sessions.append(session_data)
    else:
        for session in study_sessions:
            session_data = {
                'id': session.id,
                'location': session.location,
                'class_code': session.class_code,
                'subject': session.subject,
                'time': session.time,
                'num_students': session.num_students,
                'latitude': session.latitude,
                'longitude': session.longitude,
                'listing_picture': base64.b64encode(session.listing_picture).decode('utf-8') if session.listing_picture else None,
                'rsvpd': user in session.attendees if user else False  # Check if the user has RSVP'd
            }
            filtered_sessions.append(session_data)

    return render_template('find_study_sessions.html', study_sessions=filtered_sessions, user=user, query=query)







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
        
        latitude = request.form['latitude']
        longitude = request.form['longitude']

        listing_picture = None
        if 'listing_picture' in request.files:
            picture = request.files['listing_picture']
            if picture:
                listing_picture = picture.read()

        new_session = StudySession(
            location=location,
            class_code=class_code,
            subject=subject,
            time=time,
            num_students=num_students,
            description=description,
            listing_picture=listing_picture,
            latitude=latitude,
            longitude=longitude,  
            user_id=session['user']['id']
        )

        db.session.add(new_session)
        db.session.commit()

        flash('Study session posted successfully!', 'success')
        return redirect(url_for('find_study_sessions'))

    return render_template('post_study_sessions.html')



@app.route('/view_listing/<int:listing_id>', methods=['GET', 'POST'])
def view_listing(listing_id):
    session_item = StudySession.query.get_or_404(listing_id)
    
    user = None
    if 'user' in session:
        user = User.query.filter_by(id=session['user']['id']).first()

    if request.method == 'POST':
        if not user:
            flash('Please log in to RSVP for this session.', 'warning')
            return redirect(url_for('login'))
        

        if user in session_item.attendees:
            session_item.attendees.remove(user) 
            db.session.commit()
            flash('You have successfully un-RSVP\'d.', 'success')
        else:
            session_item.attendees.append(user)
            db.session.commit()
            flash('RSVP successful!', 'success')

        return redirect(url_for('view_listing', listing_id=listing_id))
    already_rsvpd = user in session_item.attendees if user else False

    return render_template('view_listing.html', session_item=session_item, already_rsvpd=already_rsvpd)

@app.route('/edit_listing/<int:listing_id>', methods=['GET', 'POST'])
def edit_listing(listing_id):
    listing = StudySession.query.get_or_404(listing_id)

    if 'user' not in session or listing.user_id != session['user']['id']:
        flash("You don't have permission to edit this listing.", "danger")
        return redirect(url_for('profile'))

    if request.method == 'POST':
        listing.location = request.form['location']
        listing.class_code = request.form['class_code']
        listing.subject = request.form['subject']
        listing.time = request.form['time']
        listing.num_students = request.form['num_students']
        listing.description = request.form['description']

        if 'listing_picture' in request.files:
            picture = request.files['listing_picture']
            if picture and picture.filename != '':  
                listing.listing_picture = picture.read()

        try:
            db.session.commit()
            flash('Listing updated successfully!', 'success')
            return redirect(url_for('profile'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while updating the listing.', 'danger')
            return redirect(url_for('edit_listing', listing_id=listing.id))

    return render_template('edit_listing.html', listing=listing)

if __name__ == '__main__':
    app.run(debug=True)