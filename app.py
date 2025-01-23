import csv, sqlite3, os, secrets, uuid, html
from datetime import timedelta
from flask import Flask, redirect, render_template, request, session, url_for, send_from_directory, jsonify
from flask_session import Session
from bank_transactions import Transactions
from helpers import apology, parse_number, login_required, check_password, get_posts
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
Session(app)

# Configure upload file path flask
app.config['UPLOAD_FOLDER'] = "./static/uploadfiles"


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.errorhandler(404)
def notfount(e):
    return apology("URL not found", 404)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/budget", methods=["GET", "POST"])
def budget():
    filename = ""
    if request.method == "GET":
        if not (filename := session.get("filename")):
            return render_template("budget.html", error=request.args.get("error"))
        filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    else:
        form_type = request.form.get("form_type")
        if form_type == "simple":
            categories = ["Indtægter", "Udgifter"]
        elif form_type == "advanced":
            categories = ["Indtægter", "Bolig", "Øvrige_faste", "Transport", "Mad", "Diverse", "Gældsafvikling"]
        else:
            return apology("Internal server error", 500)
        
        income_expences = dict()
        for category in categories:
            income_expences[category] = parse_number(request.form.get(category.lower()))
        
        filename = f"{uuid.uuid4().hex}_self_input" + ".csv"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ["Hovedkategori", "Beløb"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            for name in income_expences:
                writer.writerow({fieldnames[0]: name, fieldnames[1]: income_expences[name]})
        
        if old_file := session.get("filename"):
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old_file))
        session["filename"] = filename
        
        if session.get("user_id"):
            conn = sqlite3.connect("database.db")
            cur = conn.cursor()
            cur.execute("UPDATE people SET filename = ? WHERE id = ?", (filename, session["user_id"]))
            conn.commit()
            conn.close()
        
        filename = filepath
    
    if filename:
        group = "Hovedkategori"
        transactions = Transactions(filename)
        transaction_dict_list = list()
        transaction_dict_list.append(transactions.transactions(group))
        picture_path = os.path.join(app.root_path, "static", "pictures", f"{uuid.uuid4().hex}_picture.html")
        transaction_pic_name = transactions.makePlot(transaction_dict_list[0][group], picture_path)
        if old_picture := session.get("picture_path"):
            os.remove(old_picture)
        session["picture_path"] = picture_path
        picture_url = url_for('static', filename=f'pictures/{os.path.basename(picture_path)}')
        total = 0
        for key in transaction_dict_list[0][group]:
            total += transaction_dict_list[0][group][key]
            total = round(total)
        transaction_dict_list[0][group]["Rest beløb"] = total
        return render_template("budget.html", error=request.args.get("error"), transactions=transaction_dict_list, pictures=picture_url)
    return render_template("budget.html", error=request.args.get("error"))


@app.route("/uploadfile", methods=["GET", "POST"])
def upload_file():
    if request.method == "GET":
        return apology("404 Not Found", code=404)
    
    file = request.files.get("file")
    if not file:
        print("Not working")
        return apology("Internal error", code=500)
    if file is None or file.filename == "":
        return redirect("/budget?error=Ingen fil uploaded")
    if not file.filename.endswith(".csv"): # Can use regex: re.search(r"^.+\.csv$", file.filename)
        return redirect("/budget?error=Uploaded er ikke en csv fil", error="")
    filename = uuid.uuid4().hex + "_file_upload" + ".csv"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    
    if old_file := session.pop("filename", None):
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old_file))
    
    session["filename"] = filename
    if session.get("user_id"):
        # Add to database
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        rows = cur.execute("SELECT filename FROM people WHERE id = ?", (session["user_id"],))
        if old_file := rows.fetchone():
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old_file[0]))
            except:
                pass
        cur.execute("UPDATE people SET filename = ? WHERE id = ?", (filename, session["user_id"]))
        conn.commit()
        conn.close()
    return redirect("/budget")


@app.route("/budgethjælp")
def budget_hjælp():
    return render_template("budgethjælp.html")


@app.route("/suhjælp")
def su_hjælp():
    return render_template("suhjælp.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect("/")
    if request.method == "GET":
        return render_template("login.html")
    else:
        if not (email := request.form.get("email")):
            return apology("Email ikke givet", code=403)
        if not (password := request.form.get("password")):
            return apology("Password ikke givet", code=403)
        
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        rows = cur.execute("SELECT id, username, email, filename FROM people, login WHERE people.id = login.personid AND email = ?", (email,))
        output = list(rows)
        if len(output) != 1:
            conn.close()
            return apology("Konto med denne email eksisterer ikke", code=403)
        if not check_password(output[0][0], password):
            conn.close()
            return apology("Forkert password")
        
        session["user_id"] = output[0][0]
        session["username"] = output[0][1]
#        if request.form.get("remember_me") == "on":
#            session.permanent = True  # Default session behavior
#        else:
#            session.permanent = False  # Make the session non-persistent
        if logged_file := output[0][3]:
            if filename := session.get("filename"):
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            session["filename"] = logged_file
        else:
            if filename := session.get("filename"):
                cur.execute("UPDATE people SET filename = ? WHERE id = ?", (filename, session["user_id"]))
                conn.commit()
        conn.close()
        return redirect("/")


@app.route("/logout")
def logout():
    if picture_path := session.get("picture_path"):
        os.remove(picture_path)
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if password != confirm_password:
            return redirect("/register")
        if username is None or email is None or password is None:
            return apology("Brugernavn, email og/eller password mangler")
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        rows = cur.execute("SELECT email FROM login WHERE email = ?", (email,))
        if rows.fetchone():
            return apology("Email allerede brugt!", code=409)
        rows = cur.execute("SELECT username FROM people WHERE username = ?", (username,))
        if rows.fetchone():
            return apology("Brugernavn i brug allerede")
        
        if filename := session.get("filename"):
            cur.execute("INSERT INTO people(username, filename) VALUES(?, ?)", (username, filename))
        else:
            cur.execute("INSERT INTO people(username) VALUES(?)", (username,))
        
        session["user_id"] = int(cur.lastrowid)
        session["username"] = username
        cur.execute("INSERT INTO login(personid, email, password) VALUES(?, ?, ?)", (session["user_id"], email, generate_password_hash(password)))
        conn.commit()
        conn.close()
        return redirect("/")


@app.route("/myaccount", methods=["GET", "POST"])
@login_required
def myaccount():
    render = render_template("myaccount.html", username=session["username"], user_id=session["user_id"], posts=get_posts(session["username"]))
    render_success = render_template("myaccount.html", username=session["username"], user_id=session["user_id"], posts=get_posts(session["username"]), message="Success")
    if request.method == "GET":
        return render
    else:
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        match request.form.get("form_type"):
            case "username_change":
                if not check_password(session["user_id"], request.form.get("password")):
                    conn.close()
                    return apology("Wrong password")
                if new_username := request.form.get("newusername"):
                    cur.execute("UPDATE people SET username = ? WHERE id = ?", (new_username, session["user_id"]))
                    conn.commit()
                    conn.close()
                    session["username"] = new_username
                    return render_success
                                
            case "password_change":
                new_password = request.form.get("newpassword")
                if new_password == request.form.get("confirmpassword"):
                    if check_password(session["user_id"], request.form.get("oldpassword")):
                        print(new_password)
                        cur.execute("UPDATE login SET password = ? WHERE personid = ?", (generate_password_hash(new_password), session["user_id"]))
                        conn.commit()
                        conn.close()
                        return render_success
                    conn.close()
                    return apology("Wrong password")
                conn.close()
                return apology("Passwords not matching")

            case "account_delete":
                if not check_password(session["user_id"], request.form.get("password")):
                    conn.close()
                    return apology("Wrong password")
                # Delete files in people.filename and
                if session.get("picture_path"):
                    try:
                        os.remove("static/pictures/" + session["picture_path"])
                    except:
                        pass
                if session.get("filename"):
                    try:
                        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], session["filename"]))
                    except:
                        pass
                cur.execute("DELETE FROM login WHERE personid = ?", (session["user_id"],))
                cur.execute("UPDATE people SET username = 'deleted' WHERE id = ?", (session["user_id"],))
                conn.commit()
                session.clear()
                conn.close()
                return redirect("/")
            
            case _:
                conn.close()
                return apology("Internal server error", 500)
        conn.close()


@app.route("/accounts/<username>")
def account(username: str):
    posts = get_posts(username)
    return render_template("account.html", posts=posts, username=username)


@app.route("/post/<post_id>", methods=["GET", "POST"])
def messages(post_id: int):
    if request.method == "GET":
        comments = list()
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, date, (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                                    FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                                    WHERE publicMessages.id = ? ORDER BY date DESC""", (post_id,))
        post = dict(rows.fetchone())
        rows = cur.execute("SELECT date, comment, people.username AS username FROM comments, people WHERE people.id = comments.senderid AND comments.messageid = ? ORDER BY date ASC", (post_id,))
        for row in rows:
            temp = dict(row)
            temp["comment"] = html.escape(temp["comment"])
            comments.append(temp)
        return render_template("post.html", post=post, comments=comments, post_id=post_id)
    
    if session.get("user_id"):
        if (comment := request.form.get("comment")) and (message_id := request.form.get("messageid")):
            conn = sqlite3.connect("database.db")
            cur = conn.cursor()
            cur.execute("INSERT INTO comments(date, messageid, comment, senderid) VALUES((SELECT DATETIME('now', 'localtime')), ?, ?, ?)", (message_id, comment, session["user_id"]))
            conn.commit()
            conn.close()
            return redirect("/post/" + post_id)


@app.route('/postuploads/<filename>')
def uploaded_file(filename: str):
    return send_from_directory('postuploads', filename)


@app.route("/lektiehjælp")
def lektiehjælp():
    search = request.args.get("search")
    searchcriteria = request.args.get("searchcriteria")

    if searchcriteria == "newest":
        order = "date DESC"
    elif searchcriteria == "popular":
        order = "comment_count DESC"
    else:
        order = "RANDOM()"
    
    if search and search != "None":
        where = f"WHERE message LIKE ?"
    else:
        where = ""

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT name FROM category")
    categories = [dict(row) for row in rows.fetchall()]

    print(where, order)
    
    posts = list()
    rows = cur.execute(f"""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, date, (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                        FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                        {where} ORDER BY {order} LIMIT 20""", (f"%{search}%",) if where else ())

    for row in rows:
        posts.append(dict(row))
    conn.close()
    return render_template("lektiehjælp.html", posts=posts, categories=categories)


@app.route("/lektiehjælp/<category>")
def lektiehjælp_category(category):
    search = request.args.get("search")
    searchcriteria = request.args.get("searchcriteria")

    if searchcriteria == "newest":
        order = "date DESC"
    elif searchcriteria == "popular":
        order = "comment_count DESC"
    else:
        order = "RANDOM()"
    
    if search and search != "None":
        where = "AND message LIKE ?"
    else:
        where = ""
    
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT name FROM category")
    categories = [dict(row) for row in rows.fetchall()]

    posts = list()
    rows = cur.execute(f"""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, date, (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                        FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                        WHERE category_name = ? {where} ORDER BY {order} LIMIT 20""", (category, f"%{search}%") if where else (category,))

    for row in rows:
        posts.append(dict(row))
    conn.close()
    return render_template("lektiehjælp_category.html", posts=posts, categories=categories, category=category)


@app.route("/lektiehjælp/writepost", methods=["GET", "POST"])
@login_required
def writepost():
    picture_formats = (".png", ".jpg", ".jpeg", ".svg")
    if not session.get("user_id"):
        return redirect("/")
    if request.method == "GET":
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("SELECT name FROM category")
        categories = [dict(row) for row in rows]
        conn.close()
        return render_template("writepost.html", categories=categories)

    picture = request.files.get("picture", None)
    header = request.form.get("header")
    message = request.form.get("message")
    category = request.form.get("category")
    if not (header and message and category):
        return apology("Internal server error", 500)
    if picture:
        format_type = ""
        for format in picture_formats:
            if picture.filename.endswith(format):
                format_type = format
        if format_type:
            filename = uuid.uuid4().hex + "_post_upload" + format_type
            picture.save("postuploads/" + filename)
    
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM category WHERE name = ?", (category,))
    category_id = cur.fetchone()[0]

    if picture:
        cur.execute("INSERT INTO publicMessages(senderid, header, message, categoryid, date, picturename) VALUES(?, ?, ?, ?, (SELECT DATETIME('now', 'localtime')), ?)", (session["user_id"], header, message, category_id, filename))
        post_id = cur.lastrowid
    else:
        cur.execute("INSERT INTO publicMessages(senderid, header, message, categoryid, date) VALUES(?, ?, ?, ?, (SELECT DATETIME('now', 'localtime')))", (session["user_id"], header, message, category_id))
        post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return redirect("/post/" + str(post_id))


@app.route("/privatemessages")
@login_required
def private_messages():
    messages = list()
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = """SELECT 
                CASE 
                    WHEN privateMessages.senderid = ? THEN (SELECT username FROM people WHERE id = privateMessages.recipientid)
                    WHEN privateMessages.recipientid = ? THEN (SELECT username FROM people WHERE id = privateMessages.senderid)
                END AS other_username, 
                people.username AS username, 
                MAX(privateMessages.date) AS latest_date, 
                (SELECT message 
                FROM privateMessages 
                WHERE (senderid = privateMessages.senderid AND recipientid = privateMessages.recipientid) 
                    OR (senderid = privateMessages.recipientid AND recipientid = privateMessages.senderid)
                ORDER BY date DESC 
                LIMIT 1) AS message
            FROM privateMessages
            INNER JOIN people ON people.id = privateMessages.senderid
            WHERE privateMessages.senderid = ? OR privateMessages.recipientid = ? 
            """
    rows = cur.execute(query, (session["user_id"],)*4)
    for row in rows:
        messages.append(dict(row))
    conn.close()
    if len(messages) < 2 and messages[0]["message"] == None:
        messages = None

    return render_template("privatemessages.html", messages=messages)


@app.route("/privatemessages/write", methods=["GET", "POST"])
@login_required
def writemessage():
    if request.method == "GET":
        return render_template("privatemessage_write.html")
    
    username = request.form.get("username")
    message = request.form.get("message")
    if not (username and message):
        return apology("Internal server error", 500)
    
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    rows = cur.execute("SELECT id FROM people WHERE username = ?", (username,))
    if not (recipient_id := rows.fetchone()[0]):
        return render_template("privatemessage_write.html", error="Username does not exist")
    
    cur.execute("INSERT INTO privateMessages(senderid, recipientid, message, date) VALUES(?, ?, ?, (SELECT DATETIME('now', 'localtime')))", (session["user_id"], recipient_id, message))
    conn.commit()
    conn.close()
    return redirect("/privatemessages/" + username)


@app.route("/privatemessages/<username>")
@login_required
def private_messages_user(username: str):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = """SELECT senderid, message, date, username FROM privateMessages
            INNER JOIN people ON people.id = senderid
            WHERE (privateMessages.senderid = ? OR privateMessages.recipientid = ?) AND (recipientid = (SELECT id FROM people WHERE username = ?) OR senderid = (SELECT id FROM people WHERE username = ?))
            """
    rows = cur.execute(query, (session["user_id"], session["user_id"], username, username))
    messages = [dict(row) for row in rows]
    conn.close()
    return render_template("privatemessage.html", messages=messages, other_username=username)


@app.route("/checkusername/<username>")
def check_username(username):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    result = cur.execute("SELECT username FROM people WHERE username = ?", (username,)).fetchone()
    conn.close()

    if result:
        print("Success")
        return jsonify({'valid': True})
    return jsonify({'valid': False})