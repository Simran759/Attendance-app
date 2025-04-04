from flask import Flask, request, jsonify,render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from flask_cors import CORS
from sqlalchemy import and_
from werkzeug.security import generate_password_hash, check_password_hash
import os
from math import radians, sin, cos, sqrt, atan2
from dotenv import load_dotenv
from datetime import datetime, UTC,timezone
# Student Check-in Route
from datetime import timedelta
from sqlalchemy import and_


from sqlalchemy import text


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Database Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)

# -------------------- Database Models --------------------

# Student Model
class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    device_id = db.Column(db.String(100))
    date = db.Column(db.Date, default=date.today)

# Attendance Model
class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, default=date.today)

# Admin Credentials Model
class Admin(db.Model):
    __tablename__ = "admin_credentials"
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)  # Hashed password

# Admin Location Model
class AdminLocation(db.Model):
    __tablename__ = "admin_location"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
     # Add admin_id if needed
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(datetime.UTC))  # Fix UTC issue
     


# -------------------- Helper Functions --------------------

# Haversine formula to calculate distance in km
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c  # Distance in km

# -------------------- Routes --------------------

# API Health Check
@app.route("/")
def index():
    return render_template('index.html')

# Admin Login Route
@app.route("/admin_login", methods=["POST"])
def admin_login():
    try:
        data = request.json
        print(data)
        admin = Admin.query.filter_by(admin_id=data["admin_id"]).first()
        # print(admin.password)
       

        hashed_password = generate_password_hash(data["password"])
        print("Hashed:", hashed_password)

        print(check_password_hash(admin.password, data["password"]))
        if admin and check_password_hash(admin.password, data["password"]):
            return jsonify({"message": "Admin login successful!"}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Store Admin Location

print(f"📌 Connected to database: {app.config['SQLALCHEMY_DATABASE_URI']}")





# with app.app_context():  # ✅ Fix: Wrap in application context
#     try:
#         query = text("INSERT INTO admin_location (latitude, longitude, timestamp) VALUES (26.9156, 75.7825, NOW());")
#         db.session.execute(query)
#         db.session.commit()
#         print("✅ Manual insert successful!")
#     except Exception as e:
#         print(f"❌ Error inserting manually: {e}")




@app.route("/admin_location", methods=["POST"])
def save_admin_location():
    try:
        data = request.json
        print("🔹 Received Data:", data)  # Debugging

        # Check if required fields exist
        if "latitude" not in data or "longitude" not in data:
            print("❌ Missing latitude or longitude")
            return jsonify({"error": "Missing required fields"}), 400

        new_location = AdminLocation(
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            timestamp=datetime.now() # ✅ Fix datetime issue
        )

        db.session.add(new_location)
        db.session.flush()  
        db.session.commit()

        print("✅ Admin location inserted successfully!")
        return jsonify({"message": "Admin location stored!"}), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error inserting admin location: {e}")  # Print error to console
        return jsonify({"error": str(e)}), 500




@app.route("/student_checkin", methods=["POST"])
def student_checkin():
    
    try:
        data = request.json
        print("Received Data:", data)  # Debugging incoming data

        required_fields = ["student_id", "name", "latitude", "longitude", "device_id"]
        if not all(key in data for key in required_fields):
            print("Error: Missing required fields")
            return jsonify({"error": "Missing required fields"}), 400
        
        latest_admin_location = AdminLocation.query.order_by(AdminLocation.timestamp.desc()).first()
        if not latest_admin_location:
            print("❌ No admin location found")
            return jsonify({"error": "No admin location found"}), 400

        print(f"📍 Latest Admin Location: {latest_admin_location.latitude}, {latest_admin_location.longitude}, {latest_admin_location.timestamp}")
        now_time=datetime.now()
        time_difference = (now_time - latest_admin_location.timestamp).total_seconds()
        print(time_difference)
        if time_difference > 300:
            print("time difference is more")
            return jsonify({"warning": "Time difference is not in the desired range"}), 200
        
        # Check if student has already checked in today
        print("Checking if student has already checked in...")
        student_check = Student.query.filter(and_(
            Student.student_id == data["student_id"],
            Student.date == date.today()
        )).first()
        
        if student_check:
            print("Student already checked in.")
            return jsonify({"warning": "This student ID has already checked in today."}), 200

        # Check if device has already been used for check-in today
        print("Checking if device has already been used for check-in...")
        device_check = Student.query.filter(and_(
            Student.device_id == data["device_id"],
            Student.date == date.today()
        )).first()
        
        if device_check:
            print("Device already checked in.")
            return jsonify({"warning": "This device has already been used for check-in today."}), 200

        # Insert new check-in record
        print("Inserting new student check-in record...")
        new_student = Student(
            student_id=data["student_id"],
            name=data["name"],
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            device_id=data["device_id"],
            timestamp=now_time,
            date=date.today()
        )

        db.session.add(new_student)
        db.session.commit()

        print("Student check-in successful!")
        return jsonify({"message": "Student check-in successful!"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error in student_checkin: {e}")  # Print actual error in console
        return jsonify({"error": str(e)}), 500
    
@app.route("/mark_attendance",methods=["POST"])
def mark_attendance():
    try:
        
        data = request.json
        print("Received data:", data)  # Debugging line

        if not data:
            return jsonify({'error': 'No data received'}), 400
        student_id = data.get('student_id')
        name = data.get('name')
        student_lat = data.get('latitude')
        student_long = data.get('longitude')
        device_id = data.get('device_id')
        latest_admin_location = AdminLocation.query.order_by(AdminLocation.timestamp.desc()).first()
        if not latest_admin_location:
            print("❌ No admin location found")
            return jsonify({"error": "No admin location found"}), 400

        print(f"📍 Latest Admin Location: {latest_admin_location.latitude}, {latest_admin_location.longitude}, {latest_admin_location.timestamp}")
        now_time=datetime.now()
        time_difference = (now_time - latest_admin_location.timestamp).total_seconds()

        if time_difference > 300:
            return jsonify({"warning": "Admin location is older than 5 minutes"}), 400

        print(f"⏳ Time Difference: {time_difference} seconds")

       
       
        distance = haversine(student_lat, student_long, latest_admin_location.latitude, latest_admin_location.longitude)

   
            
        print(f"Student: {student_id}, Distance: {distance} km")  # Debugging
        if distance > 0.5:  # 500m radius
            print("❌ Student is too far from admin")
            return jsonify({"warning": "You are not in teacher's range"}), 200
        else :
            existing_attendance = Attendance.query.filter(
                Attendance.student_id == student_id,
                Attendance.date == date.today()
            ).first()

            if not existing_attendance:
                new_attendance = Attendance(student_id=student_id, name=name)
                db.session.add(new_attendance)
                
                print(f"Marked Present: {student_id}")
                db.session.commit()
                return jsonify({
                    "message": "Attendance marked successfully",
                    }), 201
            else:
                return jsonify({"warning": "No new students within the attendance zone or already marked."}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in mark_attendance: {str(e)}")
        return jsonify({"error": str(e)}), 500




@app.route("/attendance", methods=["GET"])
def get_attendance():
    today = date.today()
    
    # Fetch all students
    all_students = Student.query.filter_by(date=today).all()
    # print("all_students" ,all_students)
    
    # Fetch today's attendance records
    attendance_records = Attendance.query.filter_by(date=today).all()
    # print("attendee",attendance_records)
    present_students = {rec.student_id for rec in attendance_records}
    # print(present_students)
    # Prepare response
    response = []
    for student in all_students:
        if student.student_id in present_students:
            status = "Present"
        else:
            status = "Proxy"
        
        response.append({
            "student_id": student.student_id,
            "name": student.name,
            "date": today.strftime("%Y-%m-%d"),
            "status": status
        })
    print(response)

    return jsonify({
        "total_present": len(present_students),
        "total_proxy": len(all_students) - len(present_students),
        "students": response
    })









# with app.app_context():
#     result = db.session.execute(text("SELECT * FROM admin_location")).fetchall()
#     print("📌 Admin Locations:", result)
# Initialize Database
with app.app_context():
    db.create_all()

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True, port=5000)

