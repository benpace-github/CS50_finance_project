import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    user_stocks_0 = db.execute("SELECT ticker, shares FROM equity WHERE user_id=:user_id",
                               user_id=session["user_id"])
    # return a full listing of user stocks

    user_query_result_0 = db.execute("SELECT * FROM users WHERE id = :id",
                                     id=session["user_id"])
    user_info_0 = dict(user_query_result_0[0])
    user_cash_0 = float(user_info_0["cash"])
    # retrieve user information as dictionary

    equity_list = []
    user_total_value_0 = user_cash_0
    # initialize needed variables for loop

    for i in range(len(user_stocks_0)):

        equity_data = {}
        equity_data["ticker"] = user_stocks_0[i]["ticker"]
        equity_data["shares"] = user_stocks_0[i]["shares"]

        output_0 = lookup(user_stocks_0[i]["ticker"])
        # retreive symbol from user and attempt to retreive
        # info from API

        output_1 = dict(output_0)
        price_0 = float(output_1["price"])
        cash_value_0 = price_0 * int(user_stocks_0[i]["shares"])
        # retrieve api output and information from output

        equity_data["price"] = usd(price_0)
        equity_data["value"] = usd(cash_value_0)
        user_total_value_0 = user_total_value_0 + cash_value_0
        # use api information to retrieve current price and value

        equity_list.append(equity_data)
        # append to equity list

    return render_template("index.html", stock_list=equity_list, user_cash=usd(user_cash_0), total_value=usd(user_total_value_0))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "GET":
        return render_template("buy.html")

    if request.method == "POST":

        symbol_0 = request.form.get("symbol")
        shares_0 = int(request.form.get("shares"))
        output_0 = lookup(symbol_0)
        # retreive symbol from user and attempt to retreive
        # info from API

        if not output_0:
            return render_template("apology_buy.html", message="ERROR: Invalid ticker.")

        output_1 = dict(output_0)
        price_0 = float(output_1["price"])
        cash_value_0 = price_0 * shares_0
        # retrieve api output and information from output

        user_query_result_0 = db.execute("SELECT * FROM users WHERE id = :id",
                                         id=session["user_id"])
        user_info_0 = dict(user_query_result_0[0])
        user_cash_0 = float(user_info_0["cash"])
        # retrieve user information as dictionary

        if cash_value_0 > user_cash_0:
            return render_template("apology_buy.html", message="ERROR: Insufficient funds.")
        # checks is user is able to purchase given current funds

        user_cash_1 = user_cash_0 - cash_value_0
        # if user has sufficient cash subtract cash value

        equity_query_result_0 = db.execute("SELECT ticker FROM equity;")
        equity_list_0 = [list(equity_query_result_0[i].values()) for i in range(len(equity_query_result_0))]
        equity_list_1 = [i[0] for i in equity_list_0]
        # retrieve a list of current stocks owned by user

        if output_1["symbol"] in equity_list_1:

            ticker_query_result_0 = db.execute("SELECT * FROM equity WHERE user_id = :user_id AND ticker = :ticker",
                                               user_id=session["user_id"], ticker=output_1["symbol"])

            ticker_info_0 = dict(ticker_query_result_0[0])
            # if user currently owns stock add to purchased stock

            old_shares_0 = int(ticker_info_0["shares"])
            new_shares_0 = shares_0 + old_shares_0
            # add old shares to new shares

            db.execute("UPDATE equity SET shares = :shares WHERE user_id = :user_id AND ticker = :ticker",
                       shares=new_shares_0, user_id=session["user_id"], ticker=output_1["symbol"])
            # update current table accordingly

        else:
            db.execute("INSERT INTO equity (user_id, ticker, shares) VALUES (:user_id, :ticker, :shares)",
            user_id=session["user_id"], ticker=output_1["symbol"], shares=shares_0)
            # otherwise update equity table to account for purchase

        db.execute("INSERT INTO equity_2 (user_id, ticker, shares, price, type) VALUES (:user_id, :ticker, :shares, :price, :type_0)",
                   user_id=session["user_id"], ticker=output_1["symbol"], shares=shares_0, price=price_0, type_0="purchase")

        db.execute("UPDATE users SET cash= :cash WHERE id = :id",
                   cash=user_cash_1, id=session["user_id"])
        # update users table to account for purchase

        return redirect("/")
        # if sucessful return user back to home

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user_transactions_0 = db.execute("SELECT * FROM equity_2 WHERE user_id=:user_id",
                                     user_id=session["user_id"])
    # return a full listing of user transactions

    history_list = []
    # initialize list to load in using for loop

    for i in range(len(user_transactions_0)):

        transaction_data = {}
        transaction_data["ticker"] = user_transactions_0[i]["ticker"]
        transaction_data["shares"] = user_transactions_0[i]["shares"]
        transaction_data["price"] = usd(user_transactions_0[i]["price"])
        transaction_data["type"] = user_transactions_0[i]["type"]
        transaction_data["date"] = user_transactions_0[i]["date"]
        transaction_data["time"] = user_transactions_0[i]["time"]

        history_list.append(transaction_data)
        # append to transaction history list

    return render_template("history.html", history_list=history_list)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    else:

        user_name = request.form.get("username")
        user_password_0 = request.form.get("password")
        user_password_1 = request.form.get("confirmation")
        # retrieves all information submitted by the user

        if not user_name:
            return render_template("apology_register.html", message="You must provide a name.")
        # checks to ensure the user has provided a user_name

        if not user_password_0:
            return render_template("apology_register.html", message="You must provide a password.")
        # checks to ensure the user has provided a password

        if not user_password_1:
            return render_template("apology_register.html", message="Please confirm your password.")
        # checks to ensure the user has confirmed their password

        if user_password_0 != user_password_1:
            return render_template("apology_register.html", message="Passwords do not match.")
        # checks to ensure the password matches confirmation

        users_query_result = db.execute("SELECT username FROM users;")
        users_list_0 = [list(users_query_result[i].values()) for i in range(len(users_query_result))]
        users_list_1 = [i[0] for i in users_list_0]
        # retrieve a list of current users

        if user_name in users_list_1:
            return render_template("apology_register.html", message="User name is already taken.")

        password_hash = generate_password_hash(user_password_1, salt_length=30)

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                    username=user_name, hash=password_hash)

    return redirect("/login")

@app.route("/quote", methods=["GET", "POST"])
def quote():

    if request.method == "GET":
        return render_template("quote.html")

    if request.method == "POST":

        symbol_0 = request.form.get("symbol")
        output_0 = lookup(symbol_0)
        # retreive symbol from user and attempt to retreive
        # info from API

        if not output_0:
            return render_template("apology_quote.html", message="ERROR: Invalid ticker.")

        else:
            output_1 = dict(output_0)
            lookup_message = "A share of " + output_1["name"] + " (" + output_1["symbol"] + ") " + "costs " + usd(output_1["price"]) + "."
            return render_template("quoted.html", message=lookup_message)
        # use returned output to generate a message

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    if request.method == "GET":
        return render_template("sell.html")

    if request.method == "POST":

        symbol_0 = request.form.get("symbol")
        shares_0 = int(request.form.get("shares"))
        output_0 = lookup(symbol_0)
        # retreive symbol and shares from user
        # retrieve required input from API

        if not output_0:
            return render_template("apology_sell.html", message="ERROR: Invalid ticker.")

        output_1 = dict(output_0)
        price_0 = float(output_1["price"])
        cash_value_0 = price_0 * shares_0
        # retrieve api output and information from output

        user_query_result_0 = db.execute("SELECT * FROM users WHERE id = :id",
                                         id=session["user_id"])
        user_info_0 = dict(user_query_result_0[0])
        user_cash_0 = float(user_info_0["cash"])
        # retrieve user information as dictionary

        equity_query_result_0 = db.execute("SELECT ticker FROM equity;")
        equity_list_0 = [list(equity_query_result_0[i].values()) for i in range(len(equity_query_result_0))]
        equity_list_1 = [i[0] for i in equity_list_0]
        # retrieve a list of current stocks owned by user

        if output_1["symbol"] in equity_list_1:

            ticker_query_result_0 = db.execute("SELECT * FROM equity WHERE user_id = :user_id AND ticker = :ticker",
                                               user_id=session["user_id"], ticker=output_1["symbol"])
            ticker_info_0 = dict(ticker_query_result_0[0])
            # if user currently owns stock subtract from purchased stock

            old_shares_0 = int(ticker_info_0["shares"])

            if old_shares_0 == 0:
                return render_template("apology_sell.html", message="ERROR: User does not currently own this stock.")
            # if user does not own stock exit

            if old_shares_0 < shares_0:
                return render_template("apology_sell.html", message="ERROR: User does not currently own enough stock.")

            new_shares_0 = old_shares_0 - shares_0
            # substract sold shares from old shares

            db.execute("UPDATE equity SET shares = :shares WHERE user_id = :user_id AND ticker = :ticker",
                       shares=new_shares_0, user_id=session["user_id"], ticker=output_1["symbol"])
            # update current table accordingly

        else:
           return render_template("apology_sell.html", message="ERROR: User does not currently own this stock.")
           # render appology if user does not own stock

        user_cash_1 = user_cash_0 + cash_value_0
        # if user has sufficient cash add cash value

        db.execute("INSERT INTO equity_2 (user_id, ticker, shares, price, type) VALUES (:user_id, :ticker, :shares, :price, :type_0)",
                   user_id=session["user_id"], ticker=output_1["symbol"], shares=shares_0, price=price_0, type_0="sale")

        db.execute("UPDATE users SET cash= :cash WHERE id = :id",
                   cash=user_cash_1, id=session["user_id"])
        # update users table to account for purchase

        return redirect("/")
        # if sucessful return user back to home


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
