from flask import Flask, render_template, request, redirect, jsonify
import logging
import os
from flask import current_app, g
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


pool = None

def setup():
    global pool
    DATABASE_URL = os.environ['DATABASE_URL']
    current_app.logger.info(f"creating db connection pool")
    pool = ThreadedConnectionPool(1, 100, dsn=DATABASE_URL, sslmode='require')


@contextmanager
def get_db_connection():
    try:
        connection = pool.getconn()
        yield connection
    finally:
        pool.putconn(connection)


@contextmanager
def get_db_cursor(commit=False):
    with get_db_connection() as connection:
      cursor = connection.cursor(cursor_factory=DictCursor)
      try:
          yield cursor
          if commit:
              connection.commit()
      finally:
          cursor.close()


@app.route('/')
def home():
    return render_template('home.html', Title = "Food Survey Consent")


@app.route('/decline')
def decline():
    return render_template('decline.html', Title = "Food Survey Declined")


@app.route('/thanks')
def thanks():
    return render_template('thanks.html', Title = "Food Survey Completed - Thanks!")


if __name__ == '__main__':
    app.run(debug=True)
    

