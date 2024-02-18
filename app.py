import os
import datetime

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Custom filter
app.jinja_env.filters["usd"] = usd

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Index route
@app.route("/")
@login_required
def index():
    user_id = session["user_id"]

    transactions_db = db.execute("SELECT symbol, SUM(shares) AS shares, price FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0 ORDER BY price DESC", user_id)
    cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = cash_db[0]["cash"]

    return render_template("index.html", database = transactions_db, cash  = cash)

# Buy route
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        stock = lookup(symbol.upper())

        if stock is None:
            return apology("Symbol does not exist", 400)

        if shares < 0:
            return apology("Invalid number of shares")

        transaction_value = shares * stock["price"]
        user_id = session["user_id"]
        user_cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        user_cash = user_cash_db[0]["cash"]

        if user_cash < transaction_value:
            return apology("Not enough money")

        updated_cash = user_cash - transaction_value
        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)

        date = datetime.datetime.now()
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)", user_id, stock["symbol"], shares, stock["price"], date)

        flash("Bought!")
        return redirect("/")

# History route
@app.route("/history")
@login_required
def history():
    user_id  = session["user_id"]
    transactions_db = db.execute("SELECT * FROM transactions WHERE  user_id = :id", id=user_id )
    return render_template("history.html", transactions = transactions_db)

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = db.execute("SELECT * FROM users WHERE username = ?", username)

        if not user or not check_password_hash(user[0]["hash"], password):
            return apology("Invalid username and/or password", 403)

        session["user_id"] = user[0]["id"]
        return redirect("/")

    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("Must provide username, password, and confirmation", 403)

        if password != confirmation:
            return apology("Passwords must match", 403)

        hash = generate_password_hash(password)
        try:
            user_id = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
        except:
            return apology("Username already exists", 403)

        session["user_id"] = user_id
        return redirect("/")

    return render_template("register.html")

# Quote route
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Must provide symbol", 400)

        stock = lookup(symbol.upper())
        if stock is None:
            return apology("Symbol does not exist", 400)

        return render_template("quoted.html", name=stock["name"], price=stock["price"], symbol=stock["symbol"])

# Sell route (TODO)
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        user_id = session["user_id"]
        symbols_user = db.execute("SELECT symbol FROM transactions WHERE user_id = :id GROUP BY symbol HAVING SUM(shares) > 0", id=user_id)
        symbols = [row["symbol"] for row in symbols_user]
        return render_template("sell.html", symbols=symbols)
    else:
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        stock = lookup(symbol.upper())

        if stock is None:
            return apology("Symbol does not exist", 400)

        if shares < 0:
            return apology("Invalid number of shares")

        transaction_value = shares * stock["price"]
        user_id = session["user_id"]
        user_cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        user_cash = user_cash_db[0]["cash"]

        user_shares = db.execute('SELECT shares FROM transactions WHERE user_id= :id AND symbol = :symbol GROUP BY symbol ', id=user_id, symbol=symbol)
        user_real_shares = user_shares[0]["shares"]

        if shares > user_real_shares:
            return apology("Not enough shares")

        updated_cash = user_cash + transaction_value
        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)

        date = datetime.datetime.now()
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)", user_id, stock["symbol"], (-1)*shares, stock["price"], date)

        flash("Sold")
        return redirect("/")


# Run the application
if __name__ == "__main__":
    app.run(debug=True)
