from flask import Flask, request, url_for, render_template, redirect, session, jsonify, g, flash
from pymongo import MongoClient 
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt
import gridfs
import os
from bson.regex import Regex
from datetime import time

app = Flask(__name__) 

app.secret_key = 'CSE471'  
bcrypt = Bcrypt(app)

client = MongoClient('localhost', 27017) 
db = client.flask_database['student_tutor_lab'] 
print("Connected")


courses_collections = db.courses
appointment_collections = db.appointments
user_collections = db.users
st_collections = db.student_tutors

@app.before_request
def before_request():
    g.user = session.get('gsuite', None)
    g.user_type = session.get('type', None)


@app.route('/seed_products')   
def seed_products():
    consultation_hours = {"Monday": [[(9, 0),(12, 0)], [(14, 0), (17, 0)]],"Tuesday": [[(9, 30),(12, 30)], [(14, 0), (17, 0)]]}
    st = [{
        'initials': "STMHA", 'consultation':consultation_hours
    }]
    st_collections.insert_many(st)
    
    users = [
        {"gsuite": "meheruba@g.bracu.ac.bd", "password": "22341011", "type": "ST"},
        {"gsuite": "admin", "password": "22341011", "type": "admin"},
        {"gsuite": "meherubahasin@g.bracu.ac.bd", "password": "22341011", "type": "student"}
    ]
    user_collections.insert_many(users)
    
    course = [{"title":'Programming Language I',"code": 'CSE110',
                "lectures":[1, 2, 4, 3, 5],
                "STs": ['STMHA', 'STTIK', 'STFFH'],
                "qas": ["Summer 2019", "Summer 2020", "Summer 2022"],
                "popquiz": [1, 2, 3, 4, 5]}, 
              {"title":'Programming Language II',"code": 'CSE111',
                "lectures":[1, 2, 4, 3, 1, 3 ,5 ,3],
                "STs": ['STMHA', 'STTIK', 'STFFH'],
                "qas": ["Summer 2019", "Summer 2020", "Summer 2022"],
                "popquiz": [1, 2, 3, 4, 5]},
              {"title":'Data Structure',"code": 'CSE220',
                "lectures":[1, 2, 4, 3, 1, 3 ,5 ,3],
                "STs": ['STMHA', 'STTIK', 'STFFH'],
                "qas": ["Summer 2019", "Fall 2020", "Summer 2022", "Spring 2023"],
                "popquiz": [1, 2, 3, 4, 5]}]
    
    courses_collections.insert_many(course)
    return "Seeded!"


# MODULE 1

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usertype = request.form['user_type']
        gsuite = request.form['gsuite']
        password = request.form['password']
        studentID = request.form['studentID']
        name = request.form['full-name']
        initials = request.form['initials']
        # hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        user_collections.insert_one({
            "gsuite": gsuite,
            "password": password,
            "type": usertype,
            "name": name,
            "studentID": studentID,
            "initials": initials,
            "status": None,
            "ban": False
        })
        print('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        gsuite = request.form['gsuite']
        password = request.form['password']
        user = user_collections.find_one({"gsuite": gsuite})
        if user:
            session['user_id'] = str(user['_id'])
            session['user_type'] = user['type']
            session['gsuite'] = user['gsuite']
            print('Login successful!', 'success')
            if session['user_type'] == 'admin':
                return redirect(url_for('dashboard.html'))
            else:
                return render_template('index.html')
        else:
            print('Invalid username or password.')
            
        return render_template('index.html', password=password, user_id = session['user_id'], user_type = session['user_type'])
    else:
        return render_template('register.html')


@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    courses = list(courses_collections.find())
    users = list(user_collections.find())
    appointments = list(appointment_collections.find())
    print(session['user_type'])
    
    if 'user_id' not in session:
        print('Please log in to access the profile.', 'warning')
        return redirect(url_for('login'))
    if session['user_type'] == 'admin':
        return render_template('admin_dashboard.html', user=session['_id'], courses=courses, users=users)
    elif session['user_type'] == 'ST':
        return render_template('st_profile.html', username=user, courses = courses, appointments = appointments)
    else:
        return render_template('student_profile.html', username=user, courses = courses, appointments = appointments)
    
@app.route('/update_name', methods=['POST', 'GET'])
def update_name():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    if request.method == 'POST':
        user_collections.update_one(
                {"gsuite": session['gsuite']},
                {"$set": {"name": request.form.get('new_name')}}
            )
        print("Name Changed!")
    return render_template('edit_info.html',username = user, edit_type='name')

@app.route('/update_id', methods=['POST', 'GET'])
def update_id():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    if request.method == "POST":
        user_collections.update_one(
                {"gsuite": session['gsuite']},
                {"$set": {"studentID": request.form.get('newID')}}
            )
        print("ID Changed!",request.form.get('newID'))
    return render_template('edit_info.html',username = user, edit_type='id')

@app.route('/update_password', methods=['POST', 'GET'])
def update_password():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    if request.method == 'POST':
        
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        else:
            
            current_password = request.form.get('pass_current')
            if current_password == user['password']:
                new_password = request.form.get('pass')
                retype_password = request.form.get('pass2')
                if new_password == retype_password:
                    user_collections.update_one(
                        {"gsuite": session['gsuite']},
                        {"$set": {"password": new_password}}
                    )
                    print("Password Changed!")
                else:
                    print('New passwords do not match')
                    
                    
    return render_template('edit_info.html',username = user, edit_type='password')
    
    

#MODULE 3    
@app.route('/st_appointment',  methods=['GET', 'POST']) 
def appointment():
    users = list(user_collections.find())
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        st = request.form.get('initials')
        st = st_collections.find_one({'initials': st})
        date = request.form.get('date')
        slot = request.form.get('slot')
        appointment = {'st': st['initials'], 'student': user_id, 'date': date, 'slot': slot}
        appointment_collections.insert_one(appointment)
        # return jsonify({"appointment": str(appointment)})
        return render_template('book_appointment.html')
    
@app.route('/display_date',  methods=['GET', 'POST']) 
def display_consultation():
    if request.method == 'POST':
        st = request.form.get('initials')
        st = st_collections.find_one({'initials': st})
        # format: day: slot 1 --> (start, end), slot 2 --> (start, end)
        consultation_hours = st['consultation']
        # return jsonify({"consultation": str(consultation_hours), "st": str(st['initials'])})
        return render_template('book_appointment.html')

@app.route('/search_courses',  methods=['GET', 'POST']) 
def search_courses():
    search_query = request.args.get('search_query', '').strip()
    courses_query = {}
    # { <field>: { $regex: /pattern/, $options: '<options>' } }
    # { <field>: { $regex: 'pattern', $options: '<options>' } }
    if search_query:
        regex = Regex(f'.*{search_query}.*', 'i')
        courses_query = {
            '$or': [
                {'title': regex},
                {'code': regex}
            ]
        }
    courses = courses_collections.find(courses_query)
    print(regex, courses_query)
    return list(courses)
    # return jsonify({"result": str(list(courses))})

@app.route('/display_courses',  methods=['GET', 'POST']) 
def display_courses():
    search_query = request.args.get('search_query', '').strip()
    if search_query:
        courses = search_courses()
    else:
        courses = courses_collections.find()
        
    course_details = []
    users = list(user_collections.find())
    user_id = request.form.get('user_id')

    for course in courses:
        course_details.append({
                "id":  ObjectId(course['_id']),
                "title": course["title"],
                "code": course["code"],
                "lectures": len(course["lectures"]),
                "STs": len(course["STs"]),
                "qas": len(course["qas"]),
                "popquiz": len(course["popquiz"])
        })
    return render_template('courses.html', courses=course_details, users=users, user_id = user_id)
    # return jsonify({"courses available": str(course_details), "current user": str(user_id)})
  
@app.route('/coursecontent', methods=['GET', 'POST'])
def coursecontent():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user_id = user_collections.find_one({'gsuite':user_id})
        # user_type = user_id['type']
        course_code = request.form.get('course_code')
        course = courses_collections.find_one({"code": course_code})

    # return render_template('fullcourse.html', course=course, user_id = user_id)
    if request.args.get('format') == 'json':
        return jsonify({"viewing course": course})
    return render_template('fullcourse.html', course=course)
    
    
@app.route('/viewcontent', methods=['GET', 'POST'])
def viewcontent():
    if request.method == 'POST':
        users = list(user_collections.find())
        course_code = request.form.get('course-code')
        resource = request.form.get('resource')
        index = int(request.form.get('index'))
        course = courses_collections.find_one({"code": course_code})
        content = course[resource][index]

    return render_template('course_content.html',  course=course, content = content)
    # return jsonify({"clicked at": content, "from": course_code})

@app.route('/logout')
def logout():
    session.clear()
    print('You have been logged out.', 'success')
    return redirect(url_for('index'))


app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


if __name__ == '__main__': 
    app.run(debug=True, port=1011) 
