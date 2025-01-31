import csv, sqlite3, os, secrets, uuid, html
from datetime import timedelta
from flask import Flask, redirect, render_template, request, session, url_for, send_from_directory, jsonify
from flask_session import Session
from bank_transactions import Transactions
from helpers import apology, parse_number, login_required, check_password, get_posts
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

# Flask configuration
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


# If the user tries to access a non-existant route, they will get this 404 error
@app.errorhandler(404)
def notfount(e):
    return apology("URL not found", 404)


# The start / welcome page
@app.route("/")
def index():
    # Gets random posts from the database
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("""SELECT people.username AS username, publicMessages.header AS header, publicMessages.message AS message, category.name AS category_name, people.grade AS grade,
                            publicMessages.date AS date, publicMessages.picturename AS picturename, (SELECT COUNT(id) FROM comments WHERE messageid = publicMessages.id) AS comment_count
                            FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON category.id = publicMessages.categoryid
                            ORDER BY RANDOM() LIMIT 20""")
    # Stores the posts in a dict
    posts = [dict(row) for row in rows]
    conn.close()
    return render_template("index.html", posts=posts)


# The budget calculating site
@app.route("/budget", methods=["GET", "POST"])
def budget():
    filename = ""
    # When the user opens the page via the URL
    if request.method == "GET":
        # Checks if the user has a "filename" stored in their cookies for their budget
        if not (filename := session.get("filename")):
            return render_template("budget.html", error=request.args.get("error"))
        filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    # When the user submits manually to the site their budget via the form
    else:
        form_type = request.form.get("form_type")
        if form_type == "simple":
            categories = ["Indtægter", "Udgifter"]
        elif form_type == "advanced":
            categories = ["Indtægter", "Bolig", "Øvrige_faste", "Transport", "Mad", "Diverse", "Gældsafvikling"]
        else:
            return apology("Internal server error", 500)
        
        # Makes a dict for the data from the form
        income_expences = dict()
        for category in categories:
            income_expences[category] = parse_number(request.form.get(category.lower()))
        
        filename = f"{uuid.uuid4().hex}_self_input" + ".csv"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        # Stores the dict data in a .csv file.
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ["Hovedkategori", "Beløb"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            for name in income_expences:
                writer.writerow({fieldnames[0]: name, fieldnames[1]: income_expences[name]})
        
        # Removes the old .csv file connected to the user to optimize space used by uploaded files and data
        if old_file := session.get("filename"):
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old_file))
        session["filename"] = filename
        
        # Stores the filename in the database if user is logged in
        if session.get("user_id"):
            conn = sqlite3.connect("database.db")
            cur = conn.cursor()
            cur.execute("UPDATE people SET filename = ? WHERE id = ?", (filename, session["user_id"]))
            conn.commit()
            conn.close()
        name_of_file = filename
        filename = filepath
    
    # Makes a plot and a dict of the data to show graphically to the user
    if filename:
        group = "Hovedkategori"
        try:
            transactions = Transactions(filename)
            transaction_dict_list = list()
            transaction_dict_list.append(transactions.transactions(group))
        except:
            os.remove(filename)
            if session.get("user_id"):
                conn = sqlite3.connect("database.db")
                cur = conn.cursor()
                cur.execute("DELETE filename FROM people WHERE filename = ?", (name_of_file,))
                conn.commit()
                conn.close()
            return render_template("budget.html", error="The file cannot be used")
        else:
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
            transaction_dict_list[0][group]["Rådighedsbeløb"] = total
            return render_template("budget.html", error=request.args.get("error"), transactions=transaction_dict_list, pictures=picture_url)
    return render_template("budget.html", error=request.args.get("error"))


# If the user uploads a .csv file from their bank
@app.route("/uploadfile", methods=["GET", "POST"])
def upload_file():
    # Error if the user assesses this route via the URL
    if request.method == "GET":
        return apology("404 Not Found", 404)
    
    # Checks if the file given is correct and saves it on the disk
    file = request.files.get("file")
    if not file:
        print("Not working")
        return apology("Internal error", code=500)
    if file is None or file.filename == "":
        return redirect("/budget?error=Ingen fil uploaded")
    if not file.filename.endswith(".csv"): # Can use regex: re.search(r"^.+\.csv$", file.filename)
        return redirect("/budget?error=Uploaded er ikke en csv fil")
    filename = uuid.uuid4().hex + "_file_upload" + ".csv"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    
    # Deletes the previously linked file if the user has a file linked to them
    if old_file := session.pop("filename", None):
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old_file))
    
    # Saves the filename of the new file to cookies
    session["filename"] = filename
    if session.get("user_id"):
        # Add to database if user logged in
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        rows = cur.execute("SELECT filename FROM people WHERE id = ?", (session["user_id"],))
        # If the user has a file saved in the database, it will be removed
        if old_file := rows.fetchone():
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old_file[0]))
            except:
                pass
        cur.execute("UPDATE people SET filename = ? WHERE id = ?", (filename, session["user_id"]))
        conn.commit()
        conn.close()
    return redirect("/budget")


# This is a static page
@app.route("/budgethjælp")
def budget_hjælp():
    return render_template("budgethjælp.html")


# This is a static page
@app.route("/suhjælp")
def su_hjælp():
    return render_template("suhjælp.html")


# This is a login page
@app.route("/login", methods=["GET", "POST"])
def login():
    # If the user is already logged in, they will be redirected to the start page
    if session.get("user_id"):
        return redirect("/")
    # If the user accesses this route via the URL
    if request.method == "GET":
        return render_template("login.html")
    
    # If the user sends data via the form
    else:
        # Checks that email and password is given
        if not (email := request.form.get("email")):
            return apology("Email ikke givet", code=403)
        if not (password := request.form.get("password")):
            return apology("Password ikke givet", code=403)
        
        # Checks the email and password given in the database and logs in if it is the correct values
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        rows = cur.execute("SELECT id, username, email, filename, grade FROM people, login WHERE people.id = login.personid AND email = ?", (email,))
        output = list(rows)
        if len(output) != 1:
            conn.close()
            return apology("Konto med denne email eksisterer ikke", code=403)
        if not check_password(output[0][0], password):
            conn.close()
            return apology("Forkert password")
        
        # Saves in cookies the userid, username and grade
        session["user_id"] = output[0][0]
        session["username"] = output[0][1]
        session["grade"] = output[0][4]
#        if request.form.get("remember_me") == "on":
#            session.permanent = True  # Default session behavior
#        else:
#            session.permanent = False  # Make the session non-persistent

        # If the user has a file saved in cookies already and they have a file saved in the database, then the file from cookies is deleted
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


# Clears all the cookies and deletes the graph file for the user, if they have one.
@app.route("/logout")
def logout():
    if picture_path := session.get("picture_path"):
        os.remove(picture_path)
    session.clear()
    return redirect("/")


# Makes an account for the user
@app.route("/register", methods=["GET", "POST"])
def register():
    # The different grades possible to pick
    grades = ("Folkeskole", "Gymnasie", "Universitet", "Erhvervsuddannelse", "Andet")
    # If the user is logged in, they are redirected to the start page
    if session.get("user_id"):
        return redirect("/")
    
    # If the route is accessed via the URL
    if request.method == "GET":
        return render_template("register.html")
    
    # If the route is accessed via sending data with a form
    else:
        # Saves the data given by the user and checks none of the values are empty
        username = request.form.get("username")
        grade = request.form.get("grade")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if password != confirm_password:
            return redirect("/register?error=Ikke samme passwords")
        if username is None or email is None or password is None or grade is None:
            return apology("Brugernavn, Niveau, email og/eller password mangler")
        if username == "Slettet":
            return apology("Username not possible", 500)
        # Checks if the grade chosen is one of the possible ones
        if grade not in grades:
            return apology("Internal server error", 500)

        # Emails and usernames are unique. Two can't use the same username or email. THis isi checked here
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        rows = cur.execute("SELECT email FROM login WHERE email = ?", (email,))
        if rows.fetchone():
            return apology("Email allerede brugt!", code=409)
        rows = cur.execute("SELECT username FROM people WHERE username = ?", (username,))
        if rows.fetchone():
            return apology("Brugernavn i brug allerede")
        
        # Makes an account with or without a file connected
        if filename := session.get("filename"):
            cur.execute("INSERT INTO people(username, filename, grade) VALUES(?, ?, ?)", (username, filename, grade))
        else:
            cur.execute("INSERT INTO people(username, grade) VALUES(?, ?)", (username, grade))
        
        # Saves the userid, username and grade in cookies
        session["user_id"] = int(cur.lastrowid)
        session["username"] = username
        session["grade"] = grade
        cur.execute("INSERT INTO login(personid, email, password) VALUES(?, ?, ?)", (session["user_id"], email, generate_password_hash(password)))
        conn.commit()
        conn.close()
        return redirect("/")


# Possibility to change values in their own account or check their own written posts
@app.route("/myaccount", methods=["GET", "POST"])
@login_required
def myaccount():
    # These are reused
    render = render_template("myaccount.html", username=session["username"], user_id=session["user_id"], posts=get_posts(session["username"]), grade=session["grade"])
    render_success = render_template("myaccount.html", username=session["username"], user_id=session["user_id"], posts=get_posts(session["username"]), grade=session["grade"], message="Success")
    # If the site is accessed via the URL
    if request.method == "GET":
        return render
    # If the site is accessed via sending data with a form
    else:
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        # The possibilities for the form_type are username_change, password_change, account_delete, grade_change
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
                cur.execute("UPDATE people SET username = 'Slettet' WHERE id = ?", (session["user_id"],))
                conn.commit()
                session.clear()
                conn.close()
                return redirect("/")
            
            case "grade_change":
                grades = ["Folkeskole", "Gymnasie", "Universitet", "Erhvervsuddannelse", "Andet"]
                if not check_password(session["user_id"], request.form.get("password")):
                    conn.close()
                    return apology("Wrong password")
                if new_grade := request.form.get("grade"):
                    if not new_grade in grades:
                        return apology("Internal server error", 500)
                    cur.execute("UPDATE people SET grade = ? WHERE id = ?", (new_grade, session["user_id"]))
                    conn.commit()
                    session["grade"] = new_grade
                    return render_success

            case _:
                conn.close()
                return apology("Internal server error", 500)
        conn.close()


# View posts from a specific user
@app.route("/accounts/<username>")
def account(username: str):
    return render_template("account.html", posts=get_posts(username), username=username)


# View a specific post and its comments
@app.route("/post/<post_id>", methods=["GET", "POST"])
def messages(post_id: int):
    # Shows the post and comments when route is accessed via the URL
    if request.method == "GET":
        comments = list()
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, date, (SELECT COUNT(*) FROM comments 
                                    WHERE messageid = publicMessages.id) AS comment_count 
                                    FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                                    WHERE publicMessages.id = ? ORDER BY date DESC""", (post_id,))
        post = dict(rows.fetchone())
        rows = cur.execute("SELECT date, comment, people.username AS username FROM comments, people WHERE people.id = comments.senderid AND comments.messageid = ? ORDER BY date ASC", (post_id,))
        for row in rows:
            temp = dict(row)
            temp["comment"] = html.escape(temp["comment"])
            comments.append(temp)
        return render_template("post.html", post=post, comments=comments, post_id=post_id)
    
    # If data is send via a form, that means someone wants to write a comment
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


# Shows posts either random or filtered, and shows categories available to search for
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
        where = f"WHERE (message LIKE ? OR header LIKE ?)"
    else:
        where = ""

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT name FROM category ORDER BY name")
    categories = [dict(row) for row in rows.fetchall()]
    rows = cur.execute(f"""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, date, people.grade AS grade,
                            (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                            FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                            {where} ORDER BY {order} LIMIT 20""", (f"%{search}%", f"%{search}%") if where else ())


    posts = [dict(row) for row in rows]
    conn.close()
    return render_template("lektiehjælp.html", posts=posts, categories=categories)


# Show posts in a specific category
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
        where = "AND (message LIKE ? OR header LIKE ?)"
    else:
        where = ""
    
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT name FROM category")
    categories = [dict(row) for row in rows.fetchall()]
    
    rows = cur.execute(f"""SELECT publicMessages.id AS id, username, header, message, category.name AS category_name, picturename, date, people.grade AS grade,
                            (SELECT COUNT(*) FROM comments WHERE messageid = publicMessages.id) AS comment_count 
                            FROM publicMessages JOIN people ON publicMessages.senderid = people.id JOIN category ON publicMessages.categoryid = category.id 
                            WHERE category_name = ? {where} ORDER BY {order} LIMIT 20""", (category, f"%{search}%", f"%{search}%") if where else (category,))

    # Saves the posts in a list of dicts
    posts = [dict(row) for row in rows]
    conn.close()
    return render_template("lektiehjælp_category.html", posts=posts, categories=categories, category=category)


# Writing a post
@app.route("/lektiehjælp/writepost", methods=["GET", "POST"])
@login_required
def writepost():
    # The accepted fileformats for the uploaded picture
    picture_formats = (".png", ".jpg", ".jpeg", ".svg")
    # Shows the form to upload data
    if request.method == "GET":
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("SELECT name FROM category")
        categories = [dict(row) for row in rows]
        conn.close()
        return render_template("writepost.html", categories=categories)

    # If the form is sent, the data is saved in variables and made sure they aren't empty
    picture = request.files.get("picture", None)
    header = request.form.get("header")
    message = request.form.get("message")
    category = request.form.get("category")
    if not (header and message and category):
        if not category:
            return render_template("writepost.html", error="Vælg en kategori")
        return apology("Internal server error", 500)
    # If a picture is uploaded, it is checked if valid and saves it
    if picture:
        filename = ""
        format_type = ""
        for format in picture_formats:
            if picture.filename.endswith(format):
                format_type = format
        if format_type:
            filename = uuid.uuid4().hex + "_post_upload" + format_type
            picture.save("postuploads/" + filename)
    
    # Gets the categoryid from the database for use
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM category WHERE name = ?", (category,))
    category_id = cur.fetchone()[0]

    # If a picture is uploaded, the database is updated with the filename and all other needed data, if not then the database is updated without the filename
    if picture:
        if not filename:
            return apology("Can only add pictures", 500)
        cur.execute("INSERT INTO publicMessages(senderid, header, message, categoryid, date, picturename) VALUES(?, ?, ?, ?, (SELECT DATETIME('now', 'localtime')), ?)", 
                    (session["user_id"], header, message, category_id, filename))
        post_id = cur.lastrowid
    else:
        cur.execute("INSERT INTO publicMessages(senderid, header, message, categoryid, date) VALUES(?, ?, ?, ?, (SELECT DATETIME('now', 'localtime')))", 
                    (session["user_id"], header, message, category_id))
        post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return redirect("/post/" + str(post_id))


# View the users a person has chatted with
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
                people.username AS username, MAX(privateMessages.date) AS latest_date, privateMessages.message AS message
                FROM privateMessages
                INNER JOIN people ON people.id = privateMessages.senderid
                WHERE privateMessages.senderid = ? OR privateMessages.recipientid = ?
                GROUP BY other_username ORDER BY privateMessages.date ASC"""
    rows = cur.execute(query, (session["user_id"],)*4)
    for row in rows:
        messages.append(dict(row))
    conn.close()
    if not len(messages) == 0:
        if len(messages) < 2 and messages[0]["message"] == None:
            messages = None
    else:
        messages = None

    print(messages)
    return render_template("privatemessages.html", messages=messages)


# Write a private message by a username
@app.route("/privatemessages/write", methods=["GET", "POST"])
@login_required
def writemessage():
    if request.method == "GET":
        return render_template("privatemessage_write.html")
    
    username = request.form.get("username")
    message = request.form.get("message")
    if not (username and message):
        return apology("Internal server error", 500)
    if username == "Slettet":
        return apology("Can't write to a deleted account")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    rows = cur.execute("SELECT id FROM people WHERE username = ?", (username,))
    if not (recipient_id := rows.fetchone()[0]):
        conn.close()
        return render_template("privatemessage_write.html", error="Username does not exist")
    
    cur.execute("INSERT INTO privateMessages(senderid, recipientid, message, date) VALUES(?, ?, ?, (SELECT DATETIME('now', 'localtime')))", 
                (session["user_id"], recipient_id, message))
    conn.commit()
    conn.close()
    return redirect("/privatemessages/" + username)


# Shows a whole chat with another user
@app.route("/privatemessages/<username>")
@login_required
def private_messages_user(username: str):
    if username == session["username"]:
        return apology("Internal server error", 500)
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = """SELECT senderid, message, date, username FROM privateMessages
                INNER JOIN people ON people.id = senderid
                WHERE (privateMessages.senderid = ? OR privateMessages.recipientid = ?) AND (recipientid = (SELECT id FROM people WHERE username = ?) OR 
                senderid = (SELECT id FROM people WHERE username = ?))"""
    rows = cur.execute(query, (session["user_id"], session["user_id"], username, username))
    messages = [dict(row) for row in rows]
    conn.close()
    return render_template("privatemessage.html", messages=messages, other_username=username)


# For the private messages, check if a username exists
@app.route("/checkusername/<username>")
def check_username(username):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    result = cur.execute("SELECT username FROM people WHERE username = ?", (username,)).fetchone()
    conn.close()

    if result and username != session.get("username"):
        return jsonify({'valid': True})
    return jsonify({'valid': False})