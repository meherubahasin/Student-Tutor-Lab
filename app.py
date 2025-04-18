from flask import Flask, request, url_for, render_template, redirect, session, jsonify, g, flash
from pymongo import MongoClient 
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt
import base64
import gridfs
import os
from bson.regex import Regex
from datetime import time

app = Flask(__name__) 

app.secret_key = 'CSE471'  
bcrypt = Bcrypt(app)

client = MongoClient('mongodb+srv://meherubahasin:22341011@cse471.rga8dmj.mongodb.net/') 
db = client.flask_database['student_tutor_lab'] 
print("Connected")


courses_collections = db.courses
appointment_collections = db.appointments
user_collections = db.users
st_collections = db.student_tutors
requests_collections = db.requests

@app.before_request
def before_request():
    g.user = session.get('gsuite', None)
    g.user_type = session.get('user_type', None)


@app.route('/seed_products')   
def seed_products():
    consultation_hours = {"Monday": [[(9, 0),(12, 0)], [(14, 0), (17, 0)]],"Tuesday": [[(9, 30),(12, 30)], [(14, 0), (17, 0)]]}
    st = [{
        'initials': "STMHA", 'consultation':consultation_hours
    }]
    st_collections.insert_many(st)
    
    users = [
        {"gsuite": "meheruba@g.bracu.ac.bd", "password": "22341011", "type": "ST", "initals": "STMHA", "major":"Computer Science"},
        {"gsuite": "admin", "password": "1234", "type": "admin"},
        {"gsuite": "safa.amin@g.bracu.ac.bd", "password": "22341011", "type": "student", "major":"Computer Science Engineering"}
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
        usertype = request.form['user-type']
        if usertype == 'ST':
            gsuite = request.form['gsuite']
            password = request.form['password']
            studentID = request.form['studentID']
            name = request.form['fullname']
            initials = request.form['initials']
            major = request.form['major']
        # hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
            requests_collections.insert_one({
                "gsuite": gsuite,
                "password": request.form['password'],
                "type": usertype,
                "name": name,
                "studentID": studentID,
                "initials": initials,
                "status": 'Pending',
                "ban": False,
                "major": major,
                "appointment-letter": request.form['appointment-letter']
            })
        else:
            gsuite = request.form['gsuite']
            password = request.form['password']
            studentID = request.form['studentID']
            name = request.form['fullname']
            major = request.form['major']
        # hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
            requests_collections.insert_one({
                "gsuite": gsuite,
                "password": password,
                "type": usertype,
                "name": name,
                "studentID": studentID,
                "status": 'Pending',
                "ban": False,
                "major": major
              
            })
        print('Registration successful! Please log in.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/requests', methods=['GET', 'POST'])
def requests():
    requests = list(requests_collections.find())
    return render_template('requests.html', requests=requests)
    
@app.route('/authenticate', methods=['GET', 'POST'])
def authenticate():
    if request.method == 'POST':
        action = request.form['action']
        user = request.form['gsuite']
        request_data = requests_collections.find_one({'gsuite': user})
        if action == 'approve':
            if request_data['type'] == 'ST':
                user_collections.insert_one({"gsuite": request_data['gsuite'],
                "password": request_data['password'],
                "type": request_data['type'],
                "name": request_data['name'],
                "studentID": request_data['studentID'],
                "initials": request_data['initials'],
                "status": 'Approved',
                "ban": False,
                "major": request_data['major'],
                "courses_assigned": [],
                "consultation_slots":[]}),
            else:
                user_collections.insert_one({"gsuite": request_data['gsuite'],
                "password": request_data['password'],
                "type": request_data['type'],
                "name": request_data['name'],
                "studentID": request_data['studentID'],
                "status": 'Approved',
                "ban": False,
                "major": request_data['major'],
                "courses_taken": []}),   
            requests_collections.delete_one({"gsuite":user})
            
        else:
            requests_collections.delete_one({"gsuite":user})
            
    return redirect(url_for('requests'))

@app.route('/debug')
def debug():
    return jsonify(dict(session))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        gsuite = request.form['gsuite']
        password = request.form['password']
        user = user_collections.find_one({"gsuite": gsuite})
        if user and user['password'] == password:
            session['user_type'] = user['type']
            session['gsuite'] = user['gsuite']
            session['password'] = user['password']
            session['logged_in'] = True
            print('Login successful!', session['user_type']) 
            if session['user_type'] == 'admin':
                return redirect(url_for('dashboard'))

            return render_template('index.html', user_id = session['gsuite'], user_type = session['user_type'])

        print('Invalid username or password.')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/upload', methods=['POST'])
def upload():
    if request.method=="POST":
        
        image = request.files['image']
        image_data = image.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        if session['gsuite']:
            user = user_collections.find_one({"gsuite": session['gsuite']})
            datatype = request.form['datatype']
            user.update_one({"$set":{'consultation_slots':base64_image}})
            return redirect(url_for("dashboard", user = user))
        else:
            user = requests_collections.find_one({"gsuite": request.form['gsuite']})
            requests_collections.update_one({"gsuite": request.form['gsuite']}, {"$set":{"appointment-letter":base64_image}})
            
            return redirect(url_for("index"))
    redirect(url_for("index"))
        
        
        
@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    courses = list(courses_collections.find())
    users = list(user_collections.find())
    appointments = list(appointment_collections.find())
    
    
    if 'gsuite' not in session:
        print('Please log in to access the profile.', 'warning')
        return redirect(url_for('login'))
    if session['user_type'] == 'admin':
        return render_template('dashboard.html', user=session['gsuite'], courses=courses, users=users)
    elif session['user_type'] == 'ST':
        courses = []
        if "courses_assigned" in user:
            for course_id in user["courses_assigned"]:
                course = courses_collections.find_one({"_id": ObjectId(course_id)})
                if course:
                    courses.append(course)
        return render_template('st_profile.html', user=user, courses = courses, appointments = appointments, selected_slots=user.get('consultation_slots', []))
    else:
        return render_template('student_profile.html', user=user, courses = courses, appointments = appointments)
    
@app.route('/update_name', methods=['POST', 'GET'])
def update_name():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    if request.method == 'POST':
        user_collections.update_one(
                {"gsuite": session['gsuite']},
                {"$set": {"name": request.form.get('new_name')}}
            )
        print("Name Changed!", user)
    return render_template('edit_info.html', user = user, edit_type='name')

@app.route('/update_id', methods=['POST', 'GET'])
def update_id():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    if request.method == "POST":
        user_collections.update_one(
                {"gsuite": session['gsuite']},
                {"$set": {"studentID": request.form.get('newID')}}
            )
        print("ID Changed!",request.form.get('newID'))
    return render_template('edit_info.html',user = user, edit_type='id')

@app.route('/update_courses', methods=['POST', 'GET'])
def update_courses():
    if request.method == 'POST':
        action = request.form['action']
        course_id = request.form.get('course')
        
        if action == "approve":
            user_collections.update_one(
                {"gsuite": session['gsuite']},
                {"$push": {"courses_assigned": ObjectId(course_id)}}
            )
            print("Added!")
        elif action == "deny":
            user_collections.update_one(
                {"gsuite": session['gsuite']},
                {"$pull": {"courses_assigned": ObjectId(course_id)}}
            )
            print("Removed!")
        
        return redirect(url_for('update_courses'))
    user = user_collections.find_one({"gsuite": session['gsuite']})
    courses = list(courses_collections.find())
    return render_template('apply_courses.html', user=user, courses=courses)

@app.route('/update_password', methods=['POST', 'GET'])
def update_password():
    user = user_collections.find_one({"gsuite": session['gsuite']})
    if request.method == 'POST':
        
        if 'gsuite' not in session:
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
                    return jsonify({'success': True, 'message': 'Changed'}), 200
                else:
                    print('New passwords do not match')
                    
                    
    return render_template('edit_info.html',user = user, edit_type='password')

@app.route('/select_slots', methods=['GET', 'POST'])
def select_slots():
    if 'gsuite' not in session:
        return redirect(url_for('login'))
    
    user = user_collections.find_one({"gsuite": session['gsuite']})

    if request.method == 'POST':

        selected_slots = request.form.getlist('slots')

        user_collections.update_one(
            {"gsuite": session['gsuite']},
            {"$set": {"consultation_slots": selected_slots}}
        )
        return redirect(url_for('dashboard'))

    days = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    time_slots = []
    
    start_time = time(8, 0) 
    end_time = time(17, 0)  
    current_time = start_time
    while current_time < end_time:
      
        slot_end_hour = current_time.hour + 1
        slot_end_min = current_time.minute + 30
        if slot_end_min >= 60:
            slot_end_hour += 1
            slot_end_min -= 60
        slot_end = time(slot_end_hour, slot_end_min)
        
        time_slots.append({
            'start': current_time.strftime('%I:%M %p'),
            'end': slot_end.strftime('%I:%M %p'),
            'value': f"{current_time.hour:02d}{current_time.minute:02d}"
        })
        

        current_time = slot_end
    
    return render_template('consultation_slots.html', 
                         user=user, 
                         days=days, 
                         time_slots=time_slots,
                         selected_slots=user.get('consultation_slots', []))   
    

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
