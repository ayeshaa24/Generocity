from flask import Flask, render_template, url_for, make_response, flash, redirect, request
from forms import RegistrationForm, LoginForm, TaskForm
import os
import time
import json
import pyrebase
from datetime import datetime
from sentiment_analysis import analyse_text
from idea_generator import generate_idea

# Fixes an issue with pyrebase
def noquote(s):
    return s
pyrebase.pyrebase.quote = noquote

# Initialises Firebase
from firebase_config import firebase_config
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

app = Flask(__name__, static_url_path="", static_folder="../../static/", template_folder="templates/")
app.config.from_object('config')

user = False

def email_to_key(email):
    return email.replace(".", "")

def get_user_id():
    email_key = email_to_key(auth.get_account_info(auth.current_user["idToken"])["users"][0]["email"])
    all_emails = dict(db.child("emails_to_ids").get().val())
    return all_emails[email_key]


def get_user_data():
    user_id = get_user_id()
    user = dict(db.child("users").order_by_key().equal_to(user_id).get().val())[user_id]
    return user

# index route
@app.route('/')
def index():
    if auth.current_user:
        print("logged in")
    else:
        print("logged out")

    global user
    return render_template('index.html', user=user, page="index")

@app.route("/reach")
def reach():
    global user

    countries = dict(db.child("countries").get().val())
    return render_template("reach.html", user=user, countries=countries, generator=generate_idea)

@app.route("/login", methods=["GET", "POST"])
def login():
    # If logged in, it prevents you from going to the login page
    if auth.current_user:
       return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            auth.sign_in_with_email_and_password(form.email.data, form.password.data)
            global user
            user = get_user_data()
            flash("Login successful!", "success")
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("index"))
        except Exception as e:
            auth.current_user = None
            print("error")
            print(e)
            flash("Login Unsuccessful. Please check email and password.", "danger")

    return render_template("login.html", form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    # If logged in, it prevents you from going to the register page
    if auth.current_user:
       return redirect(url_for("index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = {
                "firstname": form.firstname.data,
                "lastname": form.lastname.data,
                "email": form.email.data,
                "location": form.location.data,
                "points": 0,
                "tasks": 0,
                "b_earnt": {
                    "welcome_badge": True
                },
                "b_unearnt": {
                    "1actofkindness": True,
                    "10actsofkindness": True,
                    "50actsofkindness": True,
                    "100actsofkindness": True,
                    "climate_action": True,
                    "gender_equality": True,
                    "no_poverty": True,
                    "quality_education": True,
                    "zero_hunger": True
                }
            }

            # Should return none if route doesn't exist so not none == true
            if not db.child("countries/" + form.location.data).get().val():
                c = 1
            else:
                c = db.child("countries/" + form.location.data).get().val() + 1

            key = db.generate_key()

            updates = {}
            updates["users/" + key] = user
            updates["emails_to_ids/" + email_to_key(form.email.data)] = key
            updates["countries/" + form.location.data] = c
            db.update(updates)

            # Only creates user in authentication after creating database entry
            auth.create_user_with_email_and_password(form.email.data, form.password.data)


            flash("Registered!", "success")
            return redirect(url_for("login"))
        except Exception as e:
            error = json.loads(e.args[1])['error']['message']
            if error == "EMAIL_EXISTS":
                flash("This email has already been registered.", "danger")
            print(e)

    

    return render_template("register.html", form=form)

@app.route("/account", methods=["GET", "POST"])
def account():
    if not auth.current_user:
       return redirect(url_for("index"))

    global user
    form = TaskForm()
    user_id = get_user_id()

    if form.validate_on_submit():
        task = {
            "title": form.title.data,
            "desc": form.desc.data,
            "timestamp": str(datetime.utcnow()),
            "p_earnt": analyse_text(form.desc.data),
            "category": form.category.data
        }

        key = db.generate_key()

        # alt way of updating database
        db.child("users").child(user_id).child("tasks").update({
            key: task
        })

        new = db.child("users").child(user_id).child("points").get().val() + task["p_earnt"]
        db.child("users").child(user_id).update({
            "points": new
        })

        user = get_user_data()
        # updating user in case new points were earnt

        for badge in user["b_unearnt"].keys():
            if ((badge == task["category"]) or
                (badge == "1actofkindness" and len(user["tasks"]) >= 1) or
                (badge == "10actsofkindness" and len(user["tasks"]) >= 10) or
                (badge == "50actsofkindness" and len(user["tasks"]) >= 50) or 
                (badge == "100actsofkindness" and len(user["tasks"]) >= 100)):
                    db.child("users").child(user_id).child("b_earnt").update({
                        badge: True
                    })
                    db.child("users").child(user_id).child("b_unearnt").update({
                        badge: None
                    })

        user = get_user_data()
        # updating user in case new badges were earnt


        flash('Your task has been added!', 'success')
        return redirect(url_for("account"))
        #^ have to do to avoid POST message...

    tasks = db.child("users").child(user_id).child("tasks").get().each()
    if tasks:
        tasks = [task.val() for task in tasks]
    else:
        tasks = []

    badge_names_ordered = [("Welcome", "welcome_badge"),
     ("1st act of kindness", "1actofkindness"), ("10th act of kindness", "10actsofkindness"),
     ("50th act of kindness", "50actsofkindness"), ("100th act of kindness", "100actsofkindness"),
     ("Climate action", "climate_action"), ("Gender Equality", "gender_equality"),
     ("No Poverty", "no_poverty"), ("Quality Education", "quality_education"), ("Zero Hunger", "zero_hunger")]

    return render_template("user_homepage.html", user=user, form=form, tasks=tasks, badges=badge_names_ordered)

@app.route("/logout")
def logout():
    if auth.current_user:
        flash("Logout successful!", "success")
        auth.current_user = None
        global user
        user = False
    return redirect(url_for("index"))


if __name__ == '__main__':
    app.run(debug=True)
