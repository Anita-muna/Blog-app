import os

from flask import Flask, url_for, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user, login_manager
from werkzeug.utils import redirect

# Initialize the Flask application
app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret')
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(500), nullable=False)

    post = db.relationship('Post', back_populates='user', lazy=True)

    def __repr__(self):
        return f'<User {self.fullname}>'


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(500), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='post')

    def __repr__(self):
        return f'<Post {self.title}>'


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Define a simple route
@app.route('/', methods=['GET', 'POST'])
@app.route('/home_page', methods=['GET', 'POST'])
def home_page():
    posts = Post.query.all()
    return render_template('home_page.html', posts=posts, current_user=current_user)


@app.route('/signup_page', methods=['GET', 'POST'])
def signup_page():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if confirm_password == password:
            hashed_password = generate_password_hash(password)
            new_user = User(fullname=fullname, username=username, email=email,
                            password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
        else:
            flash('Passwords do not match!!!', 'danger')
        return redirect(url_for('home_page'))
    return render_template('signup_page.html')


@app.route('/login_page', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        email_check = select(User).where(User.email == email)
        email_true = db.session.execute(email_check).scalar()
        if email_true and check_password_hash(email_true.password, password):
            login_user(email_true)
            return redirect(url_for('home_page'))
        else:
            flash('Incorrect Credentials!!!', 'danger')
        return redirect(url_for('login_page'))
    return render_template('login_page.html')


@login_required
@app.route('/blog_page', methods=['GET', 'POST'])
def blog_page():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        new_post = Post(title=title, content=content, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
    users_posts = select(Post).where(Post.user_id == current_user.id)
    posts = db.session.execute(users_posts).scalars().all()
    return render_template('blog_page.html', posts=posts)


@login_required
@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    particular_post = select(Post).where(Post.id == post_id)
    execute_post = db.session.execute(particular_post).scalar()
    if execute_post.user != current_user:
        return 'You are not authorized to edit this post.', 403

    if request.method == 'POST':
        new_title = request.form.get('title')
        new_content = request.form.get('content')
        execute_post.title = new_title
        execute_post.content = new_content
        db.session.commit()
        return redirect(url_for('blog_page'))
    return render_template('edit_post.html', post=execute_post)


@login_required
@app.route('/delete_post/<int:post_id>', methods=['GET', 'POST'])
def delete_post(post_id):
    particular_post = select(Post).where(Post.id == post_id)
    delete_execute = db.session.execute(particular_post).scalar()
    if delete_execute.user != current_user:
        return 'You are not authorized to edit this post.', 403

    db.session.delete(delete_execute)
    db.session.commit()
    return redirect(url_for('blog_page'))


@login_required
@app.route('/logout_page', methods=['GET', 'POST'])
def logout_page():
    logout_user()
    flash('Logout Successful!', 'success')
    return redirect(url_for('home_page'))


# Run the app
if __name__ == "__main__":
    app.run(debug=True)

