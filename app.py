from flask import Flask, render_template, abort, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "scardum.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Нужен для сессий (админ-логин). На Render задай свою переменную окружения SECRET_KEY.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-dev-only')

# Пароль админки. Задай ADMIN_PASSWORD в переменных окружения на Render,
# иначе локально по умолчанию будет "admin123" — смени перед деплоем.
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123'))

# Набор доступных реакций на карточках игр
ALLOWED_EMOJIS = ['🔥', '❤️', '😂', '👍', '😱']

db = SQLAlchemy(app)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    badge = db.Column(db.String(50))
    is_special = db.Column(db.Boolean, default=False)
    short_text = db.Column(db.String(255))
    views = db.Column(db.Integer, default=0, nullable=False)
    reactions = db.relationship('Reaction', backref='game', lazy=True)
    comments = db.relationship('Comment', backref='game', lazy=True)

    @property
    def reaction_counts(self):
        return {r.emoji: r.count for r in self.reactions}

    @property
    def total_reactions(self):
        return sum(r.count for r in self.reactions)

    @property
    def approved_comments(self):
        return sorted(
            [c for c in self.comments if c.is_approved],
            key=lambda c: c.created_at,
            reverse=True
        )


class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    count = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (db.UniqueConstraint('game_id', 'emoji', name='uq_game_emoji'),)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_title = db.Column(db.String(150), nullable=False)
    note = db.Column(db.String(500))
    is_reviewed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# Создаёт только те таблицы, которых ещё нет в базе (например, новую "reaction"),
# существующие таблицы (game и её данные) не трогает.
with app.app_context():
    db.create_all()


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    all_games = Game.query.all()
    all_games.sort(key=lambda g: (g.views or 0) + g.total_reactions, reverse=True)
    return render_template('index.html', games=all_games)

@app.route('/game/<game_slug>')
def game_page(game_slug):
    game = Game.query.filter_by(slug=game_slug).first()
    if game:
        try:
            # Считаем просмотр
            game.views = (game.views or 0) + 1
            db.session.commit()

            # 1. Читаем твой готовый ручной файл игры
            html_content = render_template(f'game/{game_slug}.html', game=game)

            # 1.5 Готовим блок комментариев (список одобренных + форма отправки)
            comments_html = render_template('comments_block.html', game=game, comments=game.approved_comments)
            
            # 2. Стили светлой темы из game_review.html
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
                body.light-theme .fps-box, body.light-theme .fps-box p { background: #f8fafc !important; border-left-color: #0d9488 !important; color: #2d3748 !important; }
                body.light-theme .fps-title { color: #0d9488 !important; }
            </style>
            """
            
            # 3. Скрипт, который активирует выбранную тему
            theme_script = """
            <script>
                document.addEventListener("DOMContentLoaded", () => {
                    const savedTheme = localStorage.getItem('scardum-current-theme') || 'dark-theme';
                    document.body.classList.remove('light-theme', 'dark-theme');
                    if (savedTheme !== 'dark-theme') {
                        document.body.classList.add(savedTheme);
                    }
                    
                    if (savedTheme === 'light-theme') {
                        if(document.getElementById('position-light')) document.getElementById('position-light').checked = true;
                        if(document.getElementById('theme-status')) document.getElementById('theme-status').innerText = 'LIGHT';
                    } else {
                        if(document.getElementById('position-dark')) document.getElementById('position-dark').checked = true;
                        if(document.getElementById('theme-status')) document.getElementById('theme-status').innerText = 'DARK';
                    }
                });
            </script>
            """
            
            # Вклеиваем стили в голову, а скрипт и блок комментариев — в самый конец страницы
            html_content = html_content.replace('</head>', f'{theme_styles}</head>')
            fixed_html = html_content.replace('</body>', f'{comments_html}{theme_script}</body>')
            return fixed_html
            
        except Exception:
            abort(404)
    abort(404)


@app.route('/game/<game_slug>/react', methods=['POST'])
def react(game_slug):
    game = Game.query.filter_by(slug=game_slug).first()
    if not game:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    emoji = data.get('emoji') or request.form.get('emoji')

    if emoji not in ALLOWED_EMOJIS:
        return jsonify({'error': 'invalid emoji'}), 400

    # Не даём накручивать реакции: одна игра — одна реакция с одного браузера
    reacted_cookie = request.cookies.get('scardum_reacted', '')
    reacted_slugs = set(filter(None, reacted_cookie.split(',')))

    if game_slug in reacted_slugs:
        return jsonify({'error': 'already reacted'}), 409

    reaction = Reaction.query.filter_by(game_id=game.id, emoji=emoji).first()
    if not reaction:
        reaction = Reaction(game_id=game.id, emoji=emoji, count=0)
        db.session.add(reaction)
    reaction.count += 1
    db.session.commit()

    reacted_slugs.add(game_slug)
    response = jsonify({'emoji': emoji, 'count': reaction.count})
    response.set_cookie('scardum_reacted', ','.join(reacted_slugs), max_age=60 * 60 * 24 * 365)
    return response


@app.route('/game/<game_slug>/comment', methods=['POST'])
def add_comment(game_slug):
    game = Game.query.filter_by(slug=game_slug).first()
    if not game:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    text = (data.get('text') or '').strip()
    honeypot = (data.get('website') or '').strip()

    # Honeypot-поле: если заполнено (человек его не видит и не тронет) —
    # тихо "принимаем" запрос, но ничего не сохраняем. Это бот.
    if honeypot:
        return jsonify({'status': 'queued'})

    if not name or not text:
        return jsonify({'error': 'name and text required'}), 400
    if len(name) > 50 or len(text) > 500:
        return jsonify({'error': 'too long'}), 400

    comment = Comment(game_id=game.id, name=name, text=text, is_approved=False)
    db.session.add(comment)
    db.session.commit()

    return jsonify({'status': 'queued'})


@app.route('/suggest-game', methods=['POST'])
def suggest_game():
    data = request.get_json(silent=True) or {}
    game_title = (data.get('game_title') or '').strip()
    note = (data.get('note') or '').strip()
    honeypot = (data.get('website') or '').strip()

    # Honeypot: боты заполняют это поле, люди его не видят
    if honeypot:
        return jsonify({'status': 'queued'})

    if not game_title:
        return jsonify({'error': 'game_title required'}), 400
    if len(game_title) > 150 or len(note) > 500:
        return jsonify({'error': 'too long'}), 400

    suggestion = Suggestion(game_title=game_title, note=note or None)
    db.session.add(suggestion)
    db.session.commit()

    return jsonify({'status': 'queued'})


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Неверный пароль'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    games = Game.query.order_by(Game.views.desc()).all()
    total_views = sum(g.views or 0 for g in games)
    pending_comments_count = Comment.query.filter_by(is_approved=False).count()
    pending_suggestions_count = Suggestion.query.filter_by(is_reviewed=False).count()
    return render_template(
        'admin/dashboard.html',
        games=games,
        total_views=total_views,
        pending_comments_count=pending_comments_count,
        pending_suggestions_count=pending_suggestions_count
    )


@app.route('/admin/comments')
@admin_required
def admin_comments():
    pending = Comment.query.filter_by(is_approved=False).order_by(Comment.created_at.desc()).all()
    approved = Comment.query.filter_by(is_approved=True).order_by(Comment.created_at.desc()).all()
    return render_template('admin/comments.html', pending=pending, approved=approved)


@app.route('/admin/comments/<int:comment_id>/approve', methods=['POST'])
@admin_required
def approve_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.is_approved = True
    db.session.commit()
    return redirect(url_for('admin_comments'))


@app.route('/admin/comments/<int:comment_id>/delete', methods=['POST'])
@admin_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('admin_comments'))


@app.route('/admin/suggestions')
@admin_required
def admin_suggestions():
    pending = Suggestion.query.filter_by(is_reviewed=False).order_by(Suggestion.created_at.desc()).all()
    reviewed = Suggestion.query.filter_by(is_reviewed=True).order_by(Suggestion.created_at.desc()).all()
    return render_template('admin/suggestions.html', pending=pending, reviewed=reviewed)


@app.route('/admin/suggestions/<int:suggestion_id>/mark-reviewed', methods=['POST'])
@admin_required
def mark_suggestion_reviewed(suggestion_id):
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    suggestion.is_reviewed = True
    db.session.commit()
    return redirect(url_for('admin_suggestions'))


@app.route('/admin/suggestions/<int:suggestion_id>/delete', methods=['POST'])
@admin_required
def delete_suggestion(suggestion_id):
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    db.session.delete(suggestion)
    db.session.commit()
    return redirect(url_for('admin_suggestions'))


if __name__ == '__main__':
    app.run(debug=True)