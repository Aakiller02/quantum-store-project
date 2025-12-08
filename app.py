from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors

app = Flask(__name__)
app.config.from_object("config")

mysql = MySQL(app)

@app.route('/')
def home():
    if 'username' in session:
        return redirect('/library')
    return redirect('/store')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['username'] = username
            return redirect('/library')
        else:
            return render_template('login.html', error="Invalid login!")
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO Users (username, password_hash) VALUES (%s, %s)",
            (username, password)
        )
        mysql.connection.commit()

        return redirect('/login')

    return render_template('register.html')


@app.route('/library')
def library():
    if 'username' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM Users WHERE username=%s", (session['username'],))
    user = cursor.fetchone()
    user_id = user['id']

    cursor.execute("""SELECT * FROM Games INNER JOIN Personal_Library ON Games.id = Personal_Library.game_id WHERE Personal_Library.user_id=%s""", (user_id,))
    games = cursor.fetchall()

    return render_template('library.html', games=games)

@app.route('/store')
def store():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Games")
    games = cursor.fetchall()

    if 'username' in session:
        return render_template('store.html', islogin=True, games=games)
    else:
        return render_template('store.html', islogin=False, games=games)

@app.route('/game_page/<string:game_title>')
def game_page(game_title):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Games WHERE title=%s", (game_title,))
    game = cursor.fetchone()

    if not game:
        return "Game not found", 404

    return render_template('game_page.html', game=game)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug=True)
