from app import app, db #import the flask instance from module app
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, ResetPasswordForm, ResetPasswordRequestForm
from app.email import send_password_reset_email
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, login_required, logout_user
from app.models import User, Post
from werkzeug.urls import url_parse
from datetime import datetime


@app.route("/", methods = ["GET", "POST"])
@app.route("/index", methods = ["GET", "POST"])
@login_required # will redirect if no login
def index():
	form = PostForm()
	if form.validate_on_submit():
		post = Post(body=form.body.data, timestamp=datetime.utcnow(), author=current_user)
		db.session.add(post)
		db.session.commit()
		flash("Your post is live!")
		return redirect(url_for('index'))
		''' ensures that page refreshes do not result in form resubmissions, since
			refreshes mimic the last request
			(Post/Redirect/Get pattern)
		'''

	page = request.args.get("page", 1, type=int)
	posts = current_user.followed_posts().paginate(
		page, app.config["POSTS_PER_PAGE"], False
	) # pagination object has_next, has_prev attributes for easy pagination

	next_url = url_for("index", page=posts.next_num) if posts.has_next else None # page is a query argument pased to url
	prev_url = url_for("index", page=posts.prev_num) if posts.has_prev else None

	return render_template('index.html', title="Home", posts=posts.items, next_url=next_url,
	prev_url = prev_url, form=form)

@app.before_request
def before_request():
	if current_user.is_authenticated:
		current_user.last_seen = datetime.utcnow()
		db.session.commit()


@app.route("/login", methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('index'))

	form = LoginForm()
	if form.validate_on_submit(): # validation here
		user = User.query.filter_by(username=form.username.data).first()
		if user is None or (not user.check_password(form.password.data)):
			flash("Invalid Username or password")
			return redirect(url_for('login'))

		login_user(user, remember=form.remember_me.data)
		# Redirect after login
		next_page = request.args.get('next')
		if not next_page or url_parse(next_page).netloc != '': # netloc non-empty means it's a potentially malicious url_parse
			return redirect(url_for('index'))
		return redirect(next_page)

	return render_template('login.html', title='Sign In', form=form)

@app.route("/register", methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data)
		user.set_password(form.password.data)
		user.set_email(form.email.data)
		db.session.add(user)
		db.session.commit()
		flash("You have been registered!")
		return redirect(url_for("login")) # prevent refreshes from creating same users
	return render_template('register.html', title='Register', form = form) # if no current user

@app.route("/reset_password_request", methods=['GET', 'POST'])
def reset_password_request():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = ResetPasswordRequestForm()
	if form.validate_on_submit():
		email = form.email.data
		user = User.query.filter_by(email=email).first()
		if user:
			send_password_reset_email(user)

		flash("A reset email has been sent")
		return redirect(url_for('login'))

	return render_template('reset_password_request.html', form=form, title="Reset Password")

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_password(token):
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	user = User.verify_reset_password_token(token)
	if not user: # invalid token
		return redirect(utl_for('index'))
	form = ResetPasswordForm()
	if form.validate_on_submit():
		user.set_password(form.password.data)
		db.session.commit()
		flash('Your password has been reset')
		return redirect(url_for('login'))
	return render_template('reset_password.html', form=form)


@app.route("/logout")
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route("/user/<username>")
@login_required
def user(username):
	user = User.query.filter_by(username=username).first_or_404() # user object triggers 404 if does not exist
	page = request.args.get("page", 1, type=int)

	posts = user.posts.order_by(Post.timestamp.desc()).paginate(
		page, app.config["POSTS_PER_PAGE"], False
	)
	next_url = url_for("user", username=user.username, page=posts.next_num) if posts.has_next else None
	prev_url = url_for("user", username=user.username, page=posts.prev_num) if posts.has_prev else None

	return render_template('user.html', user=user, prev_url=prev_url,
	next_url=next_url, posts=posts.items)

@app.route("/edit_profile", methods=['GET', 'POST'])
@login_required
def edit_profile():
	form = EditProfileForm(current_user.username)
	if form.validate_on_submit():
		current_user.username = form.username.data
		current_user.about_me = form.about_me.data
		db.session.commit()
		flash('Your changes have been saved')
		return redirect(url_for('index'))
	elif request.method == "GET":
		form.username.data = current_user.username
		form.about_me.data = current_user.about_me
	return render_template("edit_profile.html", form=form, title="Edit Profile")

@app.route("/explore")
@login_required
def explore():
	page = request.args.get("page", 1, type=int)
	posts = Post.query.order_by(Post.timestamp.desc()).paginate(
		page, app.config["POSTS_PER_PAGE"], False
	)
	next_url = url_for("index", page=posts.next_num) if posts.has_next else None
	prev_url = url_for("index", page=posts.prev_num) if posts.has_prev else None

	return render_template('index.html', posts=posts.items, next_url=next_url,
	prev_url=prev_url, title='Explore') #reuse the template without the form argument

@app.route("/follow/<username>")
@login_required
def follow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User {} not found'.format(username))
		return redirect(url_for('index'))
	if user == current_user:
		flash('You cannot follow yourself!')
		return redirect(url_for('user', username=username))
	current_user.follow(user)
	db.session.commit()
	flash('You are following {}'.format(username))
	return redirect(url_for('user', username=username))

@app.route("/unfollow/<username>")
@login_required
def unfollow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User {} not found'.format(username))
		return redirect(url_for('index'))
	if user == current_user:
		flash('You cannot unfollow yourself!')
		return redirect(url_for('user', username=username))

	current_user.unfollow(user)
	flash('You have unfollowed {}'.format(username))
	return redirect(url_for('user', username=current_user.username))
