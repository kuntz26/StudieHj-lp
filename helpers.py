from functools import wraps
from flask import redirect, session, render_template
from werkzeug.security import check_password_hash
import sqlite3

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


def parse_number(value):
    try:
        return int(value) if value else 0
    except ValueError:
        return 0


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


def check_password(personid: int, password: str):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    rows = cur.execute("SELECT password FROM login WHERE personid = ?", (personid,))
    if check_password_hash(rows.fetchone()[0], password):
        conn.close()
        return True
    conn.close()
    return False


def get_posts(username: str):
    posts = list()
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, date, (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                            FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                            WHERE people.username = ? ORDER BY date DESC""", (username,))
    for row in rows:
        posts.append(dict(row))
    conn.close()
    return posts