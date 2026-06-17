from flask import Flask, render_template, abort
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scardum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    badge = db.Column(db.String(50))
    is_special = db.Column(db.Boolean, default=False)
    short_text = db.Column(db.String(255))
    
    genre = db.Column(db.String(100))
    release_date = db.Column(db.String(50))
    publisher = db.Column(db.String(100))
    metacritic = db.Column(db.String(20))
    story = db.Column(db.Text)
    requirements = db.Column(db.Text)
    
    fps_750ti = db.Column(db.String(100))
    fps_1050ti = db.Column(db.String(100))
    fps_1060 = db.Column(db.String(100))
    fps_1660 = db.Column(db.String(100))
    fps_rx570_580_4 = db.Column(db.String(100))
    fps_rx580_8 = db.Column(db.String(100))

    author_test = db.Column(db.Text)
    author_settings = db.Column(db.String(50))
    author_resolution = db.Column(db.String(50))
    author_message = db.Column(db.Text)
    
    patch_instruction = db.Column(db.Text)
    optimization = db.Column(db.Text)
    worth_2026 = db.Column(db.Text)
    summary = db.Column(db.Text)

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