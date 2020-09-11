from flask import Flask, render_template, request,session,redirect,flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from datetime import datetime,timedelta
from werkzeug.utils import secure_filename
import json
import os


app = Flask(__name__)
app.secret_key = 'abc'

with open('./templates/config.json','r') as f:
    params = json.load(f)["params"]


app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gm_user'],
    MAIL_PASSWORD=params['gm_password']

)
mail = Mail(app)


if params['local_server']:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), primary_key=False)
    phone = db.Column(db.String(13), unique=False, nullable=False,primary_key=False)
    email = db.Column(db.String(120), unique=False, nullable=False,primary_key=False)
    msg = db.Column(db.String(500), nullable=False,primary_key=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), primary_key=False)
    subtitle = db.Column(db.String(100), primary_key=False)
    slug = db.Column(db.String(30), primary_key=False)
    content = db.Column(db.String(5000), primary_key=False)
    date = db.Column(db.String(13), primary_key=False)
    imgfile = db.Column(db.String(13), primary_key=False)

@app.route("/")
def home():
    posts = Posts.query.paginate(per_page=params['no_of_posts'],page=1,error_out=True)
    return render_template('index.html',urlDict = params, posts = posts)

@app.route("/posts/<int:page_no>")
def page(page_no):
    posts = Posts.query.paginate(per_page=params['no_of_posts'],page=page_no,error_out=True)
    return render_template('index.html',urlDict = params, posts = posts)


@app.route("/post/<string:slugName>",methods=['GET'])
def post_route(slugName):
    post = Posts.query.filter_by(slug=slugName).first()
    print(post)
    return render_template('post.html',urlDict = params, post = post)

@app.route("/contact",methods = ['GET','POST'])
def contact():
    if request.method == 'GET':
        return render_template('contact.html',urlDict = params)
    elif request.method =='POST':
        fName = request.form.get("name")
        fEmail = request.form.get("email")
        fMsg = request.form.get("msg")
        fPhone = request.form.get("phone")
        entry = Contacts(name=fName, email=fEmail, msg=fMsg, phone=fPhone)
        db.session.add(entry)
        db.session.commit()
        mail.send_message(subject= fName +" - "+fPhone,
                        sender=fEmail,
                        recipients=[params['gm_user']],
                        body = fMsg)

        return render_template('contact.html',urlDict = params)

@app.route("/about")
def about():
    return render_template('about.html',urlDict = params)

@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/dashboard",methods=['GET','POST'])
def dashboard():
    if 'user' in session and session['user']==params['admin_user']:
        posts = Posts.query.all()
        return render_template('dashboard.html',urlDict = params, posts=posts)

    if request.method == 'POST':
        userName = request.form.get('uname')
        password = request.form.get('password')
        if userName == params['admin_user'] and password == params['admin_password']:
            session['user']= userName
            posts = Posts.query.all()
            return render_template('dashboard.html',urlDict = params, posts=posts)
        else:
            return render_template('login.html')
    else:
        return render_template('login.html')



@app.route("/edit/<srno>")
def edit(srno):
    if 'user' in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(sno=srno).first()
        return render_template('Edit.html',urlDict = params,post=post)

@app.route("/add")
def add():
    if 'user' in session and session['user'] == params['admin_user']:
        return render_template('add.html',urlDict = params)

@app.route("/save", methods=['GET','POST'])
def save():
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            sno = request.form.get('sno')
            title = request.form.get('title')
            subtitle = request.form.get('subtitle')
            slug = request.form.get('slug')
            content = request.form.get('content')
            imgfile = request.form.get('imgfile')
            date = datetime.now()
            print(f"this is from add function{sno} and type is {type(sno)}")
            if sno == None:
                entry = Posts(imgfile=imgfile, title=title, subtitle=subtitle, slug=slug, content=content, date=date)
                db.session.add(entry)
                db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.subtitle = subtitle
                post.slug = slug
                post.content = content
                post.imgfile = imgfile
                db.session.commit()
                return redirect('/edit/'+sno)

    posts = Posts.query.all()
    return render_template('dashboard.html',urlDict = params, posts=posts)

# ------------------------File Upload--------------------
app.config['UPLOAD_FOLDER'] = params['upload_folder']
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in params['allowed_extensions']


@app.route('/uploadfile', methods=['GET', 'POST'])
def upload_file():
    if 'user' in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()
        if request.method == 'POST':
            # check if the post request has the file part
            if 'file' not in request.files:
                flash('No file part')
                return redirect('/dashboard')
            file = request.files['file']
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file')
                return redirect('/dashboard')
            if file and allowed_file(file.filename):
                flash('entered into final if')
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                return redirect("/dashboard")
        return render_template("dashboard.html",urlDict = params, posts=posts)

# -----------------------LOGOUT-----------------
@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')


# ------------Delete an entry from Database--------------
@app.route("/delete/<postID>")
def delete(postID):
    if 'user' in session and session['user'] == params['admin_user']:
        entry = Posts.query.filter_by(sno=postID).first()
        db.session.delete(entry)
        db.session.commit()
        return redirect('/dashboard')
    else:
        return redirect('/dashboard')


app.run(debug=True)