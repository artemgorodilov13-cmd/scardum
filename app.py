from flask import Flask, render_template, abort
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "scardum.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    badge = db.Column(db.String(50))
    is_special = db.Column(db.Boolean, default=False)
    short_text = db.Column(db.String(255))

@app.route('/')
def index():
    all_games = Game.query.all()
    return render_template('index.html', games=all_games)

@app.route('/game/<game_slug>')
def game_page(game_slug):
    game = Game.query.filter_by(slug=game_slug).first()
    if game:
        return render_template('game_review.html', game=game)
    abort(404)

if __name__ == '__main__':
    app.run(debug=True)