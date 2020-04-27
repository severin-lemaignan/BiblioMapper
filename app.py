from pathlib import Path
import os
import json

import tempfile

import sqlite3

from flask import Flask, escape, url_for,render_template, g, request, redirect, jsonify, session
from werkzeug import secure_filename


from article import Article, Author, get_article_network

app = Flask(__name__)

ROOT = Path(".")

ARTICLES_ROOT= ROOT / "test" / "articles"
AUTHORS_ROOT= ROOT / "test" / "authors"

PROFILE_PICTURE_FOLDER="static/profiles/"

PICTURE_EXTENSIONS = ["png","jpg","jpeg"]


## See details on how to manage user sessions in the MSC website
app.secret_key = b'\xfbC&\xd4\xde\x9ej\xcd\\\x87H\n+WhV'

ARTICLES = {p.parts[-1]: Article(p) for p in ARTICLES_ROOT.iterdir()}

AUTHORS = {a.parts[-1]: Author(a) for a in AUTHORS_ROOT.iterdir()}



@app.route('/article/<id>')
def article(id=None):

    if id is None:
        return redirect(url_for('hello'))

    if id in ARTICLES:
        return jsonify(get_article_network(ARTICLES[id]))


@app.route('/article/new', methods=["POST"])
def add_new_article_from_pdf():

    file = request.files['pdf']
    if file:
        tmp_file = tempfile.NamedTemporaryFile(delete=False)

        print("Saving PDF as temporary file %s, before processing..." % tmp_file.name)
        file.save(tmp_file)

        article = Article.create_from_pdf(tmp_file.name)
    else:
        print("No file received!")

    return redirect(url_for('hello'))



@app.route('/')
def hello():
    return render_template('landing.html')

@app.route('/keywords')
def get_keywords():

    substring = request.args.get("q", "")
    if substring:
        keywords = query_db('select * from keywords where keyword like ?', ["%" + substring + "%"])
    else:
        keywords = query_db('select * from keywords')
    return jsonify([k['keyword'] for k in keywords])

@app.route('/supervisor/')
@app.route('/supervisor/<username>/')
def show_supervisor_profile(username=None):
    if 'username' not in session:
        return redirect(url_for('login'))
    if session['username'] != "msc2020supervisors":
        return redirect(url_for('login', usertype="supervisor",msg="Wrong login"))

    subjects = []
    user = None

    supervisors = query_db('select * from supervisors')
    students = query_db('select * from students')
    keywords = query_db('select * from keywords')
    supervisor_keywords = []

    if username:
        user = query_db('select * from supervisors where username = ?', [username], one=True)
        subjects = query_db('select * from subjects where supervisor = ?', [username])
        supervisor_keywords = query_db('select * from keywords_supervisors where supervisor=?', [username])


    # show the user profile for that user
    return render_template('supervisor_profile.html',
                    username=username,
                    user=user,
                    has_picture=exist_picture(username),
                    keywords=[k['keyword'] for k in keywords],
                    supervisor_keywords=[k['keyword'] for k in supervisor_keywords],
                    subjects=subjects,
                    students=students,
                    supervisors=supervisors)

@app.route('/student/<studentid>/')
def show_student_page(studentid):
    student = query_db('select * from students where student_id = ?', [studentid], one=True)
    subjects = query_db('select * from subjects')

    return render_template('student_page.html',
                    studentid=studentid,
                    user=user,
                    has_picture=exist_picture(username),
                    keywords=[k['keyword'] for k in keywords],
                    supervisor_keywords=[k['keyword'] for k in supervisor_keywords],
                    subjects=subjects,
                    students=students,
                    supervisors=supervisors)

@app.route('/supervisor/create/<firstname>/<surname>')
def create_supervisor_profile(firstname, surname):

    username = (firstname[0] + "-" + surname).lower()
    execute_db('insert into supervisors(username, firstname, surname) values (?,?,?)', [username,firstname,surname])

    return redirect(url_for('show_supervisor_profile', username=username))

@app.route('/supervisor/<username>/profile', methods=["POST"])
def update_supervisor_profile(username):
    profile = request.form["profile"]
    execute_db('update supervisors set profile=? where username=?', [profile, username])

    return ""


@app.route('/supervisor/<username>/update', methods=["POST"])
def update_supervisor(username):

    params = request.get_json(force=True)

    if "email" in params:
        execute_db('update supervisors set email=? where username=?', [params["email"], username])

    if "max_students" in params:
        execute_db('update supervisors set max_students=? where username=?', [params["max_students"], username])


    return ""

@app.route('/supervisor/<username>/keywords', methods=["GET","POST"])
def update_supervisor_keywords(username):

    # no POST data? simply return the keywords for this user
    if not request.get_data():
        keywords = query_db('select * from keywords_supervisors where supervisor=?', [username])
        return jsonify([k['keyword'] for k in keywords])

    params = request.get_json(force=True)
    keywords = request.get_json(force=True)["keywords"]


    for k in keywords:
        # add the keyword to the list of keywords
        execute_db('insert or ignore into keywords values (?)', [k])

        execute_db('insert into keywords_supervisors(keyword, supervisor) ' \
                'select ?, ?' \
                'where not exists ' \
                        '(select 1 from keywords_supervisors where keyword = ?' \
                                                    'and supervisor = ?);', [k,username,k,username])



    return ""


@app.route('/supervisor/<username>/new-subject', methods=["POST"])
def add_new_subject(username):
    s = request.form

    execute_db('insert into subjects (title, desc, supervisor, cosupervisor, assigned_student, is_cocreated) values (?, ?, ?, ?, ?, ?)', 
            [s["title"], 
             s["desc"], 
             username, 
             s["cosupervisor"] if "cosupervisor" in s else "", 
             s["assigned_student"] if "assigned_student" in s else "", 
             "assigned_student" in s]
        )

    subjectid = query_db('select last_insert_rowid();', one=True)['last_insert_rowid()']

    if s["keywords"]:
        keywords = json.loads(s["keywords"])

        for k in keywords:
            # add the keyword to the list of keywords
            execute_db('insert or ignore into keywords values (?)', [k])

            execute_db('insert into keywords_subjects(keyword, subject) ' \
                    'select ?, ?' \
                    'where not exists ' \
                            '(select 1 from keywords_subjects where keyword = ?' \
                                                        'and subject = ?);', [k,str(subjectid),k,str(subjectid)])

    return redirect(url_for('show_supervisor_profile', username=username))


@app.route('/supervisor/<username>/delete-subject', methods=["POST"])
def delete_subject(username):

    s = request.form

    execute_db('delete from subjects where id=?', [s["subjectid"]])
    return redirect(url_for('show_supervisor_profile', username=username))

