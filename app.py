import csv, sqlite3, os, uuid
from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session
from bank_transactions import Transactions
from helpers import apology, parse_number, login_required
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure upload file path flask
app.config['UPLOAD_FOLDER'] = "./static/uploadfiles"


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
        if request.form.get('udgifter'):
            categories = ["Indtægter", "Udgifter"]
        else:
            categories = ["Indtægter", "Bolig", "Øvrige_faste", "Transport", "Mad", "Diverse", "Gældsafvikling"]
        
        income_expences = dict()
        for category in categories:
            income_expences[category] = parse_number(request.form.get(category.lower()))
            print(income_expences[category])
        
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
        rows = cur.execute("SELECT id, username, email, password, filename FROM people, login WHERE people.id = login.personid AND email = ?", (email,))
        output = list(rows)
        if len(output) != 1:
            conn.close()
            return apology("Konto med denne email eksisterer ikke", code=403)
        if not check_password_hash(output[0][3], password):
            conn.close()
            return apology("Email og password matcher ikke", code=403)
        
        session["user_id"] = output[0][0]
        session["username"] = output[0][1]
        if logged_file := output[0][4]:
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

# TODO: Add public messages
@app.route("/myaccount", methods=["GET", "POST"])
def myaccount():
    if request.method == "GET":
        if session.get("user_id"):
            return render_template("myaccount.html", username=session["username"], user_id=session["user_id"])
        return apology("Not authorized", code=401)
    else:
        return apology("Not made yet")