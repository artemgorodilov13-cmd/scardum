from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', status="Разработка на localhost")

@app.route('/about')
def about():
    return render_template('about.html')

# Добавили game/ перед каждым файлом:
@app.route('/game/bfbc2')
def bfbc2():
    return render_template('game/bfbc2.html')

@app.route('/game/crysis3')
def crysis3():
    return render_template('game/crysis3.html')

@app.route('/game/witcher3')
def witcher_page():
    return render_template('game/witcher3.html')

@app.route('/game/fallout4')
def fallout4_page():
    return render_template('game/fallout4.html')

@app.route('/game/skyrim')
def skyrim_page():
    return render_template('game/skyrim.html')

@app.route('/game/fallout3')
def fallout3_page():
    return render_template('game/fallout3.html')

@app.route('/game/falloutnv')
def falloutnv_page():
    return render_template('game/falloutnv.html')

@app.route('/game/fallout1997')
def fallout1997_page():
    return render_template('game/fallout1997.html')

@app.route('/game/fallout2')
def fallout2_page():
    return render_template('game/fallout2.html')

@app.route('/game/fallout76')
def fallout76_page():
    return render_template('game/fallout76.html')

@app.route('/game/skyrimarena')
def skyrimarena_page():
    return render_template('game/skyrimarena.html')

@app.route('/game/skyrim2')
def skyrim2_page():
    return render_template('game/skyrim2.html')

@app.route('/game/skyrim3')
def skyrim3_page():
    return render_template('game/skyrim3.html')

@app.route('/game/skyrim4')
def skyrim4_page():
    return render_template('game/skyrim4.html')

@app.route('/game/skyrim4re')
def skyrim4re_page():
    return render_template('game/skyrim4re.html')

@app.route('/game/skyrimse')
def skyrimse_page():
    return render_template('game/skyrimse.html')
    
@app.route('/game/skyrimae')
def skyrimae_page():
    return render_template('game/skyrimae.html')

if __name__ == '__main__':
    app.run(debug=True)