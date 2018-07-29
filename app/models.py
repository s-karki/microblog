from app import db, login, app
from datetime import datetime
from time import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin # enables anonymous users and automated user lookup
from hashlib import md5 # for gravatar generation
import jwt

@login.user_loader
def user_loader(id):
    return User.query.get(int(id))

# Association table for followers (self-referential wrt Users)
# left side user FOLLOWs right side user
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

# Create a user object
# UserMixin generically implements required methods for flask-login
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)


    posts = db.relationship('Post', backref='author', lazy='dynamic')

    # follower association table
    followed = db.relationship('User', # foward relationship defined as "followed"
        secondary=followers, # configure the association table
        primaryjoin=(followers.c.follower_id == id), # left to right
        secondaryjoin =(followers.c.followed_id == id), # right to left
        backref = db.backref('followers', lazy='dynamic'), #backref relationship (right to left) defined as "followers"
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def set_email(self, email):
        self.email = email

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user) # this user follows other (user1.followed.append(user2))

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            db.session.commit()



    # filter is akin to filter_by, but allows for more advanced logic (e.g. comparing two variables)
    def is_following(self, user): # look up a list of people this user is following, check if user ID matches
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def is_followed_by(self, user): # look up a list of people following this user, check if user ID matches
        return self.followers.filter(followers.c.follower_id == user.id).count() > 0

    '''
    JOIN: followed_id == Post.user_id
    For each post, retrieves followed people
    [POST_ID][USER_ID][FOLLOWER_ID][FOLLOWED_ID]
        1       2           4           2
        2       2           5           2
        3       4           2           4
        4       4           2           4

    FILTER: follower_id = self.id (in the user class)
    Retrieves the posts we are interested in, the ones where
    the follower id matches the user id.
    So if self.id == 2, we have

    [POST_ID][USER_ID][FOLLOWER_ID][FOLLOWED_ID]
        3       4           2           4
        4       4           2           4

    SORT: Sort filtered posts by timestamp, in descending order
    '''
    def followed_posts(self):

        '''
        followed = Post.query.join(
        followers, (followers.c.followed_id == Post.user_id)).filter(
        followers.c.follower_id == self.id)
        '''

        followed = Post.query.join(
        followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)


        # include own posts without inflating the follower count
        own = Post.query.filter_by(user_id = self.id)

        return followed.union(own).order_by(Post.timestamp.desc())

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return "https://www.gravatar.com/avatar/{}?d=identicon&s={}".format(digest, size)


    def get_reset_password_token(self, expires_in=1800):
        return jwt.encode({
        'reset_password': self.id,
        'exp': time() + expires_in,
        }, app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8') # generate a jwt token as a String
        # exp is standard for jwts

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'], algorithm='HS256')['reset_password']
        except:
            return
        return User.query.get(id)



    def __repr__(self): # printing for Python
        return '<User {}>'.format(self.username)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow) # easy to retrieve in chrono order
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)
