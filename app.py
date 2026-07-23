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
        try:
            # 1. Читаем твой готовый ручной файл игры
            html_content = render_template(f'game/{game_slug}.html', game=game)
            
            # 2. Стили светлой и праздничной тем из game_review.html
            theme_styles = """
            <style>
                /* СВЕТЛАЯ ТЕМА */
                body.light-theme { background: #f4f7f6 !important; color: #2d3748 !important; }
                body.light-theme .container { background: #ffffff !important; border-color: #cbd5e1 !important; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05) !important; color: #2d3748 !important; }
                body.light-theme h1 { color: #0f766e !important; border-bottom-color: #e2e8f0 !important; }
                body.light-theme h3 { color: #1a202c !important; }
                body.light-theme .info-grid { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; }
                body.light-theme .info-item, body.light-theme .info-item div { color: #2d3748 !important; }
                body.light-theme .info-item span { color: #0d9488 !important; }
                body.light-theme .game-screenshot-box { border-color: #cbd5e1 !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important; }
                body.light-theme .back-btn { color: #0d9488 !important; }
                body.light-theme .rating-highlight { color: #0d9488 !important; text-shadow: none !important; }

                /* ПРАЗДНИЧНАЯ ТЕМА */
                body.birthday-theme { background: #0a0616 !important; color: #e2def2 !important; }
                body.birthday-theme .container { background: #150f2b !important; border-color: #2f1d4f !important; box-shadow: 0 0 25px rgba(255, 0, 127, 0.25) !important; color: #e2def2 !important; }
                body.birthday-theme h1 { color: #ff007f !important; border-bottom-color: #ff007f !important; }
                body.birthday-theme h3 { color: #ff007f !important; }
                body.birthday-theme .info-grid { background: #0a0616 !important; }
                body.birthday-theme .info-item, body.birthday-theme .info-item div { color: #e2def2 !important; }
                body.birthday-theme .info-item span { color: #ff007f !important; }
                body.birthday-theme .game-screenshot-box { border-color: #ff007f !important; box-shadow: 0 0 15px rgba(255, 0, 127, 0.3) !important; }
                body.birthday-theme .back-btn { color: #ff007f !important; }
                body.birthday-theme .rating-highlight { color: #ff007f !important; text-shadow: 0 0 8px rgba(255, 0, 127, 0.6) !important; }
            </style>
            """
            
            # 3. Скрипт, который активирует выбранную тему
            theme_script = """
            <script>
                document.addEventListener("DOMContentLoaded", () => {
                    const savedTheme = localStorage.getItem('scardum-current-theme') || 'dark-theme';
                    document.body.classList.remove('light-theme', 'birthday-theme', 'dark-theme');
                    if (savedTheme !== 'dark-theme') {
                        document.body.classList.add(savedTheme);
                    }
                    
                    if (savedTheme === 'light-theme') {
                        if(document.getElementById('position-light')) document.getElementById('position-light').checked = true;
                        if(document.getElementById('theme-status')) document.getElementById('theme-status').innerText = 'LIGHT';
                    } else if (savedTheme === 'birthday-theme') {
                        if(document.getElementById('position-birthday')) document.getElementById('position-birthday').checked = true;
                        if(document.getElementById('theme-status')) document.getElementById('theme-status').innerText = 'BIRTHDAY';
                    } else {
                        if(document.getElementById('position-dark')) document.getElementById('position-dark').checked = true;
                        if(document.getElementById('theme-status')) document.getElementById('theme-status').innerText = 'DARK';
                    }
                });
            </script>
            """
            
            # Вклеиваем стили в голову, а скрипт — в самый конец страницы
            html_content = html_content.replace('</head>', f'{theme_styles}</head>')
            fixed_html = html_content.replace('</body>', f'{theme_script}</body>')
            return fixed_html
            
        except Exception:
            abort(404)
    abort(404)

if __name__ == '__main__':
    app.run(debug=True)
