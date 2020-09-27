import os
import requests

from flask import Flask,render_template,session,request,redirect,url_for,jsonify,abort,Response
from cs50 import sql
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.secret_key = 'BOOKSFORLIFE'

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

@app.route("/")
def index():
    return render_template('main.html')

@app.after_request
def after_request(response):
	response.headers.add('Cache-Control','no-store,no-cache,must-revalidate,post-check=0,pre-check=0')
	return response

@app.route("/login")
def login():
	if "user" in session:
		return redirect('/user')
	else:
		return render_template('login.html')

@app.route("/logging",methods=["POST"])
def logging():
	u_id=request.form.get("id")
	pword=request.form.get("password")
	user=db.execute("SELECT user_id FROM users WHERE user_id=:user_id AND password=:password",{"user_id":u_id,"password":pword}).fetchone()
	if user is None:
		return render_template("mypage.html",title="ERROR",message="ERROR!...No such user found")
	session["user"]=user
	return redirect(url_for("user"))

@app.route("/registering",methods=["POST"])
def registering():
	user_id=request.form.get("id")
	password=request.form.get("password")
	users=db.execute("SELECT * FROM users WHERE user_id=:user_id",{"user_id":user_id}).fetchall()
	if len(users) >0:
		return render_template("mypage.html",title="ERROR",message="Username Already Taken...")
	db.execute("INSERT INTO users(user_id,password) VALUES (:user_id,:password)",{"user_id":user_id,"password":password})
	db.commit()
	return render_template("mypage.html",title="Successful",message="Registeration Successful!....")

@app.route("/user")
def user():
	if "user" in session:
		user=session["user"]
		name=str(user)
		name=name[2:-3]
		books=db.execute("SELECT * FROM books WHERE id>1").fetchall()
		return render_template("books.html",user=name,books=books)
	else:
		return redirect('/login')

@app.route("/logout")
def logout():
	session.pop('user',None)
	return redirect(url_for('login'))

@app.route("/search",methods=["POST"])
def search():
	user=session["user"]
	name=str(user)
	name=name[2:-3]
	book=request.form.get("book_info")
	books=db.execute("SELECT * FROM books WHERE title LIKE '%"+book+"%'").fetchall()
	if len(books) >0:
		return render_template("books.html",user=name,books=books)
	books=db.execute("SELECT * FROM books WHERE author LIKE '%"+book+"%'").fetchall()
	if len(books) >0:
		return render_template("books.html",user=name,books=books)
	books=db.execute("SELECT * FROM books WHERE isbn LIKE '%"+book+"%'").fetchall()
	if len(books) >0:
		return render_template("books.html",user=name,books=books)
	return render_template("books.html",user=name,books=None)

@app.route("/search/<int:selected_book>")
def details(selected_book):
	if "user" in session:
		book_id=db.execute("SELECT * FROM books WHERE id=:id",{"id":selected_book}).fetchone()
		all_review=db.execute("SELECT * FROM reviews WHERE book_id=:book_id",{"book_id":selected_book}).fetchall()
		res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "mOeblj2oKKrPomFqBUAyA", 
			"isbns": book_id.isbn})
		data=res.json()
		mybook=data["books"]
		for book in mybook:
			average_rating=book["average_rating"]
			number_of_ratings=book["work_ratings_count"]
		if len(all_review) >0:
			return render_template("detail.html",book=book_id,all_review=all_review,a=average_rating,n=number_of_ratings)
		return render_template("detail.html",book=book_id,all_review=None,a=average_rating,n=number_of_ratings)
	else:
		return redirect(url_for('login'))

@app.route("/search/<int:book_id>",methods=["POST"])
def submit_rev(book_id):
	user=session["user"]
	user_id=str(user)
	user_id=user_id[2:-3]
	review_given=db.execute("SELECT * FROM reviews WHERE book_id=:book_id AND user_id=:user_id",{"user_id":user_id,"book_id":book_id}).fetchall()
	if len(review_given) >0:
		return render_template("mypage.html",title="Already Done",message="You have already submitted review for this book...")
	option=request.form['star']
	if option=='star1':
		rating=5
	elif option=='star2':
		rating=4
	elif option=='star3':
		rating=3
	elif option=='star4':
		rating=2
	else:
		rating=1
	review=request.form.get("review")
	db.execute("INSERT INTO reviews(user_id,book_id,review,rating) VALUES (:user_id,:book_id,:review,:rating)",{"user_id":user_id,"book_id":book_id,"review":review,"rating":rating})
	db.commit()
	return render_template("mypage.html",title="Successful",message="Review submission successful!..")
		
@app.route("/api/<string:isbn>")
def api(isbn):
	isbn=str(isbn)
	book=db.execute("SELECT * FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
	if book is None:
		# return jsonify({"error":"Invalid ISBN number"}),404
		abort(404)
	count=db.execute("SELECT COUNT(*) FROM reviews WHERE book_id=:book_id",{"book_id":book.id}).fetchall()
	count=str(count)
	count=count[2:-3]
	avg=db.execute("SELECT ROUND(AVG(rating),1) FROM reviews WHERE book_id=:book_id",{"book_id":book.id}).fetchall()
	avg=str(avg)
	avg=avg[11:-5]
	return jsonify({
	 	"title" : book.title,
	 	"author" : book.author,
	 	"year" : book.year,
	 	"isbn" : book.isbn,
		"review_count" : count,
	 	"average_score" : avg
	 })

if __name__=="__main__":
	main()