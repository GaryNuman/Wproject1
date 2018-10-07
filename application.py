import os
from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

app = Flask(__name__)

#prevent jsonify from sorting in alphabetical order
app.config['JSON_SORT_KEYS'] = False

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="Invalid username", link=url_for('index'))

        # ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="Invalid password", link=url_for('index'))

        # ensure password was confirmed
        elif request.form.get("password_conf") != request.form.get("password"):
            return render_template("error.html", message="Invalid password confirmation", link=url_for('index'))

        username = request.form.get("username")
        password = request.form.get("password")

		#check if username already in the database
        username_count = db.execute("SELECT COUNT(*) FROM users WHERE username = :username", {"username": username}).scalar()
                
        if username_count > 0 :
        	return render_template("error.html", message="Username already in use", link=url_for('index'))
        else:
	        # query to add user to database
	        result = db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
	        	{"username": username, "password": password})
	        db.commit()
           
        # remember which user has logged in
        user_id = db.execute("SELECT id_user FROM users WHERE username= :username", {"username":username}).scalar()
        session["id_user"] = user_id

        # redirect user to home page
        return render_template("search.html", loggedin = username)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("error.html", message="Invalid username/password", link=url_for('index'))

        username = request.form.get("username")
        password = request.form.get("password")
        
        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchall()

        # ensure username exists and password is correct
        if len(rows) != 1 or not password == rows[0]["password"]:
            return render_template("error.html", message="Invalid username/password", link=url_for('index'))

        # remember which user has logged in
        session["user_id"] = rows[0]["id_user"]

        # redirect user to home page
        return render_template("search.html", loggedin = username)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return render_template("index.html")

@app.route("/search", methods=["GET", "POST"])
def search():
	"""search for books in the database."""

    #if user reached route via POST (as by submitting a form via POST)
	if request.method == "POST":

        # ensure at least 1 search criteria was filled in
		if not request.form.get("isbn") and not request.form.get("title") and not request.form.get("author"):
			return render_template("error.html", message="Please provide a search criteria", link=url_for('search'))
		else:
			author = request.form.get("author")
			isbn = request.form.get("isbn")
			title = request.form.get("title")

			# query database for username
			#search for when only 1 input is given
			if not isbn and not title:
				books = db.execute("SELECT * FROM books WHERE lower(author) LIKE lower(concat('%',:author,'%'))", 
				{"author": author}).fetchall()
			if not isbn and not author:
				books = db.execute("SELECT * FROM books WHERE lower(title) LIKE lower(concat('%',:title,'%'))", 
				{"title": title}).fetchall()
			if not title and not author:
				books = db.execute("SELECT * FROM books WHERE lower(isbn) LIKE lower(concat('%',:isbn,'%'))", 
				{"isbn": isbn}).fetchall()
			#search for when 2 inputs are given
			elif not isbn:
				books = db.execute("SELECT * FROM books WHERE lower(title) LIKE lower(concat('%',:title,'%')) AND lower(author) LIKE lower(concat('%',:author, '%'))", 
				{"author": author, "title": title}).fetchall()
			elif not title:
				books = db.execute("SELECT * FROM books WHERE lower(author) LIKE lower(concat('%', :author, '%')) AND lower(isbn) LIKE lower(concat('%', :isbn, '%'))", 
				{"author": author, "isbn":isbn}).fetchall()
			elif not author:
				books = db.execute("SELECT * FROM books WHERE lower(title) LIKE lower(concat('%', :title, '%')) AND lower(isbn) LIKE lower(concat('%', :isbn, '%'))", 
 				{"isbn":isbn, "title": title}).fetchall()
			#search for when all inputs are given
			else: 
				books = db.execute("SELECT * FROM books WHERE lower(author) LIKE lower(concat('%',:author, '%')) AND lower(isbn) LIKE lower(concat('%',:isbn,'%')) AND lower(title) LIKE lower(concat('%',:title,'%'))", 
				{"author": author, "isbn":isbn, "title": title}).fetchall()
	
	        # # redirect user to book list page
			return render_template("bookList.html", books = books)

	#else if user reached route via GET (as by clicking a link or via redirect)
	else:
		return render_template("search.html")

@app.route("/bookPage/<string:isbn>", methods=["GET", "POST"])
def bookPage(isbn):

	if request.method == "POST" or "GET":
		book = db.execute("SELECT * FROM books WHERE isbn= :isbn", {"isbn":isbn}).fetchall()
		book_id = book[0]["id_book"]
		title = book [0]["title"] 
		author = book[0]["author"]
		year = book[0]["year"] 

		#get the book info from good reads api 
		res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "FG8F3FZTtXKHQkRkxyw", "isbns": isbn})

		if res.status_code != 200:
			raise Exception("REQUEST ERROR: Goodreads API request unsuccessful.")

		good_books= res.json()["books"][0]
		good_avg = good_books["average_rating"]
		good_count = good_books["ratings_count"]
		reviews = db.execute("SELECT * FROM review WHERE id_book = :book_id", {"book_id":book_id}).fetchall()
	
		return render_template("bookPage.html", title=title, isbn=isbn, author = author, year=year, reviews = reviews, good_avg = good_avg, good_count = good_count)
	
	# else if user reached route via GET
	else:
		return render_template("search.html")


@app.route("/review/<string:isbn>", methods=["POST", "GET"])
def review(isbn):

	if request.method == "POST":
		# database query for book info
		book = db.execute("SELECT * FROM books WHERE isbn= :isbn", {"isbn":isbn}).fetchall()
		book_id = book[0]["id_book"]
		title = book [0]["title"] 
		author = book[0]["author"] 

		return render_template("review.html", title=title, isbn=isbn, author = author)

	else:
		return render_template("search.html")


@app.route("/reviewed/<string:isbn>", methods=["POST", "GET"])
def reviewed(isbn):

	grade = request.form.get("grade")
	review_text = request.form.get("review_text")

	book = db.execute("SELECT id_book FROM books WHERE isbn= :isbn", {"isbn":isbn}).fetchone()
	id_book = int(book[0])

	print(id_book)
	print(grade)
	print(str(review_text))

	already = db.execute("SELECT * FROM review WHERE id_writer = :id_writer AND id_book = :id_book", {"id_writer": session["user_id"], "id_book": id_book}).fetchall()

	print(already)
	#add review to database
	if already == []:
		db.execute("INSERT INTO review (grade, review_text, id_writer, id_book) VALUES ({}, '{}' , {}, {})".format(int(grade), review_text, 7, id_book))
		db.commit()

		return render_template( 'search.html')

	else:
		return render_template("error.html", message="Only 1 review per person", link=url_for('search'))
		

	# # that to do with a GET request
	# else: 

#for method is GET return a JSON response
@app.route("/api/<string:isbn>", methods=["GET"])
def ISBNpage(isbn):

	# select from books db the id_book, title, author and year 
	book_data = db.execute("SELECT id_book, title, author, year FROM books WHERE isbn = :isbn LIMIT 1", {"isbn": isbn}).fetchone()

	if book_data is None:
		return jsonify({"error": "isbn not found"}), 422

	# select from review db the count and avg in 2 queries
	review_count= db.execute("SELECT COUNT(id_review) FROM review WHERE id_book = :id_book", {"id_book": book_data["id_book"]}).fetchone()
	review_avg= db.execute("SELECT ROUND(AVG(grade)::numeric,2) FROM review WHERE id_book = :id_book", {"id_book": book_data["id_book"]}).fetchone()
	if review_count or review_avg is None:
		review_count = [0]
		review_avg = [0]

	review_avg1 = float(review_avg[0])

	# return info in JSON format on method is GET
	return jsonify({
		"title": book_data["title"],
		"author": book_data["author"],
		"year": book_data["year"],
		"isbn": isbn,
		"review_count": review_count[0],
		"average_score": review_avg1
		})
