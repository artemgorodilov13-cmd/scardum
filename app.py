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
    publisher = db.Column(db.String(100), default='')
    # Игра-запись есть в БД (реакции/комментарии работают, страница открывается по прямой ссылке),
    # но на главную в виде карточки не попадает — используем для DLC вроде Shadow of the Erdtree.
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    views = db.Column(db.Integer, default=0, nullable=False)
    # Текст страницы-обзора, заполняемый из мобильного приложения (без доступа к файлам шаблонов).
    # Если пусто — страница по-прежнему рендерится из templates/game/<slug>.html как раньше.
    review_html = db.Column(db.Text)
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

    # db.create_all() не добавляет новые колонки к уже существующим таблицам,
    # поэтому на старой базе (где уже есть просмотры/реакции) недостающие колонки
    # нужно добавить вручную через ALTER TABLE — один раз, без потери данных.
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('game')]
    if 'publisher' not in existing_columns:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE game ADD COLUMN publisher VARCHAR(100) DEFAULT ""'))
            conn.commit()
    if 'is_hidden' not in existing_columns:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE game ADD COLUMN is_hidden BOOLEAN DEFAULT 0'))
            conn.commit()
    if 'review_html' not in existing_columns:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE game ADD COLUMN review_html TEXT'))
            conn.commit()


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper


def api_admin_required(f):
    """Как admin_required, но для JSON-эндпоинтов приложения: вместо редиректа
    на страницу логина отдаёт 401, чтобы фронт мог показать экран входа."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'unauthorized'}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route('/')
def index():
    all_games = Game.query.filter_by(is_hidden=False).all()
    all_games.sort(key=lambda g: (g.views or 0) + g.total_reactions, reverse=True)
    return render_template('index.html', games=all_games)

@app.route('/game/<game_slug>')
def game_page(game_slug):
    game = Game.query.filter_by(slug=game_slug).first()
    if not game:
        abort(404)
    try:
        # Считаем просмотр
        game.views = (game.views or 0) + 1
        db.session.commit()

        # 1. Если текст обзора заполнен через приложение — рендерим общий шаблон
        #    с этим текстом. Иначе, как раньше, берём готовый ручной файл игры.
        if game.review_html:
            html_content = render_template('game/_generated.html', game=game)
        else:
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


# ==========================================================================
#  МОБИЛЬНОЕ PWA-ПРИЛОЖЕНИЕ (/adminapp) И ЕГО JSON API (/admin/api/...)
#  Отдельная страница-приложение для управления карточками с телефона,
#  без доступа к файлам проекта. Использует ту же сессию/пароль, что и /admin.
# ==========================================================================

@app.route('/adminapp')
def adminapp():
    return render_template('adminapp.html')


def game_to_dict(g, include_review=False):
    d = {
        'id': g.id,
        'slug': g.slug,
        'title': g.title,
        'badge': g.badge or '',
        'publisher': g.publisher or '',
        'short_text': g.short_text or '',
        'is_special': bool(g.is_special),
        'is_hidden': bool(g.is_hidden),
        'views': g.views or 0,
        'total_reactions': g.total_reactions,
        'has_review_html': bool(g.review_html),
    }
    if include_review:
        d['review_html'] = g.review_html or ''
    return d


@app.route('/admin/api/login', methods=['POST'])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    if check_password_hash(ADMIN_PASSWORD_HASH, password):
        session['is_admin'] = True
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'invalid password'}), 401


@app.route('/admin/api/logout', methods=['POST'])
def api_admin_logout():
    session.pop('is_admin', None)
    return jsonify({'status': 'ok'})


@app.route('/admin/api/me')
def api_admin_me():
    return jsonify({'is_admin': bool(session.get('is_admin'))})


@app.route('/admin/api/games')
@api_admin_required
def api_list_games():
    q = (request.args.get('q') or '').strip().lower()
    games = Game.query.order_by(Game.title).all()
    if q:
        games = [g for g in games if q in g.title.lower() or q in g.slug.lower()]
    return jsonify([game_to_dict(g) for g in games])


@app.route('/admin/api/games/<int:game_id>')
@api_admin_required
def api_get_game(game_id):
    g = Game.query.get_or_404(game_id)
    return jsonify(game_to_dict(g, include_review=True))


@app.route('/admin/api/games', methods=['POST'])
@api_admin_required
def api_create_game():
    data = request.get_json(silent=True) or {}
    slug = (data.get('slug') or '').strip()
    title = (data.get('title') or '').strip()
    if not slug or not title:
        return jsonify({'error': 'slug и title обязательны'}), 400
    if Game.query.filter_by(slug=slug).first():
        return jsonify({'error': 'такой slug уже существует'}), 409

    g = Game(
        slug=slug,
        title=title,
        badge=(data.get('badge') or '').strip() or None,
        publisher=(data.get('publisher') or '').strip(),
        short_text=(data.get('short_text') or '').strip() or None,
        is_special=bool(data.get('is_special')),
        is_hidden=bool(data.get('is_hidden')),
        review_html=(data.get('review_html') or '').strip() or None,
    )
    db.session.add(g)
    db.session.commit()
    return jsonify(game_to_dict(g, include_review=True)), 201


@app.route('/admin/api/games/<int:game_id>', methods=['PUT'])
@api_admin_required
def api_update_game(game_id):
    g = Game.query.get_or_404(game_id)
    data = request.get_json(silent=True) or {}

    if 'slug' in data:
        new_slug = (data['slug'] or '').strip()
        if not new_slug:
            return jsonify({'error': 'slug не может быть пустым'}), 400
        existing = Game.query.filter_by(slug=new_slug).first()
        if existing and existing.id != g.id:
            return jsonify({'error': 'такой slug уже существует'}), 409
        g.slug = new_slug
    if 'title' in data:
        title = (data['title'] or '').strip()
        if not title:
            return jsonify({'error': 'title не может быть пустым'}), 400
        g.title = title
    if 'badge' in data:
        g.badge = (data['badge'] or '').strip() or None
    if 'publisher' in data:
        g.publisher = (data['publisher'] or '').strip()
    if 'short_text' in data:
        g.short_text = (data['short_text'] or '').strip() or None
    if 'is_special' in data:
        g.is_special = bool(data['is_special'])
    if 'is_hidden' in data:
        g.is_hidden = bool(data['is_hidden'])
    if 'review_html' in data:
        g.review_html = (data['review_html'] or '').strip() or None

    db.session.commit()
    return jsonify(game_to_dict(g, include_review=True))


@app.route('/admin/api/games/<int:game_id>', methods=['DELETE'])
@api_admin_required
def api_delete_game(game_id):
    g = Game.query.get_or_404(game_id)
    db.session.delete(g)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@app.route('/admin/api/stats')
@api_admin_required
def api_stats():
    games = Game.query.all()
    total_views = sum(g.views or 0 for g in games)
    total_reactions = sum(g.total_reactions for g in games)
    pending_comments = Comment.query.filter_by(is_approved=False).count()
    pending_suggestions = Suggestion.query.filter_by(is_reviewed=False).count()
    top_games = sorted(games, key=lambda g: (g.views or 0) + g.total_reactions, reverse=True)[:5]
    return jsonify({
        'total_games': len(games),
        'total_views': total_views,
        'total_reactions': total_reactions,
        'pending_comments': pending_comments,
        'pending_suggestions': pending_suggestions,
        'top_games': [
            {'title': g.title, 'slug': g.slug, 'views': g.views or 0, 'reactions': g.total_reactions}
            for g in top_games
        ],
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
