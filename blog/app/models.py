# coding: utf-8

from datetime import datetime
from hashlib import md5

from app import db, login
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


class ModeloComIdMixin:
    id = db.Column(db.Integer, primary_key=True)


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(db.Model, UserMixin, ModeloComIdMixin):
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))  # Password criptografado
    posts = db.relationship("Post", backref="author", lazy="dynamic")
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    # Followed -> Sendo seguido
    # Follower -> Seguindo alguém
    followed = db.relationship(
        'User',
        secondary=followers,
        primaryjoin=("followers.c.follower_id == User.id"),
        secondaryjoin=("followers.c.followed_id == User.id"),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic',
    )

    def __repr__(self):
        return "<User {}>".format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return "https://www.gravatar.com/avatar/{}?d=identicon&s={}".format(
            digest, size
        )

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user) -> bool:
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def followed_posts_v2(self):
        query = """
        select * from post p
        join followers f on f.followed_id == p.user_id
        join user u on u.id == p.user_id
        where f.follower_id == user.id
        order by p.timestamp desc;
        """
        resultado = db.session.execute(query)
        return resultado


class Post(db.Model, ModeloComIdMixin):
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return "<Post {}>".format(self.body)


@login.user_loader
def load_user(id):
    return User.query.get(id)
