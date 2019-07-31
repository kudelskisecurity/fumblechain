#!/usr/bin/env python3

"""FumbleStore database model"""

import os

from peewee import *

database_path = os.environ["SQLITE_DATABASE_PATH"]
db = SqliteDatabase(database_path)


class BaseModel(Model):
    class Meta:
        database = db


class Product(BaseModel):
    """Represents a product in the Fumblestore."""
    short = TextField(unique=True)
    title = TextField()
    price = FloatField()
    secret_flag = TextField()
    description = TextField()
    description_file = TextField()
    node_api_url = TextField()
    hint = TextField()


class User(BaseModel):
    """Represents a Fumblestore user.
    """
    username = TextField(unique=True)
    password = TextField()
    registration_date = DateTimeField()
    last_login_date = DateTimeField()


class UserProduct(BaseModel):
    """Makes the link between users and products"""
    user = ForeignKeyField(User)
    product = ForeignKeyField(Product)
    is_owned = BooleanField(default=False)
    wallet = TextField()
    owned_since = DateTimeField()


def user_owns_product(user, product):
    """Returns True if the given user owns the given product, False otherwise."""
    user_products = UserProduct.select(UserProduct, User).join(User).where(
        (UserProduct.user.username == user.username) & (UserProduct.is_owned == True))

    for up in user_products:
        if up.product.short == product.short:
            return True
    return False


def product_owners(product):
    """Returns the list of UserProducts for which the product is owned."""
    user_products = (
        UserProduct
            .select(UserProduct, User, Product)
            .join(Product)
            .switch(UserProduct)
            .join(User)
            .where(
            (UserProduct.product.short == product.short)
            & (UserProduct.is_owned == True)
        )
    )

    return [up.user for up in user_products]


def top_users():
    """Returns the list of users who solved the most challenges (sorted by that criteria, most solves first)"""
    solves = fn.Count(UserProduct.id)
    users = (
        User
            .select(User, solves.alias("count"))
            .join(UserProduct, JOIN.LEFT_OUTER)
            .where(UserProduct.is_owned == True)
            .group_by(User)
            .order_by(solves.desc())
    )
    return users


def challenge_solves():
    """Returns the list of SOLVED challenges and their associated UserProducts."""
    solves = fn.Count(UserProduct.id)
    challenges = (
        Product
            .select(Product, solves.alias("count"))
            .join(UserProduct, JOIN.LEFT_OUTER)
            .where(UserProduct.is_owned == True)
            .group_by(Product)
    )
    return challenges
