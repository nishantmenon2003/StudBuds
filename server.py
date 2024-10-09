from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def find_study_sessions():
    return render_template('find_study_sessions.html', title="Find Study Sessions", name="StudBuds")

@app.route('/profile')
def profile():
    return render_template('profile.html', title="Profile", name="StudBuds")

@app.route('/post_study_session')
def post_study_session():
    return render_template('post_study_session.html', title="Post Study Session", name="StudBuds")

if __name__ == '__main__':
    app.run(debug=True)
