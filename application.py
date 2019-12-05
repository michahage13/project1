import os
import json

from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import error, login_required, bookapi
import requests
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    #Identify current User
    currUser = db.execute("SELECT name FROM users WHERE id = :id", {"id": session["user_id"]}).fetchall()
    currUser = currUser[0]["name"]
    #if Search form is submitted
    if request.method == "POST":
        option = request.form.get("option")
        value = request.form.get("value")
        res = []
        #Check form dropdown - Which search option was chosen
        if option == "isbn":
            res = db.execute("SELECT * FROM books WHERE isbn ILIKE :val", {"val": '%' + value + '%'}).fetchall()
        elif option == "title":
            res = db.execute("SELECT * FROM books WHERE title ILIKE :val", {"val": '%' + value + '%'}).fetchall()
        elif option == "author":
            res = db.execute("SELECT * FROM books WHERE author ILIKE :val", {"val": '%' + value + '%'}).fetchall()
        elif option == "year":
            res = db.execute("SELECT * FROM books WHERE year ILIKE :val", {"val": '%' + value + '%'}).fetchall()
        else:
            return error("Please provide a valid search")
        #In case no books were found
        if res == []:
            return error("No books found")
        return render_template("index.html", user=currUser, result=res)
    #if accesses via GET method
    else:
        return render_template("index.html", user=currUser)

@app.route("/book/<isbn>", methods=["GET", "POST"])
def book(isbn):
    #Identify current User
    currUser = db.execute("SELECT name FROM users WHERE id = :id", {"id": session["user_id"]}).fetchall()
    currUser = currUser[0]["name"]
    goodread = goodreads(isbn)
    #get book data
    res = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    if res == []:
        return error("Book page not found")
    #get all reviews and check if current user provided review
    userrev = rev = db.execute("SELECT rating, comment FROM userreviews \
    WHERE userid = :id AND bookisbn = :isbn", {"id": session["user_id"], "isbn": res[0]["isbn"]}).fetchall()
    allrev = db.execute("SELECT rating, comment, usname FROM userreviews \
    WHERE bookisbn = :isbn", {"isbn": res[0]["isbn"]}).fetchall()
    #boolean condition for dynamic html, false when no review was submitted by user
    checkrev = False
    # If user already has submitted a review, change boolean so no form will be displayed
    if userrev != []:
        checkrev = True

    #if book review was submitted
    if request.method == "POST":
        rating = request.form.get("rating") or None
        comment = request.form.get("comment") or None
        if rating == None or comment == None:
            return error("No review provided")
        rating = int(rating)
        if userrev == []:
            db.execute("INSERT INTO userreviews (rating, comment, bookisbn, userid, usname)\
            VALUES (:rating, :comment, :bookisbn, :userid, :usname)", \
            {"rating": rating, "comment": comment, "bookisbn": res[0]["isbn"], "userid": session["user_id"], "usname": currUser})
            db.commit()
            checkrev = True
            return book(isbn)
    return render_template("book.html", result=res, checkrev=checkrev, rev=userrev, allrev=allrev, goodread=goodread)


@app.route("/register", methods=["GET", "POST"])
def register():
    #forget any User ID
    session.clear()

    #route is accessed by submitting registration form
    if request.method == "POST":
        #Check form validity
        if not request.form.get("username"):
            return error("Please provide a username", 400)
        if not request.form.get("password"):
            return error("Please provide a password", 400)
        if request.form.get("password") != request.form.get("confirmation"):
            return error("Passwords do not match, try again!")
        #Get user Data from form, store in variables and hash pw and check availability
        pwhash = generate_password_hash(request.form.get("password"))
        name = request.form.get("username")
        checkname = db.execute("SELECT * FROM users WHERE name = :name", {"name": name}).fetchall()
        if len(checkname) != 0:
            return error("Username is already taken!", 400)
        #add user to DATABASE
        db.execute("INSERT INTO users(name, password) VALUES (:name, :password)", {"name": name, "password": pwhash})
        db.commit()
        #Query Database for User to proceed with Login (also verify succesful entry into DB)
        rows = db.execute("SELECT * FROM users WHERE name = :name", {"name": name}).fetchall()
        session["user_id"] = rows[0]["id"]

        return redirect("/")

    #route is accessed via GET method
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        #check form validity
        if not request.form.get("username"):
            return error("No username was provided", 400)
        name = request.form.get("username")
        if not request.form.get("password"):
            return error("No password was provided", 400)
        pw = request.form.get("password")
        #Query DB for Username and check validity
        rows = db.execute("SELECT * FROM users WHERE name = :username", {"username": name}).fetchall()
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], pw):
            return error("Invalid username or password", 400)
        #Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    #Request method GET
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/api/<isbn>", methods=["GET"])
def api(isbn):
    #get data from book table
    resbook = db.execute("SELECT title, author, year, isbn \
                        FROM books  WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    #get number of reviews and average ratings from userreviews table
    revcount = db.execute("SELECT COUNT(comment) FROM userreviews WHERE bookisbn = :isbn", {"isbn": isbn}).scalar()
    revavg = db.execute("SELECT AVG(rating) FROM userreviews WHERE bookisbn = :isbn", {"isbn": isbn}).scalar()
    if resbook is None or revcount is None or revavg is None:
        return jsonify({"error": "Book was not found"}), 422
    return jsonify({
        "title": resbook[0][0],
        "author": resbook[0][1],
        "year": resbook[0][2],
        "isbn": resbook[0][3],
        "review_count": revcount,
        "average_score": float(revavg)
    })

# goodreads API route - get goodreads data
def goodreads(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json",\
                        params={"key": "sDf3war3RwIdFd2xkeAA", "isbns": isbn})
    return res.json()
