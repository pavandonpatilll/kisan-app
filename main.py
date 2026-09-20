from fastapi.staticfiles import StaticFiles
import json
from urllib import response
from fastapi import UploadFile, File
from PIL import Image
import io
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from google import genai
import sqlite3
import razorpay
import hashlib
import hmac
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# ==========================
# Firebase Firestore
# ==========================

firebase_credentials_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

if firebase_credentials_json:

    firebase_cred = credentials.Certificate(
        json.loads(firebase_credentials_json)
    )

elif os.path.exists("firebase-service-account.json"):

    firebase_cred = credentials.Certificate(
        "firebase-service-account.json"
    )

else:

    raise RuntimeError("Firebase credentials not configured")


if not firebase_admin._apps:

    firebase_admin.initialize_app(firebase_cred)


firestore_db = firestore.client()

MANDI_API_KEY = os.getenv("MANDI_API_KEY")

# ==========================
# RAZORPAY
# ==========================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


# ==========================
# FastAPI
# ==========================

app = FastAPI(
    title="Kisan AI API",
    version="1.0"
)

# ==========================
# CREATE UPLOAD FOLDERS
# ==========================

os.makedirs(
    "uploads",
    exist_ok=True
)

os.makedirs(
    "uploads/chat",
    exist_ok=True
)


# ==========================
# STATIC UPLOADS
# ==========================

app.mount(
    "/uploads",
    StaticFiles(
        directory="uploads"
    ),
    name="uploads"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=GEMINI_API_KEY
)
GEMINI_MODELS = [

    "models/gemini-3.5-flash-lite",
    
    "models/gemini-2.5-flash",
    
    "models/gemini-2.0-flash",

    "models/gemini-3.1-flash-lite",

    "models/gemini-flash-latest",

   

]

# ==========================
# CORS
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# Database
# ==========================


DATABASE_PATH = "data/database.db"

# Create database folder if it does not exist
os.makedirs(
    os.path.dirname(DATABASE_PATH),
    exist_ok=True
)

conn = sqlite3.connect(
    DATABASE_PATH,
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT,

    mobile TEXT UNIQUE,

    village TEXT,

    password TEXT,

    crop TEXT,

    latitude REAL,

    longitude REAL

)
""")

conn.commit()


# ==========================
# Add location columns
# ==========================

try:

    cursor.execute(
        "ALTER TABLE users ADD COLUMN latitude REAL"
    )

except:

    pass


try:

    cursor.execute(
        "ALTER TABLE users ADD COLUMN longitude REAL"
    )

except:

    pass


try:

    cursor.execute(
        "ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'"
    )

except:

    pass


# ==========================
# PREMIUM COLUMNS MIGRATION
# ==========================

try:

    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN premium_plan TEXT DEFAULT ''
    """)

except sqlite3.OperationalError:

    pass


try:

    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN premium_expiry TEXT DEFAULT ''
    """)

except sqlite3.OperationalError:

    pass


try:

    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN razorpay_subscription_id TEXT DEFAULT ''
    """)

except sqlite3.OperationalError:

    pass

# ==========================
# RAZORPAY AUTOPAY / PAYMENT COLUMNS
# ==========================

try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN razorpay_subscription_status TEXT DEFAULT ''
    """)
except sqlite3.OperationalError:
    pass


try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN last_payment_status TEXT DEFAULT ''
    """)
except sqlite3.OperationalError:
    pass


try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN last_payment_date TEXT DEFAULT ''
    """)
except sqlite3.OperationalError:
    pass


try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN next_payment_date TEXT DEFAULT ''
    """)
except sqlite3.OperationalError:
    pass


# ==========================
# RAZORPAY PAYMENT ID
# ==========================

try:
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN razorpay_payment_id TEXT DEFAULT ''
    """)
except sqlite3.OperationalError:
    pass


conn.commit()


# ==========================
# Disease History
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS disease_history(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    crop TEXT,

    disease TEXT,

    confidence TEXT,

    severity TEXT,

    affected TEXT,

    date TEXT

)
""")

conn.commit()

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN reason TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN symptoms TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN medicine TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN organic TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN recovery TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN yield_loss TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN prevention TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN ai TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE disease_history ADD COLUMN weather TEXT")
except:
    pass

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS farmer_posts(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    crop TEXT,

    image TEXT,

    description TEXT,

    village TEXT,

    date TEXT

)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    sender_id INTEGER,

    receiver_id INTEGER,

    message TEXT,

    time TEXT

)
""")


conn.commit()

try:
    cursor.execute("""
        ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'hi'
    """)
    conn.commit()
    print("✅ language column added")
except Exception as e:
    print("Language column:", e)


# ==========================
# MANDI TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS mandi(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crop TEXT,
    location TEXT,
    min_price REAL,
    max_price REAL,
    avg_price REAL,
    date TEXT
)
""")

conn.commit()

# ==========================
# ADMIN TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE,

    password TEXT

)
""")

conn.commit()


# Default Admin
# Username: admin
# Password: admin123

admin_password = hashlib.sha256(
    "admin123".encode()
).hexdigest()

try:

    cursor.execute(
        "INSERT INTO admins (username, password) VALUES (?, ?)",
        ("admin", admin_password)
    )

    conn.commit()

except sqlite3.IntegrityError:

    pass


cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_news(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    title TEXT NOT NULL,

    description TEXT NOT NULL,

    date TEXT

)
""")

conn.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_crop_guides(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    crop TEXT NOT NULL,

    information TEXT NOT NULL,

    date TEXT

)
""")

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_disease_data(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    disease TEXT NOT NULL,

    crop TEXT NOT NULL,

    treatment TEXT NOT NULL,

    date TEXT

)
""")

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    message TEXT NOT NULL,

    date TEXT NOT NULL

)
""")

conn.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_schemes(


id INTEGER PRIMARY KEY AUTOINCREMENT,  

name TEXT NOT NULL,  

description TEXT NOT NULL,  

benefit TEXT NOT NULL,  

eligibility TEXT NOT NULL,  

state TEXT NOT NULL,  

apply_url TEXT NOT NULL,  

date TEXT NOT NULL  


)
""")

conn.commit()

# ==========================

# UPDATE MESSAGES TABLE

# ==========================

try:
    cursor.execute("""  
        ALTER TABLE messages  
        ADD COLUMN message_type TEXT DEFAULT 'text'  
    """)  
except sqlite3.OperationalError:
    pass  

try:
    cursor.execute("""  
        ALTER TABLE messages  
        ADD COLUMN image TEXT  
    """)  
except sqlite3.OperationalError:
    pass  


try:
    cursor.execute("""  
        ALTER TABLE messages  
        ADD COLUMN latitude REAL  
    """)  
except sqlite3.OperationalError:
    pass  


try:
    cursor.execute("""  
        ALTER TABLE messages  
        ADD COLUMN longitude REAL  
    """)  
except sqlite3.OperationalError:
    pass  


conn.commit()


# ==========================
# Password Hash
# ==========================

def hash_password(password):

    return hashlib.sha256(password.encode()).hexdigest()

# ==========================
# Models
# ==========================

class RegisterModel(BaseModel):

    name:str

    mobile:str

    village:str

    crop:str

    password:str

    language: str = "hi"


class LoginModel(BaseModel):

    mobile:str

    password:str

class LocationModel(BaseModel):

    user_id:int

    latitude:float

    longitude:float    

class HomeCropModel(BaseModel):
        user_id: int
        crop: str


class AdminLoginModel(BaseModel):

    username: str

    password: str


class AdminNewsModel(BaseModel):

    title: str

    description: str


class AdminCropGuideModel(BaseModel):

    crop: str

    information: str


class AdminDiseaseModel(BaseModel):

    disease: str

    crop: str

    treatment: str


class NotificationModel(BaseModel):

    message: str

class SchemeModel(BaseModel):

    name: str
    description: str
    benefit: str
    eligibility: str
    state: str
    apply_url: str


# ==========================
# ADMIN LOGIN API
# ==========================

@app.post("/admin/login")
def admin_login(data: AdminLoginModel):

    password_hash = hashlib.sha256(
        data.password.encode()
    ).hexdigest()


    cursor.execute(
        """
        SELECT
            id,
            username
        FROM admins
        WHERE username = ?
        AND password = ?
        """,
        (
            data.username,
            password_hash
        )
    )


    admin = cursor.fetchone()


    if not admin:

        return {
            "status": False,
            "message": "Invalid username or password"
        }


    return {

        "status": True,

        "message": "Admin login successful",

        "admin": {

            "id": admin[0],

            "username": admin[1]

        }

    }



# ==========================
# ADMIN DASHBOARD - FIRESTORE
# ==========================

@app.get("/admin/dashboard")
def admin_dashboard():

    try:

        # ==========================
        # USERS
        # ==========================

        users_docs = (
            firestore_db
            .collection("users")
            .stream()
        )

        total_users = sum(
            1 for _ in users_docs
        )


        # ==========================
        # DISEASE HISTORY
        # ==========================

        disease_docs = (
            firestore_db
            .collection("disease_history")
            .stream()
        )

        total_disease = sum(
            1 for _ in disease_docs
        )


        # ==========================
        # MANDI
        # ==========================

        mandi_docs = (
            firestore_db
            .collection("mandi")
            .stream()
        )

        total_mandi = sum(
            1 for _ in mandi_docs
        )


        # ==========================
        # ADMIN NEWS
        # ==========================

        news_docs = (
            firestore_db
            .collection("admin_news")
            .stream()
        )

        total_news = sum(
            1 for _ in news_docs
        )


        # ==========================
        # RESPONSE
        # ==========================

        return {

            "status": True,

            "totalUsers":
                total_users,

            "totalMandi":
                total_mandi,

            "totalNews":
                total_news,

            "totalDisease":
                total_disease

        }


    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }



# ==========================
# ADMIN USERS - FIRESTORE
# ==========================

@app.get("/admin/users")
def admin_users():

    users = []

    user_docs = (
        firestore_db
        .collection("users")
        .stream()
    )

    for doc in user_docs:

        data = doc.to_dict()

        users.append({

            "id": data.get("id", doc.id),

            "name": data.get("name", ""),

            "mobile": data.get("mobile", ""),

            "village": data.get("village", ""),

            "crop": data.get("crop", ""),

            "language": data.get("language", "")

        })

    return {

        "status": True,

        "users": users

    }


# ==========================
# ADMIN PREMIUM USERS - FIRESTORE
# ==========================

@app.get("/admin/premium-users")
def admin_premium_users():

    user_docs = firestore_db.collection("users").stream()

    users = []

    for doc in user_docs:

        data = doc.to_dict()

        plan = data.get("premium_plan") or ""
        expiry = data.get("premium_expiry") or ""

        subscription_status = (
            data.get("razorpay_subscription_status") or ""
        )

        last_payment_status = (
            data.get("last_payment_status") or ""
        )

        plan_lower = plan.lower()

        # ==========================
        # PREMIUM STATUS
        # ==========================

        if not plan:

            premium_status = "free"

        elif "advanced" in plan_lower:

            premium_status = "advanced"

        elif "basic" in plan_lower:

            premium_status = "basic"

        else:

            premium_status = "free"

        # ==========================
        # EXPIRY CHECK
        # ==========================

        if expiry:

            try:

                expiry_date = datetime.fromisoformat(expiry)

                if expiry_date < datetime.now():

                    premium_status = "expired"

            except:

                pass

        # ==========================
        # AUTOPAY STATUS
        # ==========================

        if subscription_status == "halted":

            autopay_status = "halted"

        elif subscription_status == "cancelled":

            autopay_status = "cancelled"

        elif subscription_status in [
            "charged",
            "activated",
            "authenticated"
        ]:

            autopay_status = "active"

        elif subscription_status == "pending":

            autopay_status = "pending"

        elif subscription_status:

            autopay_status = subscription_status

        else:

            autopay_status = "-"

        users.append({

            "id": data.get("id", doc.id),

            "name": data.get("name", ""),

            "mobile": data.get("mobile", ""),

            "premium_plan":
                plan if plan else "Free",

            "premium_expiry":
                expiry if expiry else "-",

            "premium_status":
                premium_status,

            "razorpay_subscription_id":
                data.get("razorpay_subscription_id") or "-",

            "razorpay_payment_id":
                data.get("razorpay_payment_id") or "-",

            "razorpay_subscription_status":
                subscription_status or "-",

            "autopay_status":
                autopay_status,

            "last_payment_status":
                last_payment_status or "-",

            "last_payment_date":
                data.get("last_payment_date") or "-",

            "next_payment_date":
                data.get("next_payment_date") or "-"

        })

    return {

        "status": True,

        "users": users

    }

# ==========================
# ADMIN ADD MANDI
# ==========================

class MandiModel(BaseModel):

    crop: str
    location: str
    min_price: float
    max_price: float
    avg_price: float


# ==========================
# ADMIN ADD MANDI - FIRESTORE
# ==========================

@app.post("/admin/mandi")
def add_mandi(data: MandiModel):

    try:

        mandi_id = str(uuid.uuid4())

        mandi_data = {

            "id": mandi_id,

            "crop": data.crop.strip(),

            "location": data.location.strip(),

            "min_price": data.min_price,

            "max_price": data.max_price,

            "avg_price": data.avg_price,

            "date": datetime.now().strftime("%Y-%m-%d"),

            "created_at": datetime.now().isoformat()

        }

        firestore_db.collection("mandi").document(
            mandi_id
        ).set(mandi_data)

        return {

            "status": True,

            "message": "Mandi rate added successfully",

            "saved": mandi_data

        }

    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }



# ==========================
# ADMIN MANDI LIST - FIRESTORE
# ==========================

@app.get("/admin/mandi")
def get_admin_mandi():

    mandi_docs = (
        firestore_db
        .collection("mandi")
        .stream()
    )

    mandi = []

    for doc in mandi_docs:

        data = doc.to_dict()

        mandi.append({

            "id": data.get("id", doc.id),

            "crop": data.get("crop", ""),

            "location": data.get("location", ""),

            "min_price": data.get("min_price", 0),

            "max_price": data.get("max_price", 0),

            "avg_price": data.get("avg_price", 0),

            "date": data.get("date", ""),

            "_created_at": data.get("created_at", "")

        })

    mandi.sort(
        key=lambda x: x.get("_created_at", ""),
        reverse=True
    )

    for item in mandi:
        item.pop("_created_at", None)

    return {

        "status": True,

        "mandi": mandi

    }


class NotificationModel(BaseModel):
    message: str

# ==========================
# ADMIN ADD NOTIFICATION - FIRESTORE
# ==========================

@app.post("/admin/notification")
def add_notification(data: NotificationModel):

    try:

        message = data.message.strip()

        if not message:

            return {
                "status": False,
                "message": "Notification message is required"
            }

        notification_id = str(uuid.uuid4())

        notification_data = {

            "id": notification_id,

            "message": message,

            "date": datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),

            "created_at": datetime.now().isoformat()

        }

        firestore_db.collection(
            "notifications"
        ).document(
            notification_id
        ).set(
            notification_data
        )

        return {

            "status": True,

            "message": "Notification sent successfully"

        }

    except Exception as e:

        print(
            "NOTIFICATION ERROR:",
            str(e)
        )

        return {

            "status": False,

            "message": str(e)

        }


# ==========================
# GET NOTIFICATIONS - FIRESTORE
# ==========================

@app.get("/notifications/{user_id}")
def get_notifications(user_id: str):

    try:

        notification_docs = (
            firestore_db
            .collection("notifications")
            .stream()
        )

        notifications = []

        for doc in notification_docs:

            data = doc.to_dict()

            notifications.append({

                "id": data.get(
                    "id",
                    doc.id
                ),

                "message": data.get(
                    "message",
                    ""
                ),

                "date": data.get(
                    "date",
                    ""
                ),

                "_created_at": data.get(
                    "created_at",
                    ""
                )

            })


        # Latest notifications first
        notifications.sort(
            key=lambda x: x.get(
                "_created_at",
                ""
            ),
            reverse=True
        )


        # Only latest 20
        notifications = notifications[:20]


        # Remove internal sorting field
        for item in notifications:

            item.pop(
                "_created_at",
                None
            )


        return {

            "status": True,

            "notifications": notifications

        }


    except Exception as e:

        print(
            "GET NOTIFICATIONS ERROR:",
            str(e)
        )

        return {

            "status": False,

            "message": str(e)

        }



# ==========================
# Register API - FIRESTORE
# ==========================

@app.post("/register")
def register(user: RegisterModel):

    # Mobile Validation
    if len(user.mobile) != 10 or not user.mobile.isdigit():
        return {
            "status": False,
            "message": "Enter Valid Mobile Number"
        }

    # Language Validation
    if user.language not in ["mr", "hi", "en"]:
        user.language = "hi"

    # Duplicate Mobile Check
    existing_users = (
        firestore_db
        .collection("users")
        .where("mobile", "==", user.mobile)
        .limit(1)
        .stream()
    )

    for existing_user in existing_users:
        return {
            "status": False,
            "message": "Mobile Number Already Registered"
        }

    # Create Firestore User ID
    user_id = str(uuid.uuid4())

    # Save User
    user_data = {
        "id": user_id,
        "name": user.name,
        "mobile": user.mobile,
        "village": user.village,
        "crop": user.crop,
        "password": hash_password(user.password),
        "language": user.language,
        "latitude": None,
        "longitude": None,
        "created_at": datetime.now().isoformat()
    }

    firestore_db.collection("users").document(user_id).set(user_data)

    return {
        "status": True,
        "message": "Registration Successful"
    }


# ==========================
# Login API - FIRESTORE
# ==========================

@app.post("/login")
def login(user: LoginModel):

    # Find User By Mobile
    users = (
        firestore_db
        .collection("users")
        .where("mobile", "==", user.mobile)
        .limit(1)
        .stream()
    )

    user_doc = None

    for doc in users:
        user_doc = doc
        break

    # User Not Found
    if user_doc is None:
        return {
            "status": False,
            "message": "User Not Found"
        }

    data = user_doc.to_dict()

    # Password Check
    if data.get("password") != hash_password(user.password):
        return {
            "status": False,
            "message": "Wrong Password"
        }

    return {
        "status": True,
        "message": "Login Successful",
        "user": {
            "id": data.get("id"),
            "name": data.get("name"),
            "mobile": data.get("mobile"),
            "village": data.get("village"),
            "crop": data.get("crop")
        }
    }

# ==========================
# Get Profile API
# ==========================

# ==========================
# Profile API - FIRESTORE
# ==========================

@app.get("/profile/{user_id}")
def get_profile(user_id: str):

    try:

        user_doc = (
            firestore_db
            .collection("users")
            .document(user_id)
            .get()
        )

        if not user_doc.exists:

            return {
                "status": False,
                "message": "User Not Found"
            }

        user = user_doc.to_dict()

        return {

            "status": True,

            "user": {

                "id": user.get("id", user_doc.id),

                "name": user.get("name", ""),

                "mobile": user.get("mobile", ""),

                "village": user.get("village", "")

            }

        }

    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }


# ==========================
# Save User Location - FIRESTORE
# ==========================

@app.post("/save-location")
def save_location(data: LocationModel):

    try:

        user_ref = (
            firestore_db
            .collection("users")
            .document(str(data.user_id))
        )

        user_doc = user_ref.get()

        if not user_doc.exists:

            return {

                "status": False,

                "message": "User Not Found"

            }

        user_ref.update({

            "latitude": data.latitude,

            "longitude": data.longitude

        })

        return {

            "status": True,

            "message": "Location Saved",

            "latitude": data.latitude,

            "longitude": data.longitude

        }

    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }

# ==========================
# Weather API
# ==========================

@app.get("/weather/{lat}/{lon}")
def get_weather(lat: float, lon: float):

    try:

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}"
            f"&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            "&hourly=precipitation_probability,relative_humidity_2m,wind_speed_10m"
            "&daily="
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "sunrise,"
            "sunset,"
            "precipitation_probability_max"
            "&forecast_days=7"
            "&timezone=auto"
        )


        response = requests.get(
            url,
            timeout=10
        )


        response.raise_for_status()


        data = response.json()


        current = data["current"]


        # Current hour rain probability

        current_time = current["time"]

        try:

            current_hour = data["hourly"]["time"].index(
                current_time
            )

            rain_probability = data["hourly"]["precipitation_probability"][current_hour]


        except:

            rain_probability = 0



        return {


            "status": True,


            "latitude": lat,


            "longitude": lon,


            "temperature": current["temperature_2m"],


            "humidity": current["relative_humidity_2m"],


            "wind": current["wind_speed_10m"],


            "weather_code": current["weather_code"],


            "rain_probability": rain_probability,


            "forecast":{


                "date":
                data["daily"]["time"],


                "weather_code":
                data["daily"]["weather_code"],


                "max":
                data["daily"]["temperature_2m_max"],


                "min":
                data["daily"]["temperature_2m_min"],


                "sunrise":
                data["daily"]["sunrise"],


                "sunset":
                data["daily"]["sunset"],


                "rain":
                data["daily"]["precipitation_probability_max"]


            }

        }



    except Exception as e:


        return {


            "status": False,


            "message": str(e)


        }

@app.get("/location/{lat}/{lon}")
def get_location(lat: float, lon: float):

    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?format=jsonv2&lat={lat}&lon={lon}"
    )

    headers = {
        "User-Agent": "KisanAI/1.0"
    }

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        return {
            "status": False,
            "message": "Location not found"
        }

    data = response.json()

    address = data.get("address", {})

    village = (
        address.get("village")
        or address.get("town")
        or address.get("city")
        or address.get("hamlet")
        or "Unknown"
    )

    state = address.get("state", "")

    district = (
        address.get("county")
        or address.get("state_district")
        or ""
    )

    return {
        "status": True,
        "village": village,
        "district": district,
        "state": state,
        "country": address.get("country", "")
    }


@app.get("/location-name/{lat}/{lon}")
def location_name(lat:float, lon:float):

    try:

        url=f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"


        response=requests.get(
            url,
            headers={
                "User-Agent":"KisanAI"
            },
            timeout=10
        )


        data=response.json()


        address=data.get("address",{})


        city=(
            address.get("city")
            or
            address.get("town")
            or
            address.get("village")
            or
            "Unknown"
        )


        state=address.get(
            "state",
            ""
        )


        return {

            "status":True,

            "location":
            city+", "+state

        }


    except Exception as e:


        return {

            "status":False,

            "message":str(e)

        }


@app.get("/crop-guide/{user_id}/{crop}")
def crop_guide(user_id: int, crop: str):

    try:

        # --------------------------------
        # USER DATA
        # --------------------------------

        cursor.execute("""
            SELECT village, latitude, longitude, language
            FROM users
            WHERE id=?
        """, (user_id,))

        user = cursor.fetchone()

        if user is None:
            return {
                "status": False,
                "message": "User not found"
            }

        village = user[0]
        latitude = user[1]
        longitude = user[2]
        language = user[3] or "hi"


        if crop.strip() == "":
            crop = "General Crop"


        # --------------------------------
        # ADMIN CROP GUIDE
        # --------------------------------

        admin_information = ""

        try:

            cursor.execute("""
                SELECT information
                FROM admin_crop_guides
                WHERE LOWER(crop) = LOWER(?)
                ORDER BY id DESC
                LIMIT 1
            """, (crop,))

            admin_row = cursor.fetchone()

            if admin_row:

                admin_information = admin_row[0] or ""

        except Exception as e:

            print(
                "ADMIN CROP GUIDE ERROR:",
                str(e)
            )


        # --------------------------------
        # LANGUAGE
        # --------------------------------

        language_instruction = {

            "mr": """
Answer only in simple Marathi.
Use natural farmer-friendly Marathi.
Do not answer in Hindi.
Do not answer in English unless a technical word is necessary.
""",

            "hi": """
Answer only in simple Hindi.
Use natural farmer-friendly Hindi.
Do not answer in Marathi.
Do not answer in English unless a technical word is necessary.
""",

            "en": """
Answer only in simple English.
Use simple farmer-friendly English.
Do not answer in Hindi or Marathi.
"""

        }.get(
            language,
            """
Answer only in simple Hindi.
Use natural farmer-friendly Hindi.
"""
        )


        # --------------------------------
        # DEFAULT WEATHER VALUES
        # --------------------------------

        temperature = "--"
        humidity = "--"
        wind = "--"
        weather_name = "--"
        rain = "--"


        # --------------------------------
        # LIVE WEATHER
        # --------------------------------

        try:

            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={latitude}"
                f"&longitude={longitude}"
                "&current=temperature_2m,"
                "relative_humidity_2m,"
                "wind_speed_10m,"
                "weather_code"
                "&hourly=precipitation_probability"
                "&timezone=auto"
            )


            weather_response = requests.get(
                url,
                timeout=10
            )


            weather_response.raise_for_status()

            weather_data = weather_response.json()


            current = weather_data["current"]


            temperature = current["temperature_2m"]

            humidity = current["relative_humidity_2m"]

            wind = current["wind_speed_10m"]

            code = current["weather_code"]


            weather_names = {

                0: "Clear Sky",

                1: "Mainly Clear",

                2: "Partly Cloudy",

                3: "Cloudy",

                45: "Fog",

                48: "Fog",

                51: "Light Drizzle",

                53: "Drizzle",

                55: "Heavy Drizzle",

                61: "Light Rain",

                63: "Rain",

                65: "Heavy Rain",

                71: "Light Snow",

                73: "Snow",

                75: "Heavy Snow",

                80: "Rain Showers",

                81: "Heavy Rain Showers",

                82: "Violent Rain",

                95: "Thunderstorm"

            }


            weather_name = weather_names.get(
                code,
                "Unknown"
            )


            try:

                index = weather_data[
                    "hourly"
                ][
                    "time"
                ].index(
                    current["time"]
                )


                rain = weather_data[
                    "hourly"
                ][
                    "precipitation_probability"
                ][index]


            except Exception:

                rain = 0


        except Exception as e:

            print(
                "Weather Error:",
                str(e)
            )


        # --------------------------------
        # AI PROMPT
        # --------------------------------

        prompt = f"""

You are India's best agriculture expert.

IMPORTANT LANGUAGE RULE:

{language_instruction}


Farmer Details

Crop: {crop}

Village: {village}


ADMIN CROP GUIDE INFORMATION

{admin_information if admin_information else "No admin guide available for this crop."}


Today's Live Weather

Temperature: {temperature} °C

Humidity: {humidity} %

Wind Speed: {wind} km/h

Weather: {weather_name}

Rain Chance: {rain} %


Give practical farming advice for this farmer.

Consider:

1. The selected crop.
2. The Admin Crop Guide Information if available.
3. Today's live weather.
4. Rain probability.
5. Practical farming conditions.


Reply ONLY exactly in this format:

Stage: ...

Irrigation: ...

Fertilizer: ...

Weather: ...

Pest: ...

AI: ...


IMPORTANT:

- Keep every answer within ONE short sentence.
- Keep advice practical.
- Use simple farmer-friendly language.
- Do not change the labels.
- Do not add extra sections.
- Follow the selected language strictly.

"""


        # --------------------------------
        # GEMINI
        # --------------------------------

        response = None

        last_error = ""


        for model_name in GEMINI_MODELS:

            try:

                print(
                    "Trying:",
                    model_name
                )


                response = client.models.generate_content(

                    model=model_name,

                    contents=prompt

                )


                print(
                    "Success:",
                    model_name
                )


                break


            except Exception as e:

                print(
                    "Failed:",
                    model_name
                )

                last_error = str(e)


        if response is None:

            return {

                "status": False,

                "message": last_error

            }


        text = response.text.strip()


        # --------------------------------
        # DEFAULT AI VALUES
        # --------------------------------

        stage = "--"

        irrigation = "--"

        fertilizer = "--"

        weather = "--"

        pest = "--"

        ai = "--"


        # --------------------------------
        # PARSE AI RESPONSE
        # --------------------------------

        for line in text.split("\n"):

            line = line.strip()


            if line.startswith("Stage:"):

                stage = line.replace(
                    "Stage:",
                    "",
                    1
                ).strip()


            elif line.startswith("Irrigation:"):

                irrigation = line.replace(
                    "Irrigation:",
                    "",
                    1
                ).strip()


            elif line.startswith("Fertilizer:"):

                fertilizer = line.replace(
                    "Fertilizer:",
                    "",
                    1
                ).strip()


            elif line.startswith("Weather:"):

                weather = line.replace(
                    "Weather:",
                    "",
                    1
                ).strip()


            elif line.startswith("Pest:"):

                pest = line.replace(
                    "Pest:",
                    "",
                    1
                ).strip()


            elif line.startswith("AI:"):

                ai = line.replace(
                    "AI:",
                    "",
                    1
                ).strip()


        # --------------------------------
        # FINAL RESPONSE
        # --------------------------------

        return {

            "status": True,

            "crop": crop,

            "location": village,

            # ADMIN GUIDE
            "admin_guide": admin_information,

            # LIVE WEATHER
            "temperature": temperature,

            "humidity": humidity,

            "wind": wind,

            "weather_live": weather_name,

            "rain_probability": rain,

            # AI
            "stage": stage,

            "irrigation": irrigation,

            "fertilizer": fertilizer,

            "weather": weather,

            "pest": pest,

            "ai": ai

        }


    except Exception as e:

        print(
            "Crop Guide Error:",
            str(e)
        )


        return {

            "status": False,

            "message": str(e)

        }
    


# ==========================
# ADMIN ADD CROP GUIDE - FIRESTORE
# ==========================

@app.post("/admin/crop-guide")
def add_admin_crop_guide(data: AdminCropGuideModel):

    try:

        crop = data.crop.strip()
        information = data.information.strip()

        if not crop or not information:

            return {
                "status": False,
                "message": "Crop name and information required"
            }

        guide_id = str(uuid.uuid4())

        crop_guide_data = {

            "id": guide_id,

            "crop": crop,

            "information": information,

            "date": datetime.now().strftime("%Y-%m-%d"),

            "created_at": datetime.now().isoformat()

        }

        firestore_db.collection(
            "admin_crop_guides"
        ).document(guide_id).set(
            crop_guide_data
        )

        return {

            "status": True,

            "message": "Crop guide added successfully"

        }

    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }
# ==========================
# DISEASE SCAN - FIRESTORE
# ==========================

@app.post("/disease-scan")
async def disease_scan(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):

    try:

        image_bytes = await file.read()

        image = Image.open(
            io.BytesIO(image_bytes)
        )


        # ==========================
        # GET USER LOCATION - FIRESTORE
        # ==========================

        user_ref = (
            firestore_db
            .collection("users")
            .document(str(user_id))
        )

        user_doc = user_ref.get()

        if not user_doc.exists:

            return {
                "status": False,
                "message": "User Not Found"
            }

        user_data = user_doc.to_dict()

        latitude = user_data.get("latitude")
        longitude = user_data.get("longitude")

        language = (
            user_data.get("language")
            if user_data.get("language")
            else "en"
        )

        weather_info = "Weather data unavailable"


        # ==========================
        # WEATHER DATA
        # ==========================

        if latitude is not None and longitude is not None:

            try:

                weather_url = (
                    "https://api.open-meteo.com/v1/forecast?"
                    f"latitude={latitude}"
                    f"&longitude={longitude}"
                    "&current=temperature_2m,relative_humidity_2m"
                )

                weather_response = requests.get(
                    weather_url,
                    timeout=8
                )

                weather_response.raise_for_status()

                weather = weather_response.json()

                current = weather["current"]

                weather_info = f"""
Temperature:
{current['temperature_2m']} C

Humidity:
{current['relative_humidity_2m']} %
"""


            except Exception as e:

                print(
                    "Weather API Failed:",
                    e
                )

                weather_info = """
Temperature:
Unknown

Humidity:
Unknown
"""


        # ==========================
        # GEMINI AI
        # ==========================

        response = None

        last_error = ""


        for model_name in GEMINI_MODELS:

            try:

                print(
                    "Trying Model:",
                    model_name
                )


                response = client.models.generate_content(

                    model=model_name,

                    contents=[

                        f"""

You are India's best agriculture scientist.

Analyze this crop image.

Selected Language:
{language}

Use:
mr = Marathi
hi = Hindi
en = English

Reply in the farmer's selected language.

Current Weather:

{weather_info}

If image is not plant, crop, leaf, fruit or vegetable reply:

Invalid Image

Otherwise reply only:

Crop:
Disease:
Confidence:
Severity:
Affected Part:
Reason:
Symptoms:
Chemical Medicine:
Organic Treatment:
Recovery Time:
Yield Loss:
Prevention:
AI Recommendation:

Rules:

Confidence in percentage.
Recovery time estimate.
Yield loss estimate.
Each answer one short sentence.

""",

                        image

                    ]

                )


                print(
                    "SUCCESS:",
                    model_name
                )

                break


            except Exception as e:

                print(
                    "FAILED:",
                    model_name
                )

                last_error = str(e)


        if response is None:

            return {
                "status": False,
                "message": last_error
            }


        text = response.text.strip()


        # ==========================
        # INVALID IMAGE
        # ==========================

        if text.lower().startswith(
            "invalid image"
        ):

            return {
                "status": False,
                "message": "Please upload crop image."
            }


        # ==========================
        # RESULT FORMAT
        # ==========================

        result = {

            "crop": "--",

            "disease": "--",

            "confidence": "--",

            "severity": "--",

            "affected": "--",

            "reason": "--",

            "symptoms": "--",

            "medicine": "--",

            "organic": "--",

            "recovery": "--",

            "yield_loss": "--",

            "prevention": "--",

            "ai": "--"

        }


        # ==========================
        # PARSE AI RESPONSE
        # ==========================

        for line in text.split("\n"):

            line = line.strip()


            if line.startswith("Crop:"):

                result["crop"] = line.replace(
                    "Crop:",
                    "",
                    1
                ).strip()


            elif line.startswith("Disease:"):

                result["disease"] = line.replace(
                    "Disease:",
                    "",
                    1
                ).strip()


            elif line.startswith("Confidence:"):

                result["confidence"] = line.replace(
                    "Confidence:",
                    "",
                    1
                ).strip()


            elif line.startswith("Severity:"):

                result["severity"] = line.replace(
                    "Severity:",
                    "",
                    1
                ).strip()


            elif line.startswith("Affected Part:"):

                result["affected"] = line.replace(
                    "Affected Part:",
                    "",
                    1
                ).strip()


            elif line.startswith("Reason:"):

                result["reason"] = line.replace(
                    "Reason:",
                    "",
                    1
                ).strip()


            elif line.startswith("Symptoms:"):

                result["symptoms"] = line.replace(
                    "Symptoms:",
                    "",
                    1
                ).strip()


            elif line.startswith("Chemical Medicine:"):

                result["medicine"] = line.replace(
                    "Chemical Medicine:",
                    "",
                    1
                ).strip()


            elif line.startswith("Organic Treatment:"):

                result["organic"] = line.replace(
                    "Organic Treatment:",
                    "",
                    1
                ).strip()


            elif line.startswith("Recovery Time:"):

                result["recovery"] = line.replace(
                    "Recovery Time:",
                    "",
                    1
                ).strip()


            elif line.startswith("Yield Loss:"):

                result["yield_loss"] = line.replace(
                    "Yield Loss:",
                    "",
                    1
                ).strip()


            elif line.startswith("Prevention:"):

                result["prevention"] = line.replace(
                    "Prevention:",
                    "",
                    1
                ).strip()


            elif line.startswith("AI Recommendation:"):

                result["ai"] = line.replace(
                    "AI Recommendation:",
                    "",
                    1
                ).strip()


        # ==========================
        # ADMIN DISEASE DATA - FIRESTORE
        # ==========================

        admin_treatment = ""

        try:

            ai_crop = result["crop"].strip()
            ai_disease = result["disease"].strip()


            # ==========================
            # EXACT MATCH
            # ==========================

            disease_docs = (
                firestore_db
                .collection("admin_disease_data")
                .stream()
            )

            admin_row = None

            for doc in disease_docs:

                data = doc.to_dict()

                db_crop = str(
                    data.get("crop", "")
                ).strip().lower()

                db_disease = str(
                    data.get("disease", "")
                ).strip().lower()

                if (
                    db_crop == ai_crop.lower()
                    and
                    db_disease == ai_disease.lower()
                ):

                    admin_row = data
                    break


            # ==========================
            # DISEASE NAME FALLBACK
            # ==========================

            if not admin_row:

                english_disease = (
                    ai_disease
                    .split("(")[-1]
                    .replace(")", "")
                    .strip()
                    .lower()
                )

                disease_docs = (
                    firestore_db
                    .collection("admin_disease_data")
                    .stream()
                )

                for doc in disease_docs:

                    data = doc.to_dict()

                    db_disease = str(
                        data.get("disease", "")
                    ).strip().lower()

                    if (
                        ai_disease.lower() in db_disease
                        or
                        db_disease in ai_disease.lower()
                        or
                        english_disease in db_disease
                        or
                        db_disease in english_disease
                    ):

                        admin_row = data
                        break


            # ==========================
            # GET ADMIN TREATMENT
            # ==========================

            if admin_row:

                admin_treatment = (
                    admin_row.get("treatment", "")
                    or ""
                )


        except Exception as e:

            print(
                "ADMIN DISEASE LOOKUP ERROR:",
                str(e)
            )


        # ==========================
        # SAVE HISTORY - FIRESTORE
        # ==========================

        history_id = str(uuid.uuid4())

        history_data = {

            "id": history_id,

            "user_id": str(user_id),

            "crop": result["crop"],

            "disease": result["disease"],

            "confidence": result["confidence"],

            "severity": result["severity"],

            "affected": result["affected"],

            "reason": result["reason"],

            "symptoms": result["symptoms"],

            "medicine": result["medicine"],

            "organic": result["organic"],

            "recovery": result["recovery"],

            "yield_loss": result["yield_loss"],

            "prevention": result["prevention"],

            "ai": result["ai"],

            "weather": weather_info,

            "date": datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),

            "created_at": datetime.now().isoformat()

        }


        firestore_db.collection(
            "disease_history"
        ).document(history_id).set(
            history_data
        )


        # ==========================
        # FINAL RESPONSE
        # ==========================

        return {

            "status": True,

            **result,

            "weather": weather_info,

            "admin_treatment":
                admin_treatment

        }


    except Exception as e:

        print(
            "DISEASE SCAN ERROR:",
            str(e)
        )

        return {

            "status": False,

            "message": str(e)

        }


# ==========================
# ADMIN ADD DISEASE - FIRESTORE
# ==========================

@app.post("/admin/disease")
def add_admin_disease(data: AdminDiseaseModel):

    try:

        disease = data.disease.strip()
        crop = data.crop.strip()
        treatment = data.treatment.strip()

        if not disease or not crop or not treatment:

            return {
                "status": False,
                "message": "Please fill all fields"
            }

        disease_id = str(uuid.uuid4())

        disease_data = {

            "id": disease_id,

            "disease": disease,

            "crop": crop,

            "treatment": treatment,

            "date": datetime.now().strftime("%Y-%m-%d"),

            "created_at": datetime.now().isoformat()

        }

        firestore_db.collection(
            "admin_disease_data"
        ).document(disease_id).set(disease_data)

        return {

            "status": True,

            "message": "Disease data added successfully"

        }

    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }


# ==========================
# DISEASE HISTORY - FIRESTORE
# ==========================

@app.get("/disease-history/{user_id}")
def disease_history(user_id: str):

    try:

        history_docs = (
            firestore_db
            .collection("disease_history")
            .where("user_id", "==", str(user_id))
            .stream()
        )

        history = []

        for doc in history_docs:

            data = doc.to_dict()

            history.append({

                "crop": data.get("crop", ""),

                "disease": data.get("disease", ""),

                "confidence": data.get("confidence", ""),

                "severity": data.get("severity", ""),

                "affected": data.get("affected", ""),

                "reason": data.get("reason", ""),

                "symptoms": data.get("symptoms", ""),

                "medicine": data.get("medicine", ""),

                "organic": data.get("organic", ""),

                "recovery": data.get("recovery", ""),

                "yield_loss": data.get("yield_loss", ""),

                "prevention": data.get("prevention", ""),

                "ai": data.get("ai", ""),

                "weather": data.get("weather", ""),

                "date": data.get("date", "")

            })

        # Latest records first
        history.sort(
            key=lambda x: x.get("date", ""),
            reverse=True
        )

        return {

            "status": True,

            "count": len(history),

            "history": history

        }

    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }


# ==========================
# CHECK DISEASE HISTORY - FIRESTORE
# ==========================

@app.get("/check-history")
def check_history():

    try:

        history_docs = (
            firestore_db
            .collection("disease_history")
            .stream()
        )

        data = []

        for doc in history_docs:

            item = doc.to_dict()

            item["firestore_id"] = doc.id

            data.append(item)

        return {

            "data": data

        }

    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }


@app.get("/farming-advice/{user_id}")
def farming_advice(user_id: int):

    try:

        # =========================
        # USER DATA + LANGUAGE
        # =========================

        cursor.execute("""
        SELECT crop, village, latitude, longitude, language
        FROM users
        WHERE id=?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:

            return {
                "status": False,
                "message": "User not found"
            }


        crop = user[0]
        village = user[1]
        latitude = user[2]
        longitude = user[3]
        language = user[4] or "hi"


        # =========================
        # LANGUAGE
        # =========================

        language_names = {

            "mr": "Marathi",
            "hi": "Hindi",
            "en": "English"

        }

        selected_language = language_names.get(
            language,
            "Hindi"
        )


        # =========================
        # WEATHER
        # =========================

        weather_info = "Weather unavailable"


        if latitude and longitude:

            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={latitude}"
                f"&longitude={longitude}"
                "&current=temperature_2m,"
                "relative_humidity_2m,"
                "rain"
            )


            weather_response = requests.get(
                url,
                timeout=10
            )


            weather = weather_response.json()

            current = weather["current"]


            weather_info = f"""
Temperature:
{current.get('temperature_2m', '--')} C

Humidity:
{current.get('relative_humidity_2m', '--')} %

Rain:
{current.get('rain', 0)} mm
"""


        # =========================
        # LAST DISEASE
        # =========================

        cursor.execute("""
        SELECT disease, severity
        FROM disease_history
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 1
        """, (user_id,))


        disease = cursor.fetchone()


        disease_info = "No recent disease"


        if disease:

            disease_info = f"""
Disease:
{disease[0]}

Severity:
{disease[1]}
"""


        # =========================
        # AI PROMPT
        # =========================

        prompt = f"""

You are India's best agriculture expert.

The farmer selected language: {selected_language}

IMPORTANT:
Reply ONLY in {selected_language}.
Do NOT use Hindi, Marathi or English mixed language.
Use simple language that an Indian farmer can easily understand.

Farmer Details:

Crop:
{crop}

Village:
{village}

Weather:

{weather_info}

Disease History:

{disease_info}


Give short and practical farming advice.

Use exactly this format:

🌱 Crop Status:
💧 Irrigation Advice:
💊 Disease Protection:
🌿 Fertilizer Advice:
⚠ Alert:
🤖 AI Recommendation:

Keep every section short and practical.
"""


        # =========================
        # GEMINI
        # =========================

        response = client.models.generate_content(

            model=GEMINI_MODELS[0],

            contents=prompt

        )


        # =========================
        # RESPONSE
        # =========================

        return {

            "status": True,

            "crop": crop,

            "language": language,

            "weather": weather_info,

            "advice": response.text

        }


    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }

@app.post("/ai-chat")
async def ai_chat(data: dict):

    try:

        question = data["question"]

        language = data.get("language", "hi")

        language_instruction = data.get(
            "language_instruction",
            "Answer only in simple Hindi."
        )

        response = client.models.generate_content(

            model=GEMINI_MODELS[0],

            contents=f"""
You are India's best agriculture expert.

IMPORTANT LANGUAGE RULE:
{language_instruction}

Farmer Question:
{question}

Give practical and simple farming advice.

Include:

Problem:
Possible Reason:
Solution:
Medicine:
Organic Solution:
Prevention:

Do not change the requested language.
Do not mix languages unnecessarily.

"""
        )

        return {

            "status": True,

            "answer": response.text

        }


    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }
    

# ==========================
# MANDI RATES
# ==========================

@app.get("/mandi/{crop}/{state}")
def get_mandi(crop: str, state: str):

    try:

        cursor.execute(
            """
            SELECT
                id,
                crop,
                location,
                min_price,
                max_price,
                avg_price,
                date
            FROM mandi
            WHERE LOWER(crop) = LOWER(?)
            AND LOWER(location) = LOWER(?)
            ORDER BY id DESC
            """,
            (
                crop,
                state
            )
        )

        rows = cursor.fetchall()


        records = []


        for row in rows:

            records.append({

                "id": row[0],

                "Commodity": row[1],

                "State": row[2],

                "Min_Price": row[3],

                "Max_Price": row[4],

                "Modal_Price": row[5],

                "Date": row[6]

            })


        return {

            "status": True,

            "crop": crop,

            "state": state,

            "records": records

        }


    except Exception as e:

        return {

            "status": False,

            "message": str(e)

        }

@app.get("/mandi-all/{state}")
def get_all_mandi(state: str):

    try:

        cursor.execute(
            """
            SELECT
                id,
                crop,
                location,
                min_price,
                max_price,
                avg_price,
                date
            FROM mandi
            WHERE LOWER(location) = LOWER(?)
            ORDER BY id DESC
            """,
            (state,)
        )

        rows = cursor.fetchall()

        records = []

        for row in rows:

            records.append({

                "id": row[0],
                "Commodity": row[1],
                "State": row[2],
                "Min_Price": row[3],
                "Max_Price": row[4],
                "Modal_Price": row[5],
                "Date": row[6]

            })

        return {
            "status": True,
            "state": state,
            "records": records
        }

    except Exception as e:

        return {
            "status": False,
            "message": str(e)
        }


@app.get("/schemes/{state}")
def get_schemes(state: str):

    try:

        # ==========================
        # EXISTING GOVERNMENT SCHEMES
        # ==========================

        schemes = {

            "Maharashtra": [

                {
                    "name":
                        "🌾 PM Kisan Samman Nidhi",

                    "description":
                        "Eligible land holding farmer families receive financial support from Government of India.",

                    "benefit":
                        "₹6000 per year (3 installments)",

                    "eligibility":
                        "Land holding farmers",

                    "apply":
                        "https://pmkisan.gov.in/"
                },


                {
                    "name":
                        "🌱 MahaDBT Farmer Scheme",

                    "description":
                        "Agriculture department subsidy schemes for seeds, machinery, irrigation and farming equipment.",

                    "benefit":
                        "Agriculture equipment and input subsidy",

                    "eligibility":
                        "Maharashtra farmers",

                    "apply":
                        "https://mahadbt.maharashtra.gov.in/"
                },


                {
                    "name":
                        "💧 Dr. Babasaheb Ambedkar Krushi Swavalamban Yojana",

                    "description":
                        "Support scheme for agricultural development activities.",

                    "benefit":
                        "Agriculture improvement assistance",

                    "eligibility":
                        "Eligible Maharashtra farmers",

                    "apply":
                        "https://mahadbt.maharashtra.gov.in/"
                }

            ]

        }


        # ==========================
        # ADMIN ADDED SCHEMES
        # ==========================

        admin_schemes = []


        try:

            cursor.execute("""
                SELECT
                    name,
                    description,
                    benefit,
                    eligibility,
                    apply_url
                FROM admin_schemes
                WHERE LOWER(TRIM(state))
                      = LOWER(TRIM(?))
                ORDER BY id DESC
            """, (state,))


            rows = cursor.fetchall()


            for row in rows:

                admin_schemes.append({

                    "name":
                        row[0],

                    "description":
                        row[1],

                    "benefit":
                        row[2],

                    "eligibility":
                        row[3],

                    "apply":
                        row[4]

                })


        except Exception as e:

            print(
                "ADMIN SCHEME LOAD ERROR:",
                str(e)
            )


        # ==========================
        # COMBINE EXISTING
        # + ADMIN SCHEMES
        # ==========================

        final_schemes = (

            schemes.get(
                state,
                []
            )

            +

            admin_schemes

        )


        # ==========================
        # FINAL RESPONSE
        # ==========================

        return {

            "status": True,

            "state": state,

            "total": len(final_schemes),

            "schemes": final_schemes

        }


    except Exception as e:

        print(
            "SCHEME API ERROR:",
            str(e)
        )


        return {

            "status": False,

            "message": str(e)

        }


@app.post("/admin/scheme")
def add_admin_scheme(data: SchemeModel):

    try:

        cursor.execute("""
            INSERT INTO admin_schemes(
                name,
                description,
                benefit,
                eligibility,
                state,
                apply_url,
                date
            )
            VALUES(?,?,?,?,?,?,?)
        """, (

            data.name,
            data.description,
            data.benefit,
            data.eligibility,
            data.state,
            data.apply_url,
            datetime.now().strftime("%d-%m-%Y %H:%M")

        ))

        conn.commit()

        return {

            "status": True,

            "message":
                "Government scheme added successfully"

        }

    except Exception as e:

        print(
            "ADMIN SCHEME ERROR:",
            str(e)
        )

        return {

            "status": False,

            "message": str(e)

        }

    


# ==========================
# UPDATE HOME CROP - FIRESTORE
# ==========================

@app.post("/update-home-crop")
def update_home_crop(data: HomeCropModel):

    try:

        user_ref = (
            firestore_db
            .collection("users")
            .document(str(data.user_id))
        )

        user_doc = user_ref.get()

        if not user_doc.exists:

            return {
                "status": False,
                "message": "User Not Found"
            }

        crop = data.crop.strip()

        if not crop:

            return {
                "status": False,
                "message": "Crop is required"
            }

        user_ref.update({
            "crop": crop
        })

        return {
            "status": True
        }

    except Exception as e:

        return {
            "status": False,
            "message": str(e)
        }


# ==========================
# SMART ALERTS - FIRESTORE
# ==========================

@app.get("/alerts/{user_id}")
def smart_alerts(user_id: str):

    try:

        # =====================================================
        # USER DATA - FIRESTORE
        # =====================================================

        user_doc = (
            firestore_db
            .collection("users")
            .document(str(user_id))
            .get()
        )

        if not user_doc.exists:

            return {
                "status": False,
                "message": "User not found"
            }

        user = user_doc.to_dict()

        crop = user.get("crop") or "General Crop"
        village = user.get("village") or "Unknown"

        lat = user.get("latitude")
        lon = user.get("longitude")

        language = user.get("language") or "hi"


        # =====================================================
        # LIVE WEATHER
        # USE SAME WORKING WEATHER LOGIC
        # =====================================================

        temperature = None
        humidity = None
        wind = None
        rain = None

        weather_available = False


        if lat is not None and lon is not None:

            try:

                url = (
                    "https://api.open-meteo.com/v1/forecast"
                    f"?latitude={lat}"
                    f"&longitude={lon}"
                    "&current=temperature_2m,"
                    "relative_humidity_2m,"
                    "wind_speed_10m,"
                    "weather_code"
                    "&hourly=precipitation_probability,"
                    "relative_humidity_2m,"
                    "wind_speed_10m"
                    "&daily=weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "sunrise,"
                    "sunset,"
                    "precipitation_probability_max"
                    "&forecast_days=7"
                    "&timezone=auto"
                )


                weather_response = requests.get(
                    url,
                    timeout=10
                )

                weather_response.raise_for_status()

                weather_data = weather_response.json()

                current = weather_data["current"]


                temperature = current[
                    "temperature_2m"
                ]

                humidity = current[
                    "relative_humidity_2m"
                ]

                wind = current[
                    "wind_speed_10m"
                ]


                # =================================================
                # CURRENT HOUR RAIN PROBABILITY
                # =================================================

                try:

                    current_time = current["time"]

                    current_hour = (
                        weather_data["hourly"]["time"]
                        .index(current_time)
                    )

                    rain = weather_data[
                        "hourly"
                    ][
                        "precipitation_probability"
                    ][current_hour]

                except Exception:

                    rain = 0


                weather_available = True


                print(
                    "ALERT LIVE WEATHER:",
                    temperature,
                    humidity,
                    wind,
                    rain
                )


            except Exception as e:

                print(
                    "Alert Weather Error:",
                    e
                )


        # =====================================================
        # DISEASE HISTORY - FIRESTORE
        # =====================================================

        disease_info = (
            "No previous disease scan available."
        )

        last_disease = None


        try:

            disease_docs = (
                firestore_db
                .collection("disease_history")
                .stream()
            )


            user_diseases = []

            for doc in disease_docs:

                disease_data = doc.to_dict()

                if str(
                    disease_data.get("user_id", "")
                ) == str(user_id):

                    user_diseases.append(
                        disease_data
                    )


            # Latest scan first
            user_diseases.sort(
                key=lambda x: (
                    x.get("created_at", "")
                    or x.get("date", "")
                    or ""
                ),
                reverse=True
            )


            if user_diseases:

                last_disease = user_diseases[0]


                disease_info = f"""
Previous Scan Crop: {last_disease.get("crop", "")}
Previous Disease: {last_disease.get("disease", "")}
Previous Confidence: {last_disease.get("confidence", "")}
Previous Severity: {last_disease.get("severity", "")}
Affected Part: {last_disease.get("affected", "")}
Symptoms: {last_disease.get("symptoms", "")}
Scan Date: {last_disease.get("date", "")}
"""


        except Exception as e:

            print(
                "Disease History Error:",
                e
            )


        # =====================================================
        # LANGUAGE
        # =====================================================

        language_map = {

            "mr": "Marathi",

            "hi": "Hindi",

            "en": "English",

            "Marathi": "Marathi",

            "Hindi": "Hindi",

            "English": "English"

        }


        selected_language = language_map.get(
            language,
            "Hindi"
        )


        # =====================================================
        # WEATHER INFORMATION FOR AI
        # =====================================================

        if weather_available:

            weather_info = f"""
Temperature: {temperature} °C
Humidity: {humidity} %
Wind Speed: {wind} km/h
Rain Probability: {rain} %
"""

        else:

            weather_info = """
Live weather data unavailable.
Do NOT invent temperature,
humidity, wind or rain probability.
"""


        # =====================================================
        # DISEASE INFORMATION
        # =====================================================

        if last_disease:

            disease_instruction = f"""

Previous disease scan:

{disease_info}

IMPORTANT:

This is only a previous scan.

Do NOT say that this disease is currently
active unless current evidence supports it.

Also consider that the previous scan crop
may be different from the farmer's current crop.
"""

        else:

            disease_instruction = """

There is no previous disease scan.

Do not invent any previous disease.
"""


        # =====================================================
        # GEMINI PROMPT
        # =====================================================

        prompt = f"""

You are India's expert agriculture advisor.

Farmer location:
{village}

Current crop:
{crop}

Selected language:
{selected_language}

IMPORTANT LANGUAGE RULE:

Write ALL answer text ONLY in {selected_language}.

Do not mix Hindi, Marathi and English.

English is allowed only for necessary
agricultural technical names.

{weather_info}

{disease_instruction}

Generate today's REAL farmer alerts.

Analyze:

1. Weather
2. Current crop
3. Disease risk
4. Farming reminder
5. Today's practical tasks

IMPORTANT:

Never invent weather values.

Never invent disease history.

Never say an old disease is currently active
without evidence.

Advice must be relevant to the current crop.

If weather is unavailable, clearly say
live weather data is unavailable.

If rain probability is high:
consider irrigation, spraying and fertilizer timing.

If humidity is high:
consider fungal disease risk.

If temperature is high:
consider heat stress.

Return ONLY valid JSON.

Do NOT use markdown.

Do NOT use ```json.

Use exactly:

{{
    "weather_alert": "...",
    "crop_alert": "...",
    "disease_risk": "Low",
    "disease_message": "...",
    "reminder": "...",
    "tasks": [
        "...",
        "...",
        "..."
    ]
}}

disease_risk must be:

Low
Medium
High

All descriptive text must be in {selected_language}.

"""


        # =====================================================
        # GEMINI
        # =====================================================

        response = None
        last_error = ""


        for model_name in GEMINI_MODELS:

            try:

                print(
                    "Trying Alert Model:",
                    model_name
                )


                response = client.models.generate_content(

                    model=model_name,

                    contents=prompt

                )


                print(
                    "Alert Model Success:",
                    model_name
                )

                break


            except Exception as e:

                print(
                    "Alert Model Failed:",
                    model_name,
                    e
                )

                last_error = str(e)


        if response is None:

            return {

                "status": False,

                "message": last_error

            }


        # =====================================================
        # CLEAN AI RESPONSE
        # =====================================================

        text = response.text.strip()


        print(
            "GEMINI ALERT RESPONSE:",
            text
        )


        if text.startswith("```json"):

            text = text[
                7:
            ].strip()


        if text.startswith("```"):

            text = text[
                3:
            ].strip()


        if text.endswith("```"):

            text = text[
                :-3
            ].strip()


        # =====================================================
        # JSON
        # =====================================================

        try:

            result = json.loads(text)


        except Exception as e:

            print(
                "Alert JSON Error:",
                e
            )

            return {

                "status": False,

                "message":
                "AI returned invalid alert data",

                "raw_response":
                text

            }


        # =====================================================
        # TASKS
        # =====================================================

        tasks = result.get(
            "tasks",
            []
        )


        if not isinstance(tasks, list):

            tasks = []


        tasks = [
            str(x).strip()
            for x in tasks
            if str(x).strip()
        ]


        tasks = tasks[:3]


        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {

            "status": True,

            "location": village,

            "crop": crop,

            "language": language,


            "weather_data": {

                "available":
                weather_available,

                "temperature":
                temperature,

                "humidity":
                humidity,

                "wind":
                wind,

                "rain":
                rain

            },


            "weather_alert":
            result.get(
                "weather_alert",
                "--"
            ),


            "crop_alert":
            result.get(
                "crop_alert",
                "--"
            ),


            "disease_alert": {

                "risk":
                result.get(
                    "disease_risk",
                    "Low"
                ),

                "message":
                result.get(
                    "disease_message",
                    "--"
                )

            },


            "reminder":
            result.get(
                "reminder",
                "--"
            ),


            "tasks":
            tasks

        }


    except Exception as e:

        print(
            "SMART ALERT ERROR:",
            e
        )

        return {

            "status": False,

            "message":
            str(e)

        }


# ============================================================
# RAIN ALERT - FIRESTORE
# ============================================================

@app.get("/rain-alert/{user_id}")
def rain_alert(user_id: str):

    try:

        # =====================================================
        # USER DATA - FIRESTORE
        # =====================================================

        user_ref = (
            firestore_db
            .collection("users")
            .document(str(user_id))
        )

        user_doc = user_ref.get()

        if not user_doc.exists:

            return {
                "status": False,
                "message": "User not found"
            }

        user = user_doc.to_dict()

        crop = user.get("crop") or "General Crop"
        village = user.get("village") or "Unknown"

        latitude = user.get("latitude")
        longitude = user.get("longitude")

        language = user.get("language") or "hi"


        # =====================================================
        # LANGUAGE
        # =====================================================

        language_map = {

            "mr": "Marathi",
            "hi": "Hindi",
            "en": "English",

            "Marathi": "Marathi",
            "Hindi": "Hindi",
            "English": "English"

        }

        selected_language = language_map.get(
            language,
            "Hindi"
        )


        # =====================================================
        # WEATHER
        # =====================================================

        temperature = None
        humidity = None
        rain = None
        weather_name = "Unknown"

        weather_available = False


        if latitude is not None and longitude is not None:

            try:

                url = (
                    "https://api.open-meteo.com/v1/forecast"
                    f"?latitude={latitude}"
                    f"&longitude={longitude}"
                    "&current=temperature_2m,"
                    "relative_humidity_2m,"
                    "wind_speed_10m,"
                    "weather_code"
                    "&hourly=precipitation_probability"
                    "&timezone=auto"
                )


                weather_response = requests.get(
                    url,
                    timeout=10
                )

                weather_response.raise_for_status()

                weather = weather_response.json()

                current = weather["current"]


                temperature = current[
                    "temperature_2m"
                ]

                humidity = current[
                    "relative_humidity_2m"
                ]


                # =================================================
                # WEATHER CODE
                # =================================================

                code = current[
                    "weather_code"
                ]


                weather_map = {

                    0: "Clear Sky",
                    1: "Mainly Clear",
                    2: "Partly Cloudy",
                    3: "Cloudy",

                    45: "Fog",
                    48: "Fog",

                    51: "Light Drizzle",
                    53: "Drizzle",
                    55: "Heavy Drizzle",

                    61: "Light Rain",
                    63: "Rain",
                    65: "Heavy Rain",

                    71: "Light Snow",
                    73: "Snow",
                    75: "Heavy Snow",

                    80: "Rain Showers",
                    81: "Heavy Rain Showers",
                    82: "Violent Rain",

                    95: "Thunderstorm",
                    96: "Thunderstorm with Hail",
                    99: "Thunderstorm with Heavy Hail"

                }


                weather_name = weather_map.get(
                    code,
                    "Unknown"
                )


                # =================================================
                # CURRENT RAIN PROBABILITY
                # =================================================

                try:

                    current_time = current["time"]

                    index = (
                        weather["hourly"]["time"]
                        .index(current_time)
                    )

                    rain = weather[
                        "hourly"
                    ][
                        "precipitation_probability"
                    ][index]

                except Exception:

                    rain = 0


                weather_available = True


                print(
                    "RAIN ALERT LIVE WEATHER:",
                    temperature,
                    humidity,
                    rain,
                    weather_name
                )


            except Exception as e:

                print(
                    "Rain Alert Weather Error:",
                    e
                )


        # =====================================================
        # WEATHER DATA FOR AI
        # =====================================================

        if weather_available:

            weather_info = f"""
Temperature: {temperature} °C
Humidity: {humidity} %
Rain Probability: {rain} %
Weather: {weather_name}
"""

        else:

            weather_info = """
Live weather data unavailable.

Do not invent weather values.
"""


        # =====================================================
        # GEMINI PROMPT
        # =====================================================

        prompt = f"""

You are India's expert agriculture advisor.

Farmer Location:
{village}

Current Crop:
{crop}

Selected Language:
{selected_language}

Live Weather:

{weather_info}

Create a REAL rain-related farming alert.

IMPORTANT LANGUAGE RULE:

Write the entire answer ONLY in {selected_language}.

Do not mix Hindi, Marathi and English.

Do not invent weather values.

If live weather is unavailable, clearly mention
that live weather data is unavailable.

Consider:

- rain probability
- current weather
- current crop
- possible crop risk
- spraying timing
- fertilizer timing
- irrigation requirement

Give practical advice for the farmer.

Reply ONLY in this exact format:

Rain Status: ...
Crop Risk: ...
Advice: ...
Action: ...

Keep each answer to one short sentence.

"""


        # =====================================================
        # GEMINI
        # =====================================================

        response = None
        last_error = ""


        for model_name in GEMINI_MODELS:

            try:

                print(
                    "Trying Rain Alert Model:",
                    model_name
                )


                response = client.models.generate_content(

                    model=model_name,

                    contents=prompt

                )


                print(
                    "Rain Alert Model Success:",
                    model_name
                )

                break


            except Exception as e:

                print(
                    "Rain Alert Model Failed:",
                    model_name,
                    e
                )

                last_error = str(e)


        if response is None:

            return {

                "status": False,

                "message": last_error

            }


        # =====================================================
        # PARSE AI RESPONSE
        # =====================================================

        text = response.text.strip()


        print(
            "RAIN AI RESPONSE:"
        )

        print(text)


        rain_status = "--"
        crop_risk = "--"
        advice = "--"
        action = "--"


        for line in text.split("\n"):

            line = line.replace(
                "*",
                ""
            ).strip()


            if line.startswith(
                "Rain Status:"
            ):

                rain_status = (
                    line.replace(
                        "Rain Status:",
                        "",
                        1
                    ).strip()
                )


            elif line.startswith(
                "Crop Risk:"
            ):

                crop_risk = (
                    line.replace(
                        "Crop Risk:",
                        "",
                        1
                    ).strip()
                )


            elif line.startswith(
                "Advice:"
            ):

                advice = (
                    line.replace(
                        "Advice:",
                        "",
                        1
                    ).strip()
                )


            elif line.startswith(
                "Action:"
            ):

                action = (
                    line.replace(
                        "Action:",
                        "",
                        1
                    ).strip()
                )


        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {

            "status": True,

            "location": village,

            "crop": crop,

            "language": language,


            "weather_data": {

                "available":
                weather_available,

                "temperature":
                temperature,

                "humidity":
                humidity,

                "rain_probability":
                rain

            },


            "weather":
            weather_name,


            "rain_status":
            rain_status,

            "crop_risk":
            crop_risk,

            "advice":
            advice,

            "action":
            action

        }


    except Exception as e:

        print(
            "RAIN ALERT ERROR:",
            e
        )

        return {

            "status": False,

            "message": str(e)

        }

    

def classify_news(title, description):

    prompt = f"""

You are an agriculture news classifier.

News Title:
{title}

News Description:
{description}


Choose only one category:

Weather
Crop
Market
Disease
Government


Reply only category name.

"""


    try:

        response = client.models.generate_content(

            model="models/gemini-3.1-flash-lite",

            contents=prompt

        )


        category = response.text.strip()


        allowed = [

            "Weather",
            "Crop",
            "Market",
            "Disease",
            "Government"

        ]


        if category in allowed:

            return category


        return "Crop"



    except Exception as e:


        print(
            "Category AI Error:",
            e
        )


        return "Crop"



def get_farmer_meaning(title, description, language):

    language_names = {
        "hi": "Hindi",
        "mr": "Marathi",
        "en": "English",
        "gu": "Gujarati",
        "pa": "Punjabi",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "ml": "Malayalam"
    }

    selected_language = language_names.get(
        language,
        "Hindi"
    )

    prompt = f"""
You are an expert Indian agriculture advisor.

News Title:
{title}

News Details:
{description}

Explain what this news means for an Indian farmer.

Reply ONLY in {selected_language}.

Rules:
- Give exactly 2 short sentences.
- Use simple language that farmers can understand.
- Do not use unnecessary English.
- Do not invent facts.
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODELS[0],
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:

        print("Farmer Meaning AI Error:", e)

        return "या बातमीचा शेतीवरील परिणाम तपासा."


@app.get("/agri-news/{user_id}")
def agri_news(user_id: int):

    try:

        # ==========================
        # USER DATA
        # ==========================

        cursor.execute("""
            SELECT village, language
            FROM users
            WHERE id=?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:

            return {
                "status": False,
                "message": "User not found"
            }

        village = user[0]

        language = user[1] or "hi"


        # ==========================
        # FINAL NEWS LIST
        # ==========================

        news = []


        # ==========================
        # ADMIN NEWS
        # ==========================

        admin_news_list = []

        try:

            cursor.execute("""
                SELECT
                    id,
                    title,
                    description,
                    date
                FROM admin_news
                ORDER BY id DESC
                LIMIT 20
            """)

            admin_rows = cursor.fetchall()


            for row in admin_rows:

                admin_title = row[1]

                admin_description = row[2]

                admin_date = row[3]


                # ==========================
                # AI CATEGORY
                # ==========================

                category = classify_news(
                    admin_title,
                    admin_description
                )


                # ==========================
                # FARMER MEANING
                # ==========================

                farmer_meaning = get_farmer_meaning(
                    admin_title,
                    admin_description,
                    language
                )


                # ==========================
                # ICON
                # ==========================

                icon = "🌱"

                if category == "Weather":

                    icon = "🌧️"

                elif category == "Market":

                    icon = "💰"

                elif category == "Disease":

                    icon = "🐛"

                elif category == "Government":

                    icon = "🏛️"


                # ==========================
                # ADD ADMIN NEWS
                # ==========================

                admin_news_list.append({

                    "title":
                        admin_title,

                    "description":
                        admin_description,

                    "category":
                        category,

                    "icon":
                        icon,

                    "farmer_meaning":
                        farmer_meaning,

                    "source":
                        "Kisan AI",

                    "date":
                        admin_date

                })


        except Exception as e:

            print(
                "ADMIN NEWS ERROR:",
                e
            )


        # ==========================
        # ADD ADMIN NEWS FIRST
        # ==========================

        news.extend(
            admin_news_list
        )


        # ==========================
        # NEWS API
        # ==========================

        url = (
            "https://newsdata.io/api/1/news?"
            "apikey=pub_28ba34b1a77041cfae4e3f43b21bbf3b"
            "&q=agriculture OR farmer OR crop OR mandi OR farming"
            "&country=in"
            "&language=en"
        )


        response = requests.get(
            url,
            timeout=10
        )


        response.raise_for_status()


        data = response.json()


        print(
            "NEWS API RESPONSE"
        )

        print(data)


        # ==========================
        # API ERROR
        # ==========================

        if "results" not in data:

            print(
                "NEWS API ERROR:",
                data
            )

            # Admin news available ho to
            # API fail hone par bhi return karo

            return {

                "status": True,

                "location": village,

                "language": language,

                "total": len(news),

                "news": news

            }


        results = data.get(
            "results",
            []
        )


        if not isinstance(
            results,
            list
        ):

            results = []


        # ==========================
        # PROCESS LIVE API NEWS
        # ==========================

        for item in results[:10]:

            title = item.get(
                "title"
            ) or "Agriculture News"


            description = item.get(
                "description"
            ) or "Latest farming update"


            # ==========================
            # AI CATEGORY
            # ==========================

            category = classify_news(
                title,
                description
            )


            # ==========================
            # FARMER MEANING
            # ==========================

            farmer_meaning = get_farmer_meaning(
                title,
                description,
                language
            )


            # ==========================
            # ICON
            # ==========================

            icon = "🌱"


            if category == "Weather":

                icon = "🌧️"

            elif category == "Market":

                icon = "💰"

            elif category == "Disease":

                icon = "🐛"

            elif category == "Government":

                icon = "🏛️"


            # ==========================
            # ADD LIVE NEWS
            # ==========================

            news.append({

                "title":
                    title,

                "description":
                    description,

                "category":
                    category,

                "icon":
                    icon,

                "farmer_meaning":
                    farmer_meaning,

                "source":
                    item.get(
                        "source_id",
                        "News"
                    ),

                "date":
                    item.get(
                        "pubDate",
                        ""
                    )

            })


        # ==========================
        # FINAL RESPONSE
        # ==========================

        return {

            "status": True,

            "location": village,

            "language": language,

            "total": len(news),

            "news": news

        }


    except Exception as e:

        print(
            "AGRI NEWS ERROR:",
            e
        )


        # ==========================
        # FINAL ERROR
        # ==========================

        return {

            "status": False,

            "message": str(e)

        }

    
@app.post("/admin/news")
def add_admin_news(data: AdminNewsModel):

    try:

        title = data.title.strip()
        description = data.description.strip()

        if not title or not description:

            return {
                "status": False,
                "message": "Title and description required"
            }


        cursor.execute(
            """
            INSERT INTO admin_news(
                title,
                description,
                date
            )
            VALUES (?, ?, ?)
            """,
            (
                title,
                description,
                datetime.now().strftime("%Y-%m-%d")
            )
        )

        conn.commit()


        return {
            "status": True,
            "message": "News added successfully"
        }


    except Exception as e:

        conn.rollback()

        return {
            "status": False,
            "message": str(e)
        }
    

# ==========================
# Farmers API - FIRESTORE
# ==========================

@app.get("/farmers")
def get_farmers():

    farmers = []

    users = firestore_db.collection("users").stream()

    for doc in users:

        f = doc.to_dict()

        farmers.append({

            "id": f.get("id", doc.id),

            "name": f.get("name", ""),

            "crop": f.get("crop", ""),

            "village": f.get("village", "")

        })

    return {

        "status": True,

        "farmers": farmers

    }


@app.post("/send-chat")
def send_chat(data: dict):

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()


    # Purane text chat ke liye default
    message_type = data.get(
        "message_type",
        "text"
    )


    message = data.get(
        "message",
        ""
    )


    image = data.get(
        "image",
        None
    )


    latitude = data.get(
        "latitude",
        None
    )


    longitude = data.get(
        "longitude",
        None
    )


    cursor.execute("""
    INSERT INTO messages
    (
        sender_id,
        receiver_id,
        message,
        time,
        message_type,
        image,
        latitude,
        longitude
    )
    VALUES(?,?,?,?,?,?,?,?)
    """,
    (
        data["sender_id"],
        data["receiver_id"],
        message,
        datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        ),
        message_type,
        image,
        latitude,
        longitude
    ))


    conn.commit()
    conn.close()


    return {
        "status": True,
        "message": "Sent"
    }



@app.get("/chat/{user1}/{user2}")
def get_chat(
    user1: int,
    user2: int
):

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()


    cursor.execute("""
    SELECT
        sender_id,
        message,
        time,
        message_type,
        image,
        latitude,
        longitude

    FROM messages

    WHERE
    (
        sender_id=?
        AND receiver_id=?
    )

    OR

    (
        sender_id=?
        AND receiver_id=?
    )

    ORDER BY id
    """,
    (
        user1,
        user2,
        user2,
        user1
    ))


    chats = cursor.fetchall()

    conn.close()


    data = []


    for c in chats:

        data.append({

            "sender": c[0],

            "message": c[1],

            "time": c[2],

            "message_type":
                c[3] or "text",

            "image":
                c[4],

            "latitude":
                c[5],

            "longitude":
                c[6]

        })


    return {

        "status": True,

        "chat": data

    }


# ==========================
# CHAT IMAGE UPLOAD
# ==========================

CHAT_UPLOAD_DIR = "uploads/chat"

os.makedirs(
    CHAT_UPLOAD_DIR,
    exist_ok=True
)


@app.post("/upload-chat-image")
async def upload_chat_image(
    file: UploadFile = File(...)
):

    try:

        if not file.content_type:

            return {
                "status": False,
                "message": "Invalid file"
            }


        if not file.content_type.startswith(
            "image/"
        ):

            return {
                "status": False,
                "message": "Only images are allowed"
            }


        extension = os.path.splitext(
            file.filename
        )[1]


        if not extension:

            extension = ".jpg"


        filename = (
            str(uuid.uuid4())
            + extension
        )


        file_path = os.path.join(
            CHAT_UPLOAD_DIR,
            filename
        )


        with open(
            file_path,
            "wb"
        ) as buffer:

            buffer.write(
                await file.read()
            )


        return {

            "status": True,

            "image_url":
                "/uploads/chat/" + filename

        }


    except Exception as e:

        print(
            "CHAT IMAGE ERROR:",
            str(e)
        )

        return {

            "status": False,

            "message": str(e)

        }

    

# ==========================
# RAZORPAY PLAN IDS
# ==========================

RAZORPAY_PLANS = {

    # ==========================
    # CURRENT FIRST PAYMENT PLANS
    # ==========================

    "basic_monthly":
        "plan_TQTNYbVUVJZU8x",

    "advanced_monthly":
        "plan_TQTXJ6JYggjOB9",


    # ==========================
    # NEW RECURRING PLANS
    # NEXT MONTH ONWARDS
    # ==========================

    "basic_recurring":
        "plan_TUgYTYlfaMuTau",

    "advanced_recurring":
        "plan_TUgZSzgA538Fiw",


    # ==========================
    # 6 MONTH PLANS
    # ==========================

    "basic_6months":
        "plan_TQTQz6LK1C5okB",

    "advanced_6months":
        "plan_TQTYoLVEnhRlVD",


    # ==========================
    # YEARLY PLANS
    # ==========================

    "basic_yearly":
        "plan_TQTVr8lsra1RGb",

    "advanced_yearly":
        "plan_TQTadndbEu7Uwm"

}

# ==========================
# CREATE SUBSCRIPTION
# ==========================

@app.post("/create-subscription")
def create_subscription(data: dict):

    try:

        user_id = data.get("user_id")
        plan_key = data.get("plan")


        if not user_id:

            return {
                "status": False,
                "message": "User ID required"
            }


        # ==========================
        # MONTHLY SPECIAL FLOW
        # FIRST PAYMENT:
        # Basic = ₹9
        # Advanced = ₹17
        #
        # NEXT MONTH:
        # Basic = ₹150/month
        # Advanced = ₹200/month
        # ==========================

        if plan_key == "basic_monthly":

            plan_id = RAZORPAY_PLANS[
                "basic_recurring"
            ]

            first_payment = 900

            first_payment_name = (
                "Basic First Month"
            )


        elif plan_key == "advanced_monthly":

            plan_id = RAZORPAY_PLANS[
                "advanced_recurring"
            ]

            first_payment = 1700

            first_payment_name = (
                "Advanced First Month"
            )


        # ==========================
        # EXISTING 6 MONTH / YEARLY
        # ==========================

        elif plan_key in [

            "basic_6months",
            "basic_yearly",

            "advanced_6months",
            "advanced_yearly"

        ]:

            plan_id = RAZORPAY_PLANS[
                plan_key
            ]

            subscription = (
                razorpay_client
                .subscription
                .create({

                    "plan_id": plan_id,

                    "customer_notify": 1,

                    "total_count": 12

                })
            )


            return {

                "status": True,

                "subscription_id":
                    subscription["id"],

                "plan_id":
                    plan_id,

                "key_id":
                    RAZORPAY_KEY_ID

            }


        else:

            return {

                "status": False,

                "message":
                    "Invalid plan"

            }


        # ==========================
        # NEXT MONTH START DATE
        # ==========================

        from dateutil.relativedelta import (
            relativedelta
        )


        next_month = (
            datetime.now()
            + relativedelta(months=1)
        )


        start_at = int(
            next_month.timestamp()
        )


        # ==========================
        # CREATE RECURRING
        # SUBSCRIPTION
        # ==========================

        subscription = (
            razorpay_client
            .subscription
            .create({

                "plan_id":
                    plan_id,

                "customer_notify":
                    1,

                "total_count":
                    120,

                # ₹150 / ₹200 billing
                # starts next month
                "start_at":
                    start_at,

                # TODAY:
                # Basic ₹9
                # Advanced ₹17
                "addons": [

                    {

                        "item": {

                            "name":
                                first_payment_name,

                            "amount":
                                first_payment,

                            "currency":
                                "INR"

                        }

                    }

                ],

                "notes": {

                    "user_id":
                        str(user_id),

                    "selected_plan":
                        plan_key

                }

            })
        )


        return {

            "status": True,

            "subscription_id":
                subscription["id"],

            "plan_id":
                plan_id,

            "key_id":
                RAZORPAY_KEY_ID

        }


    except Exception as e:

        print(
            "RAZORPAY SUBSCRIPTION ERROR:",
            str(e)
        )


        return {

            "status": False,

            "message":
                str(e)

        }
    


# ==========================
# VERIFY RAZORPAY SUBSCRIPTION - FIRESTORE
# ==========================

@app.post("/verify-subscription")
def verify_subscription(data: dict):

    try:

        user_id = data.get("user_id")

        payment_id = data.get(
            "razorpay_payment_id"
        )

        subscription_id = data.get(
            "razorpay_subscription_id"
        )

        signature = data.get(
            "razorpay_signature"
        )

        plan_key = data.get(
            "plan"
        )


        # ==========================
        # VALIDATION
        # ==========================

        if not user_id:

            return {
                "status": False,
                "message": "User ID required"
            }


        if not payment_id:

            return {
                "status": False,
                "message": "Payment ID missing"
            }


        if not subscription_id:

            return {
                "status": False,
                "message": "Subscription ID missing"
            }


        if not signature:

            return {
                "status": False,
                "message": "Signature missing"
            }


        if plan_key not in RAZORPAY_PLANS:

            return {
                "status": False,
                "message": "Invalid plan"
            }


        # ==========================
        # VERIFY RAZORPAY SIGNATURE
        # ==========================

        razorpay_client.utility.verify_subscription_payment_signature({

            "razorpay_payment_id":
                payment_id,

            "razorpay_subscription_id":
                subscription_id,

            "razorpay_signature":
                signature

        })


        # ==========================
        # PLAN DURATION
        # ==========================

        if plan_key.endswith("_monthly"):

            months = 1

        elif plan_key.endswith("_6months"):

            months = 6

        elif plan_key.endswith("_yearly"):

            months = 12

        else:

            months = 1


        # ==========================
        # ADD MONTHS FUNCTION
        # ==========================

        from calendar import monthrange


        def add_months(
            base_date,
            months_to_add
        ):

            total_months = (
                base_date.year * 12
                + base_date.month
                - 1
                + months_to_add
            )

            year = (
                total_months // 12
            )

            month = (
                total_months % 12
            ) + 1

            day = min(
                base_date.day,
                monthrange(
                    year,
                    month
                )[1]
            )

            return base_date.replace(
                year=year,
                month=month,
                day=day
            )


        # ==========================
        # DATES
        # ==========================

        today = datetime.now()


        expiry_date = add_months(
            today,
            months
        )


        expiry_string = (
            expiry_date.strftime(
                "%Y-%m-%d"
            )
        )


        payment_date = (
            today.strftime(
                "%Y-%m-%d"
            )
        )


        next_payment_date = (
            expiry_string
        )


        # ==========================
        # FIRESTORE USER
        # ==========================

        user_ref = (
            firestore_db
            .collection("users")
            .document(str(user_id))
        )

        user_doc = user_ref.get()


        if not user_doc.exists:

            return {
                "status": False,
                "message": "User not found"
            }


        # ==========================
        # SAVE PREMIUM + PAYMENT DATA
        # ==========================

        user_ref.update({

            "premium_plan":
                plan_key,

            "premium_expiry":
                expiry_string,

            "razorpay_subscription_id":
                subscription_id,

            "razorpay_payment_id":
                payment_id,

            "razorpay_subscription_status":
                "authenticated",

            "last_payment_status":
                "paid",

            "last_payment_date":
                payment_date,

            "next_payment_date":
                next_payment_date

        })


        # ==========================
        # SUCCESS
        # ==========================

        return {

            "status": True,

            "message":
                "Premium activated successfully",

            "plan":
                plan_key,

            "expiry":
                expiry_string,

            "payment_id":
                payment_id,

            "subscription_id":
                subscription_id,

            "payment_status":
                "paid",

            "subscription_status":
                "authenticated",

            "last_payment_date":
                payment_date,

            "next_payment_date":
                next_payment_date

        }


    except Exception as e:

        print(
            "RAZORPAY VERIFY ERROR:",
            str(e)
        )


        return {

            "status": False,

            "message":
                str(e)

        }


# ==========================
# PREMIUM STATUS - FIRESTORE
# ==========================

@app.get("/premium-status/{user_id}")
def premium_status(user_id: str):

    try:

        # ==========================
        # GET USER FROM FIRESTORE
        # ==========================

        user_ref = (
            firestore_db
            .collection("users")
            .document(str(user_id))
        )

        user_doc = user_ref.get()


        if not user_doc.exists:

            return {

                "status": False,

                "premium": False

            }


        user = user_doc.to_dict()


        # ==========================
        # PREMIUM DATA
        # ==========================

        premium_plan = (
            user.get("premium_plan")
            or ""
        )

        premium_expiry = (
            user.get("premium_expiry")
            or ""
        )

        subscription_id = (
            user.get(
                "razorpay_subscription_id"
            )
            or ""
        )


        # ==========================
        # CHECK EXPIRY
        # ==========================

        premium_active = False


        if premium_plan and premium_expiry:

            try:

                expiry_date = datetime.strptime(
                    premium_expiry,
                    "%Y-%m-%d"
                )


                if datetime.now() < expiry_date:

                    premium_active = True


            except Exception:

                premium_active = False


        # ==========================
        # RESPONSE
        # ==========================

        return {

            "status": True,

            "premium":
                premium_active,

            "plan":
                premium_plan,

            "expiry":
                premium_expiry,

            "subscription_id":
                subscription_id

        }


    except Exception as e:

        print(
            "PREMIUM STATUS ERROR:",
            str(e)
        )


        return {

            "status": False,

            "premium": False,

            "message":
                str(e)

        }

    


# ==========================
# RECOVER PENDING PREMIUM PAYMENT - FIRESTORE
# ==========================

@app.post("/recover-premium-payment")
def recover_premium_payment(data: dict):

    try:

        user_id = data.get(
            "user_id"
        )

        subscription_id = data.get(
            "subscription_id"
        )

        plan_key = data.get(
            "plan"
        )


        # ==========================
        # VALIDATION
        # ==========================

        if not user_id:

            return {

                "status": False,

                "premium": False,

                "message":
                    "User ID required"

            }


        if not subscription_id:

            return {

                "status": False,

                "premium": False,

                "message":
                    "Subscription ID required"

            }


        if plan_key not in RAZORPAY_PLANS:

            return {

                "status": False,

                "premium": False,

                "message":
                    "Invalid plan"

            }


        # ==========================
        # FETCH SUBSCRIPTION
        # FROM RAZORPAY
        # ==========================

        subscription = (

            razorpay_client
            .subscription
            .fetch(
                subscription_id
            )

        )


        subscription_status = (
            subscription.get(
                "status"
            )
        )


        print(
            "RECOVERY SUBSCRIPTION STATUS:",
            subscription_status
        )


        # ==========================
        # PAYMENT CONFIRMED
        # ==========================

        valid_statuses = [

            "authenticated",

            "active"

        ]


        if subscription_status not in valid_statuses:

            return {

                "status": True,

                "premium": False,

                "subscription_status":
                    subscription_status,

                "message":
                    "Payment is not confirmed yet"

            }


        # ==========================
        # PLAN DURATION
        # ==========================

        if plan_key.endswith(
            "_monthly"
        ):

            months = 1


        elif plan_key.endswith(
            "_6months"
        ):

            months = 6


        elif plan_key.endswith(
            "_yearly"
        ):

            months = 12


        else:

            months = 1


        # ==========================
        # CALCULATE EXPIRY
        # ==========================

        from calendar import monthrange


        def add_months(
            base_date,
            months_to_add
        ):

            total_months = (

                base_date.year * 12

                + base_date.month

                - 1

                + months_to_add

            )


            year = (
                total_months // 12
            )


            month = (
                total_months % 12
            ) + 1


            day = min(

                base_date.day,

                monthrange(
                    year,
                    month
                )[1]

            )


            return base_date.replace(

                year=year,

                month=month,

                day=day

            )


        expiry_date = add_months(

            datetime.now(),

            months

        )


        expiry_string = (

            expiry_date.strftime(
                "%Y-%m-%d"
            )

        )


        # ==========================
        # FIRESTORE USER
        # ==========================

        user_ref = (

            firestore_db
            .collection("users")
            .document(str(user_id))

        )


        user_doc = user_ref.get()


        if not user_doc.exists:

            return {

                "status": False,

                "premium": False,

                "message":
                    "User not found"

            }


        # ==========================
        # SAVE PREMIUM
        # ==========================

        user_ref.update({

            "premium_plan":
                plan_key,

            "premium_expiry":
                expiry_string,

            "razorpay_subscription_id":
                subscription_id,

            "razorpay_subscription_status":
                subscription_status,

            "last_payment_status":
                "paid"

        })


        # ==========================
        # SUCCESS
        # ==========================

        return {

            "status": True,

            "premium": True,

            "message":
                "Premium recovered successfully",

            "plan":
                plan_key,

            "expiry":
                expiry_string

        }


    except Exception as e:

        print(

            "PREMIUM RECOVERY ERROR:",
            str(e)

        )


        return {

            "status": False,

            "premium": False,

            "message":
                str(e)

        }



# ==========================
# RAZORPAY WEBHOOK - FIRESTORE
# ==========================

@app.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):

    try:

        # ==========================
        # READ RAW BODY
        # ==========================

        body = await request.body()

        webhook_signature = request.headers.get(
            "X-Razorpay-Signature"
        )

        event_id = request.headers.get(
            "x-razorpay-event-id"
        )

        webhook_secret = os.getenv(
            "RAZORPAY_WEBHOOK_SECRET"
        )


        # ==========================
        # BASIC VALIDATION
        # ==========================

        if not webhook_signature:

            return {
                "status": False,
                "message": "Webhook signature missing"
            }


        if not webhook_secret:

            return {
                "status": False,
                "message": "Webhook secret not configured"
            }


        # ==========================
        # VERIFY SIGNATURE
        # ==========================

        expected_signature = hmac.new(

            webhook_secret.encode(),

            body,

            hashlib.sha256

        ).hexdigest()


        if not hmac.compare_digest(
            expected_signature,
            webhook_signature
        ):

            return {
                "status": False,
                "message": "Invalid webhook signature"
            }


        # ==========================
        # READ PAYLOAD
        # ==========================

        payload = json.loads(body)

        event = payload.get("event")


        print(
            "RAZORPAY WEBHOOK EVENT:",
            event
        )

        print(
            "RAZORPAY EVENT ID:",
            event_id
        )


        # ==========================
        # ONLY HANDLE SUBSCRIPTION EVENTS
        # ==========================

        if event not in [

            "subscription.pending",

            "subscription.charged",

            "subscription.halted"

        ]:

            return {

                "status": True,

                "message": "Event ignored"

            }


        # ==========================
        # SUBSCRIPTION ENTITY
        # ==========================

        subscription_entity = (

            payload
            .get("payload", {})
            .get("subscription", {})
            .get("entity", {})

        )


        subscription_id = (

            subscription_entity.get("id")
            or ""

        )


        notes = (

            subscription_entity.get(
                "notes",
                {}
            )

        )


        # ==========================
        # USER + PLAN
        # ==========================

        user_id = notes.get(
            "user_id"
        )

        plan_key = notes.get(
            "selected_plan"
        )


        print(
            "WEBHOOK SUBSCRIPTION:",
            subscription_id
        )

        print(
            "WEBHOOK USER:",
            user_id
        )

        print(
            "WEBHOOK PLAN:",
            plan_key
        )


        # ==========================
        # VALIDATION
        # ==========================

        if not user_id:

            return {

                "status": True,

                "message": "User ID missing"

            }


        if not plan_key:

            return {

                "status": True,

                "message": "Plan missing"

            }


        # ==========================
        # FIRESTORE USER
        # ==========================

        user_ref = (
            firestore_db
            .collection("users")
            .document(str(user_id))
        )

        user_doc = user_ref.get()


        if not user_doc.exists:

            return {

                "status": False,

                "message": "User not found"

            }


        # ==========================
        # DUPLICATE EVENT PROTECTION
        # ==========================

        if event_id:

            event_ref = (
                firestore_db
                .collection(
                    "razorpay_webhook_events"
                )
                .document(str(event_id))
            )

            event_doc = event_ref.get()


            if event_doc.exists:

                print(
                    "DUPLICATE WEBHOOK IGNORED:",
                    event_id
                )

                return {

                    "status": True,

                    "message":
                        "Duplicate event ignored"

                }


        # ==========================
        # SUBSCRIPTION PENDING
        # ==========================

        if event == "subscription.pending":

            user_ref.update({

                "razorpay_subscription_id":
                    subscription_id,

                "razorpay_subscription_status":
                    "pending",

                "last_payment_status":
                    "pending"

            })


            # Save event AFTER successful user update

            if event_id:

                event_ref.set({

                    "event": event,

                    "created_at":
                        datetime.now().isoformat()

                })


            print(
                "PREMIUM PAYMENT PENDING:",
                user_id
            )


            return {

                "status": True,

                "message":
                    "Subscription payment pending"

            }


        # ==========================
        # SUBSCRIPTION HALTED
        # ==========================

        if event == "subscription.halted":

            user_ref.update({

                "razorpay_subscription_id":
                    subscription_id,

                "razorpay_subscription_status":
                    "halted",

                "last_payment_status":
                    "failed"

            })


            # Save event AFTER successful user update

            if event_id:

                event_ref.set({

                    "event": event,

                    "created_at":
                        datetime.now().isoformat()

                })


            print(
                "PREMIUM AUTOPAY HALTED:",
                user_id
            )


            return {

                "status": True,

                "message":
                    "Subscription halted. Premium not renewed."

            }


        # ==========================
        # SUCCESSFUL RECURRING PAYMENT
        # ==========================

        if event == "subscription.charged":


            # ==========================
            # SAVE EVENT FIRST
            # ==========================

            if event_id:

                event_ref = (
                    firestore_db
                    .collection(
                        "razorpay_webhook_events"
                    )
                    .document(str(event_id))
                )


                event_doc = event_ref.get()


                if event_doc.exists:

                    print(
                        "DUPLICATE CHARGED EVENT:",
                        event_id
                    )

                    return {

                        "status": True,

                        "message":
                            "Duplicate event ignored"

                    }


                # Reserve event before premium update

                event_ref.set({

                    "event": event,

                    "created_at":
                        datetime.now().isoformat()

                })


            # ==========================
            # PLAN DURATION
            # ==========================

            if plan_key.endswith(
                "_monthly"
            ):

                months = 1

            elif plan_key.endswith(
                "_6months"
            ):

                months = 6

            elif plan_key.endswith(
                "_yearly"
            ):

                months = 12

            else:

                months = 1


            # ==========================
            # GET CURRENT PREMIUM
            # ==========================

            user_data = user_doc.to_dict()

            current_expiry_string = (
                user_data.get(
                    "premium_expiry"
                )
            )


            # ==========================
            # CURRENT DATE
            # ==========================

            today = datetime.now()


            if current_expiry_string:

                try:

                    current_expiry = (
                        datetime.strptime(

                            current_expiry_string,

                            "%Y-%m-%d"

                        )
                    )

                except Exception:

                    current_expiry = today

            else:

                current_expiry = today


            # ==========================
            # NEVER MOVE EXPIRY BACKWARD
            # ==========================

            if current_expiry > today:

                base_date = current_expiry

            else:

                base_date = today


            # ==========================
            # ADD PLAN DURATION
            # ==========================

            from calendar import monthrange


            total_months = (

                base_date.year * 12

                + base_date.month
                - 1

                + months

            )


            new_year = (
                total_months // 12
            )


            new_month = (
                total_months % 12
            ) + 1


            new_day = min(

                base_date.day,

                monthrange(

                    new_year,

                    new_month

                )[1]

            )


            new_expiry = base_date.replace(

                year=new_year,

                month=new_month,

                day=new_day

            )


            expiry_string = (

                new_expiry.strftime(
                    "%Y-%m-%d"
                )

            )


            # ==========================
            # NEXT PAYMENT DATE
            # ==========================

            next_payment_date = (
                expiry_string
            )


            # ==========================
            # UPDATE PREMIUM
            # ==========================

            user_ref.update({

                "premium_plan":
                    plan_key,

                "premium_expiry":
                    expiry_string,

                "razorpay_subscription_id":
                    subscription_id,

                "razorpay_subscription_status":
                    "charged",

                "last_payment_status":
                    "paid",

                "last_payment_date":
                    today.strftime(
                        "%Y-%m-%d"
                    ),

                "next_payment_date":
                    next_payment_date

            })


            print(
                "PREMIUM PAYMENT SUCCESS:",
                user_id
            )

            print(
                "PREMIUM RENEWED UNTIL:",
                expiry_string
            )

            print(
                "NEXT PAYMENT DATE:",
                next_payment_date
            )


            return {

                "status": True,

                "message":
                    "Premium renewed successfully",

                "expiry":
                    expiry_string,

                "next_payment_date":
                    next_payment_date

            }


        return {

            "status": True

        }


    except Exception as e:

        print(
            "RAZORPAY WEBHOOK ERROR:",
            str(e)
        )


        return {

            "status": False,

            "message":
                str(e)

        }