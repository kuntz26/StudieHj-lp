from functools import wraps
from flask import redirect, session, render_template
from werkzeug.security import check_password_hash
import sqlite3

# Makes routes only available if the user i logged in
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Trying to turn a str into int
def parse_number(value):
    try:
        return int(value) if value else 0
    except ValueError:
        return 0


# When errors happen, this is a fun way to show the error. It is just a placeholder
def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


# Checks the database if the password for a specific user is correct
def check_password(personid: int, password: str):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    rows = cur.execute("SELECT password FROM login WHERE personid = ?", (personid,))
    if check_password_hash(rows.fetchone()[0], password):
        conn.close()
        return True
    conn.close()
    return False


# Get all the posts from a user. Ordered by the date written
def get_posts(username: str):
    posts = list()
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if username:
        rows = cur.execute("""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, people.grade AS grade, date, 
                                (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                                FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                                WHERE people.username = ? ORDER BY date DESC""", (username,))
        posts = [dict(row) for row in rows]
    else:
        rows = cur.execute("""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, people.grade AS grade, date, 
                                (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                                FROM publicMessages JOIN people ON publicMessages.senderid = people.id  JOIN category ON publicMessages.categoryid = category.id 
                                ORDER BY RANDOM()""")
        posts = [dict(row) for row in rows]
    conn.close()
    return posts