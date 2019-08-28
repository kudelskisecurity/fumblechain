#!/usr/bin/env python3

import datetime
import math
import os
import re

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask import Markup
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from peewee import DoesNotExist
from pytz import utc
from werkzeug.exceptions import NotFound
from werkzeug.security import generate_password_hash, check_password_hash

from model.wallet import Wallet
from store.database import Product
from store.database import User
from store.database import UserProduct
from store.database import db
from store.database import user_owns_product, product_owners, top_users, challenge_solves
from store.lesson import get_available_lessons

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
SECRET_KEY = os.environ.get("FUMBLESTORE_FLASK_SECRET_KEY", default=None)
if SECRET_KEY is None:
    raise Exception("FUMBLESTORE_FLASK_SECRET_KEY environment variable is not set!")
app.secret_key = SECRET_KEY

# enable secure cookies
SESSION_COOKIE_SECURE = True if os.environ.get("SESSION_COOKIE_SECURE", False) == "1" else False
SESSION_COOKIE_HTTPONLY = True if os.environ.get("SESSION_COOKIE_HTTPONLY", False) == "1" else False
SESSION_COOKIE_SAMESITE = "Lax"
print(f"Cookies: SECURE={SESSION_COOKIE_SECURE}, HTTPONLY={SESSION_COOKIE_HTTPONLY}")

app.config.update(
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY=SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
)

FLASH_SUCCESS = "success"
FLASH_ERROR = "error"
FLASH_INFO = "info"


def insert_products():
    """Insert products (challenges) into database if they have not been inserted yet."""
    ch1_product_node_api_url = os.environ["CHALLENGE1_PRODUCT_NODE_API_URL"]
    ch2_product_node_api_url = os.environ["CHALLENGE2_PRODUCT_NODE_API_URL"]
    ch3_product_node_api_url = os.environ["CHALLENGE3_PRODUCT_NODE_API_URL"]
    ch4_product_node_api_url = os.environ["CHALLENGE4_PRODUCT_NODE_API_URL"]
    products = [
        Product(short="flag1", title="2chains", price=5000000,
                description="Introduction to Blockchain security with essential integrity checks.",
                description_file="challenges/challenge1.html",
                secret_flag="FCKS{tHat_Was_eAsy_waSnt_It?}", node_api_url=ch1_product_node_api_url,
                hint="Is there a way to move coins from one chain to another?"),
        Product(short="flag2", title="Erressa", price=10000000,
                description="RSA Cryptography",
                description_file="challenges/challenge2.html",
                secret_flag="FCKS{letS_not_jump_t0_concluSions_toO_earLy}",
                node_api_url=ch2_product_node_api_url,
                hint="""Not even using a technique described in <a target="_blank" href="https://research.kudelskisecurity.com/2018/08/16/breaking-and-reaping-keys-updated-slides-and-resources/">a specific DEF CON 26 talk about public keys</a>."""),
        Product(short="flag3", title="Infinichain", price=math.inf,
                description="Have to think about that as well.",
                description_file="challenges/challenge3.html",
                secret_flag="FCKS{madE_iT_to_teh_End?}", node_api_url=ch3_product_node_api_url,
                hint="What's a transaction nonce? Probably useless..."),
        Product(short="flag4", title="TxCheck", price=8500000,
                description="Exploiting transaction validation.",
                description_file="challenges/challenge4.html",
                secret_flag="FCKS{nEgaTivE_amounts_rulE}", node_api_url=ch4_product_node_api_url,
                hint="Could you force someone else to send you coins with a simple transaction?")
    ]

    existing_products = [p for p in Product.select()]

    if len(existing_products) == 0:
        # first launch, create initial products
        for p in products:
            p.save()


def get_products():
    """Return the list of products."""
    query = Product.select()
    products = [p for p in query]
    for p in products:
        print(p.id, p.short, p.title)
    return products


def is_payment_processed(address, product, node_api_url):
    """Return True if the payment for the given product `product` has been made.
    The payment is considered valid if the wallet with given `address` has a secure wallet balance at least as great as
    the product price.
    The given `node_api_url` is used to check the secure balance.
    Note that secure balance is balance including transactions that have at least 6 confirmations only."""
    print(f"checking whether payment is done for product {product.short}...")
    print(f"api_url is: {node_api_url}")

    endpoint = f"{node_api_url}/wallet/{address}/secure_balance"
    response = requests.get(endpoint)

    if response.status_code == 200:
        balance = response.json()["balance"]

        if balance >= product.price:
            return True
        else:
            print(f"Not enough funds received. Balance: {balance}. Required: {product.price}")
    else:
        print(f"API returned: {response.status_code}")

    return False


def validate_payments():
    """Check whether payment has been performed for each UserProduct not yet owned.
    If payment was performed, set UserProduct.is_owned to True to indicate that the payment has been done.
    """
    pending_user_products = UserProduct.select().where(UserProduct.is_owned == False)

    for pup in pending_user_products:
        user = pup.user
        address = pup.wallet
        product = pup.product
        node_api_url = product.node_api_url
        try:
            payment_ok = is_payment_processed(address, product, node_api_url)
        except Exception as e:
            print(f"Failed to check whether payment is processed. (user: {user.username}, product: {product.short})")
            print(e)
            continue

        if payment_ok:
            # mark UserProduct as owned
            pup.is_owned = True
            pup.owned_since = datetime.datetime.utcnow()
            pup.save()

            print(f"Validated payment for user {user.username} for product {product.short}")
        else:
            print(f"Payment not yet done (user: {user.username}, product: {product.short})")


def get_user():
    """Return the logged in user.
    Return None if the user is not logged in.
    """
    if "user" in session:
        user = User.get(User.username == session["user"])
        print(f"get_user(): {user.username}")
        return user
    else:
        return None


def get_globals():
    """Return a dictionary of global variables.
    We inject these variables into every Jinja2 template.
    """
    kwargs = {
        "user": get_user(),
        "now": datetime.datetime.utcnow(),
        "recaptcha_enabled": True if os.environ.get("RECAPTCHA_ENABLED", False) == "1" else False,
        "recaptcha_site_key": os.environ.get("RECAPTCHA_SITE_KEY", ""),
        "recaptcha_secret_key": os.environ.get("RECAPTCHA_SECRET_KEY", ""),
        "display_port_warning": True if os.environ.get("DISPLAY_PORT_WARNING", False) == "1" else False
    }

    env_vars = [
        "CHALLENGE1_MONEYMAKER_URL",
        "CHALLENGE1_MAINNET_NODE_URL",
        "CHALLENGE1_TESTNET_NODE_URL",
        "CHALLENGE1_TESTNET_MAGIC",
        "CHALLENGE2_MAINNET2_NODE_URL",
        "CHALLENGE2_MAINNET2_MAGIC",
        "CHALLENGE2_MAINNET2_MAGIC",
        "CHALLENGE3_MAINNET3_NODE_URL",
        "CHALLENGE3_MAINNET3_MAGIC",
        "CHALLENGE4_MAINNET4_NODE_URL",
        "CHALLENGE4_MAINNET4_MAGIC",
        "CHALLENGE3_ECHOSERVICE_WALLET_ADDRESS",
        "CHALLENGE3_ECHOSERVICE_MIN_CONFIRMATIONS"
    ]

    for v in env_vars:
        env_val = os.environ[v]
        kwargs[v] = env_val

        # support local docker instances
        is_docker_local = os.environ.get("IS_DOCKER_LOCAL", False)
        if type(is_docker_local) == str:
            is_docker_local = True if is_docker_local == "1" else False

        if is_docker_local:
            if "NODE_URL" in v:
                host, port = env_val.split(":")
                host = os.environ[v.replace("NODE_URL", "NODE_HOST")]
                kwargs[v] = f"{host}:{port}"

    return kwargs


def recaptcha_ok(request):
    """Return True if the reCAPTCHA associated with the given `request` was successfully completed by the user.
    Return False otherwise.
    """
    fc_globals = get_globals()
    if fc_globals["recaptcha_enabled"]:
        recaptcha_client_response = request.form["g-recaptcha-response"]
        recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
        params = {
            "secret": fc_globals["recaptcha_secret_key"],
            "response": recaptcha_client_response
        }

        recaptcha_backend_response = requests.post(recaptcha_url, data=params)
        try:
            response_json = recaptcha_backend_response.json()
            success = response_json["success"]
            if success:
                return True
        except:
            return False
    else:
        return True


def get_product_for_id(product_id):
    """Return the product with the given ID `product_id`."""
    products = get_products()

    for product in products:
        if product.short == product_id:
            return product

    raise NotFound()


def is_product_owned(product, user):
    """Return True if the given `user` owns the given `product`.
    In other words, return True if the user solved the challenge.
    Return False otherwise.
    """
    if user is None:
        return False

    owned = user_owns_product(user, product)
    return owned


def generate_wallet():
    """Generate and return a new wallet."""
    w = Wallet()
    w.create_keys()
    return w


####################################################################
# Template filters
####################################################################

@app.template_filter("price")
def display_price(price):
    """Template filter
    Print the infinity sign if the given `price` is infinite.
    Print the given `price` otherwise."""
    if math.isinf(price):
        return '\u221e'
    else:
        return price


@app.template_filter("pluralize")
def pluralize(count, singular_suffix="", plural_suffix="s"):
    """Template filter
    Pluralize words.
    If the given `count` is equal to 1, then by default, do not print anything (`singular_suffix`).
    Otherwise, print an "s" to indicate that the word is plural (`plural_suffix`).
    """
    count = int(count)
    if count == 1:
        return singular_suffix
    else:
        return plural_suffix


####################################################################
# Endpoints
####################################################################

@app.route("/", methods=["GET"])
def get_home():
    """Display the home page of the FumbleStore."""
    return render_template("home.html", **get_globals())


@app.route("/challenges", methods=["GET"])
def get_challenges():
    """Display the challenges page."""
    products = get_products()
    user = get_user()
    product_ownage = []

    for p in products:
        if user is not None:
            owned = user_owns_product(user, p)
        else:
            owned = False
        product_ownage.append((p, owned))

    return render_template("challenges.html", products=product_ownage, **get_globals())


@app.route("/login", methods=["GET"])
def get_login():
    """Display the sign in page."""
    return render_template("login_form.html", **get_globals())


@app.route("/login", methods=["POST"])
def post_login():
    """Try to authenticate the user trying to sign in."""
    username = request.form["username"]
    password = request.form["password"]

    try:
        user = User.get(User.username == username)

        if check_password_hash(user.password, password):
            # successful login, create session
            session["user"] = user.username
            user.last_login_date = datetime.datetime.utcnow()
            user.save()
            flash(f"Successfully signed in as {user.username}.", FLASH_SUCCESS)
            return redirect("/")
        else:
            raise Exception()
    except Exception as e:
        print(e)
        flash(f"Invalid username or password. Please try again.", FLASH_ERROR)
        return redirect("/login")


@app.route("/logout", methods=["GET"])
def logout():
    """Sign out the currently signed in user."""
    try:
        session.pop("user")
        flash(f"Successfully signed out.", FLASH_INFO)
    except KeyError:
        pass
    return redirect("/")


@app.route("/register", methods=["GET"])
def get_register():
    """Display the sign up page."""
    return render_template("register_form.html", **get_globals())


@app.route("/register", methods=["POST"])
def post_register():
    """Try to register the user."""
    username = request.form["username"]
    password = request.form["password"]

    regex = "^[a-zA-Z0-9_.-]+$"
    max_length = 256

    if re.match(regex, username) and len(username) <= max_length and max_length >= len(password) > 0:
        pass
    else:
        flash_message = f"Username must be composed of letters (a-z, A-Z), numbers (0-9), dot (.), dash (-) or underscore (_) only.<br />Username and password length must be between 1 and {max_length} characters."
        flash(Markup(flash_message), FLASH_ERROR)
        return redirect("/register")

    try:
        existing_user = User.get(User.username == username)
        # username already in use, register failure
        flash(f"Username already exists! Please chose another username and try again.", FLASH_ERROR)
        return redirect("/register")
    except DoesNotExist:
        # first check that reCAPTCHA check passed
        if recaptcha_ok(request):
            pass
        else:
            flash(f"Please complete the CAPTCHA.", FLASH_ERROR)
            return redirect("/register")

        new_user = User(username=username,
                        password=generate_password_hash(password),
                        registration_date=datetime.datetime.utcnow(),
                        last_login_date=datetime.datetime.fromtimestamp(0))
        new_user.save()

        flash(f"Successfully registered as {username}! You can now sign in.", FLASH_SUCCESS)
        return redirect("/login")


@app.route("/product/<product_id>", methods=["GET"])
def get_challenges_product(product_id):
    """Display the challenge with given ID `product_id`."""
    product = get_product_for_id(product_id)
    owned = is_product_owned(product, get_user())
    pus = product_owners(product)
    product_owners_count = len(pus)
    return render_template("product.html", product=product, owned=owned, pus=pus,
                           product_owners_count=product_owners_count,
                           **get_globals())


@app.route("/product/<product_id>/hint", methods=["GET"])
def get_challenges_product_hint(product_id):
    """Display the hint for the given challenge with ID `product_id`."""
    product = get_product_for_id(product_id)
    hint = f"<strong>Hint:</strong> {product.hint}"
    flash(Markup(hint), FLASH_INFO)
    return redirect(f"/product/{product_id}")


@app.route("/scoreboard", methods=["GET"])
def get_scoreboard():
    """Display the scoreboard page."""
    users = top_users()
    challenges = challenge_solves()

    return render_template("scoreboard.html", top_users=users, challenges=challenges, **get_globals())


@app.route("/faq", methods=["GET"])
def get_faq():
    """Display the FAQ page."""
    faq = {
        "What is FumbleChain?": "FumbleChain is a purposefully vulnerable Blockchain. Its goal is to raise awareness about Blockchain security and let people like you, who are interested in Blockchain security, learn in a fun way.",
        "Who made FumbleChain?": """FumbleChain was initially developed by the research team at <a target="_blank" href="https://www.kudelskisecurity.com">Kudelski Security</a>.""",
        "I am stuck on challenge X.": """Please have a look at the hint and go through the <a href="/lessons">Lessons</a> for some help.""",
        "How to report bugs?": """Please report any bugs by opening an issue on the project's <a target="_blank" href="https://github.com/kudelskisecurity/fumblechain">Github page</a>."""
    }
    return render_template("faq.html", faq=faq, **get_globals())


@app.route("/lessons", methods=["GET"])
def get_lessons():
    """Display the lessons page."""
    categories = get_available_lessons()
    return render_template("lessons.html", categories=categories, **get_globals())


@app.route("/lessons/<int:lesson_id>", methods=["GET"])
def get_lessons_lesson(lesson_id):
    """Display the lesson with given ID `lesson_id`."""
    categories = get_available_lessons()
    lessons = []

    for title, category_lessons in categories.items():
        lessons += category_lessons

    for lesson in lessons:
        if lesson.id == lesson_id:
            with open(f"templates/{lesson.template_path}") as f:
                lesson_contents = f.read()
                return render_template("lesson.html", lesson=lesson, lesson_contents=lesson_contents, **get_globals())
    return NotFound()


@app.route("/buy/<product_id>", methods=["POST"])
def post_challenges_buy_product(product_id):
    """Buy the challenge with given ID `product_id`.
    This actually displays the 'Proceed to payment' page."""
    product = get_product_for_id(product_id)
    print("buying...")
    user = get_user()

    # check whether user product already exist for (user,product)
    user_products = (
        UserProduct
            .select(UserProduct, User, Product)
            .join(Product)
            .switch(UserProduct)
            .join(User)
            .where(
            (UserProduct.product.short == product_id)
            & (UserProduct.user.username == user.username)
        )
    )

    wallet_address = None
    for up in user_products:
        wallet_address = up.wallet

    if wallet_address is None:
        # else, generate wallet and insert into DB
        wallet = generate_wallet()
        wallet_address = wallet.get_address()
        # insert UserProduct since it doesn't exist
        up = UserProduct(user=get_user(), product=product, is_owned=False, wallet=wallet_address,
                         owned_since=datetime.datetime.utcnow())
        up.save()

    # show wallet address to user
    return render_template("please_proceed_to_payment.html", product=product, wallet_address=wallet_address,
                           **get_globals())


####################################################################
# Setup
####################################################################

# init database
db.connect()
db.create_tables([User, Product, UserProduct])

# Insert products into database on first run
insert_products()

# Start payment validation background task
scheduler = BackgroundScheduler(timezone=utc)
scheduler.add_job(func=validate_payments, trigger="interval", seconds=10)
scheduler.start()


def main():
    app.run(host="0.0.0.0", port=os.environ["FUMBLESTORE_PORT"])
    scheduler.shutdown()


if __name__ == '__main__':
    main()
