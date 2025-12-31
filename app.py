from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask import request  # Added import for request

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

@app.route('/admin_page')
def admin():
    """Admin dashboard"""
    sort_by_id = request.args.get('sort_by_id', 'asc')  # Default is ascending
    sort_by_title = request.args.get('sort_by_title', 'asc')  # Default is A-Z
    # Simple admin check (you should implement proper role-based access)
    if session.get('username') != "Aakiller":
        flash('Access denied', 'error')
        return redirect(url_for('store'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
         # Dynamic sorting logic
        if sort_by_id == 'asc':
            id_order = 'ASC'
        else:
            id_order = 'DESC'

        if sort_by_title == 'asc':
            title_order = 'ASC'
        else:
            title_order = 'DESC'

        # SQL Query with dynamic sorting based on user input
        cursor.execute(f'''
            SELECT g.id AS game_id, g.*, d.name as developer_name, p.name as publisher_name
            FROM Games g
            LEFT JOIN Developers d ON g.developer_id = d.id
            LEFT JOIN Publishers p ON g.publisher_id = p.id
            ORDER BY g.title {title_order}
        ''')
        games = cursor.fetchall()

        cursor.execute('SELECT * FROM Developers ORDER BY name')
        developers = cursor.fetchall()

        cursor.execute('SELECT * FROM Publishers ORDER BY name')
        publishers = cursor.fetchall()

        cursor.execute('SELECT * FROM Categories ORDER BY type')
        categories = cursor.fetchall()

        cursor.execute('SELECT * FROM Users')
        users = cursor.fetchall()

        return render_template('admin_page.html',
                             games=games,
                             developers=developers,
                             publishers=publishers,
                             categories=categories,
                             users=users,
                             sort_by_id=sort_by_id,
                             sort_by_title=sort_by_title)

    except Exception as e:
        flash(f'Error loading admin panel: {str(e)}', 'error')
    
    return redirect(url_for('store'))

@app.route('/admin_page/game/add', methods=['POST'])
def admin_add_game():
    """Add a new game (CREATE)"""
    if session.get('username') != "Aakiller":
        flash('Access denied', 'error')
        return redirect(url_for('store'))
    
    title = request.form.get('title', '').strip()
    description = request.form.get('descrition', '').strip()
    release_date = request.form.get('release_date')
    price = request.form.get('price')
    developer_id = request.form.get('developer_id')
    publisher_id = request.form.get('publisher_id')
    categories = request.form.getlist('categories')
    
    if not title or not price or not developer_id or not publisher_id:
        flash('Please fill all required fields', 'error')
        return redirect(url_for('admin'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('''
            INSERT INTO Games (title, descrition, release_date, price, developer_id, publisher_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, description, release_date, price, developer_id, publisher_id))
        
        game_id = cursor.lastrowid
        
        # Add categories
        for category_id in categories:
            cursor.execute('''
                INSERT INTO Game_Categories (game_id, category_id)
                VALUES (%s, %s)
            ''', (game_id, category_id))
        
        mysql.connection.commit()
        flash(f'Game "{title}" added successfully', 'success')
        
    except Exception as e:
        flash(f'Failed to add game: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin_page/game/edit/<int:game_id>', methods=['GET', 'POST'])
def admin_edit_game(game_id):
    """Edit a game (UPDATE)"""
    if session.get('username') != "Aakiller":
        flash('Access denied', 'error')
        return redirect(url_for('store'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Handle GET request: retrieve game data and pre-fill the form
    if request.method == 'GET':
        cursor.execute('''
            SELECT g.id AS game_id, g.*, d.name as developer_name, p.name as publisher_name
            FROM Games g
            LEFT JOIN Developers d ON g.developer_id = d.id
            LEFT JOIN Publishers p ON g.publisher_id = p.id
            WHERE g.id = %s
        ''', (game_id,))
        game = cursor.fetchone()

        # If game not found, redirect back to the admin panel
        if not game:
            flash('Game not found', 'error')
            return redirect(url_for('admin'))

        # Fetch developers and publishers to populate dropdowns
        cursor.execute('SELECT * FROM Developers ORDER BY name')
        developers = cursor.fetchall()

        cursor.execute('SELECT * FROM Publishers ORDER BY name')
        publishers = cursor.fetchall()

        return render_template('edit_game.html', game=game, developers=developers, publishers=publishers)

    # Handle POST request: update the game
    elif request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('descrition', '').strip()
        release_date = request.form.get('release_date')
        price = request.form.get('price')
        developer_id = request.form.get('developer_id')
        publisher_id = request.form.get('publisher_id')

        try:
            cursor.execute('''
                UPDATE Games
                SET title = %s, descrition = %s, release_date = %s, price = %s, developer_id = %s, publisher_id = %s
                WHERE id = %s
            ''', (title, description, release_date, price, developer_id, publisher_id, game_id))
            mysql.connection.commit()
            flash('Game updated successfully', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Failed to update game: {str(e)}', 'error')

        return redirect(url_for('admin'))
    
@app.route('/admin_page/user/edit/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    """Edit a user (UPDATE)"""
    if session.get('username') != "Aakiller":
        flash('Access denied', 'error')
        return redirect(url_for('store'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Handle GET request: retrieve game data and pre-fill the form
    if request.method == 'GET':
        cursor.execute('SELECT * FROM Users')
        users = cursor.fetchall()

        return render_template('edit_user.html', users=users)

    # Handle POST request: update the game
    elif request.method == 'POST':
        username = request.form.get('username', '').strip()

        try:
            cursor.execute('''
                UPDATE Users
                SET username = %s
                WHERE id = %s
            ''', (username, user_id))
            mysql.connection.commit()
            flash('User updated successfully', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Failed to update user: {str(e)}', 'error')

        return redirect(url_for('admin'))

@app.route('/admin_page/game/delete/<int:game_id>', methods=['POST'])
def admin_delete_game(game_id):
    """Delete a game (DELETE)"""
    if session.get('username') != "Aakiller":
        flash('Access denied', 'error')
        return redirect(url_for('store'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Delete related records first (foreign key constraints)
        cursor.execute('DELETE FROM Game_Categories WHERE game_id = %s', (game_id,))
        cursor.execute('DELETE FROM Personal_Library WHERE game_id = %s', (game_id,))
        cursor.execute('DELETE FROM Games WHERE id = %s', (game_id,))
        
        mysql.connection.commit()
        flash('Game deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Failed to delete game: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin_page/user/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    """Delete a user (DELETE)"""
    if session.get('username') != "Aakiller":
        flash('Access denied', 'error')
        return redirect(url_for('store'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Delete related records first (foreign key constraints)
        cursor.execute('DELETE FROM Users WHERE id = %s', (user_id,))
        cursor.execute('DELETE FROM Personal_Library WHERE user_id = %s', (user_id,))

        mysql.connection.commit()
        flash('User deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Failed to delete user: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/library')
def library():
    if 'username' not in session:
        return redirect('/login')

    sort_by = request.args.get('sort', 'title')
    valid_sorts = {'title', 'price', 'release_date'}
    sort_column = sort_by if sort_by in valid_sorts else 'title'
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM Users WHERE username=%s", (session['username'],))
    user = cursor.fetchone()
    user_id = user['id']

    cursor.execute("""
        SELECT * FROM Games
        INNER JOIN Personal_Library ON Games.id = Personal_Library.game_id
        WHERE Personal_Library.user_id=%s
        ORDER BY Games.{sort_column}
    """.format(sort_column=sort_column), (user_id,))
    games = cursor.fetchall()

    if 'username' in session:
        if session['username'] == "Aakiller":
            return render_template('library.html', islogin=True, isadmin=True, games=games, sort_by=sort_column)
        else:
            return render_template('library.html', islogin=True, games=games, sort_by=sort_column)
    else:
        return render_template('library.html', islogin=False, games=games, sort_by=sort_column)

@app.route('/store')
def store():
    sort_by = request.args.get('sort', 'title')
    valid_sorts = {'title', 'price', 'release_date'}
    sort_column = sort_by if sort_by in valid_sorts else 'title'
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(f"SELECT * FROM Games ORDER BY {sort_column}")
    games = cursor.fetchall()
    return render_template('home.html', games=games, sort_by=sort_column)

@app.route('/description/<string:game_title>')
def game_page(game_title):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Games WHERE title=%s", (game_title,))
    game = cursor.fetchone()

    cursor.execute('SELECT name FROM Developers WHERE id=%s', (game['developer_id'],))
    developers = cursor.fetchall()

    cursor.execute('SELECT name FROM Publishers WHERE id=%s', (game['publisher_id'],))
    publishers = cursor.fetchall()

    if not game:
        return "Game not found", 404

    if 'username' in session:
        cursor.execute("SELECT id FROM Users WHERE username=%s", (session['username'],))
        user = cursor.fetchone()
        user_id = user['id']

        cursor.execute("SELECT 1 FROM Personal_Library WHERE user_id=%s AND game_id=%s", (user_id, game['id']))
        owned = cursor.fetchone() is not None

        return render_template('description.html', islogin=True, owned=owned, game=game, developers=developers[0], publishers=publishers[0])

    return render_template('description.html', islogin=False, owned=False, game=game, developers=developers[0], publishers=publishers[0])

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/store')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == "POST":
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM Games WHERE title LIKE %s", (f"%{request.form['search']}%",))
        games = cursor.fetchall()
        return render_template("results.html", games=games)
    return render_template('search.html')

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    if not cart:
        return render_template('cart.html', cart_items=[], total=0)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # If only one item, tuple needs a trailing comma
    ids_tuple = tuple(map(int, cart.keys()))
    if len(ids_tuple) == 1:
        ids_tuple = (ids_tuple[0],)
    cursor.execute(
        "SELECT * FROM Games WHERE id IN %s", (ids_tuple,)
    )
    games = cursor.fetchall()
    cart_items = []
    total = 0
    for game in games:
        qty = cart.get(str(game['id']), 1)
        game['quantity'] = qty
        game['subtotal'] = qty * float(game['price'])
        total += game['subtotal']
        cart_items.append(game)
    return render_template('cart.html', cart_items=cart_items, total=total)

# Add to cart route
@app.route('/add_to_cart/<int:game_id>', methods=['POST'])
def add_to_cart(game_id):
    cart = session.get('cart', {})
    cart[str(game_id)] = cart.get(str(game_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('cart'))

# Remove from cart route
@app.route('/remove_from_cart/<int:game_id>', methods=['POST'])
def remove_from_cart(game_id):
    cart = session.get('cart', {})
    cart.pop(str(game_id), None)
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkoutPage():
    if request.method == 'POST':
        return checkout()
    return render_template('checkout.html')

def checkout():
    if 'username' not in session:
        flash('You must be logged in to checkout.', 'error')
        return redirect(url_for('login'))
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('cart'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM Users WHERE username=%s", (session['username'],))
    user = cursor.fetchone()
    user_id = user['id']
    for game_id in cart.keys():
        cursor.execute(
            "INSERT IGNORE INTO Personal_Library (user_id, game_id) VALUES (%s, %s)",
            (user_id, int(game_id))
        )
    mysql.connection.commit()
    session['cart'] = {}
    flash('Checkout successful! Games added to your library.', 'success')
    return redirect(url_for('library'))


if __name__ == "__main__":
    app.run(debug=True)
