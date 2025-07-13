from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import ObjectId
from dotenv import load_dotenv
import os
import requests
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# MongoDB Connection
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["healthbot"]
    users = db["users"]
    chat_collection = db["chat_history"]
    chat_sessions = db["chat_sessions"]
    client.admin.command("ping")
    logger.info("✅ Successfully connected to MongoDB")
except (ConnectionFailure, OperationFailure) as e:
    logger.error(f"❌ MongoDB connection error: {e}")
    raise

# Load OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Use a working model
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct"

def create_chat_session(email, session_name=None):
    """Create a new chat session"""
    try:
        if not session_name:
            session_name = f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        session_data = {
            "email": email,
            "name": session_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message_count": 0
        }
        
        result = chat_sessions.insert_one(session_data)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        return None

def save_chat_history(email, message, role, session_id=None):
    """Save chat message to a specific session"""
    try:
        # If no session_id provided, create a new session
        if not session_id:
            session_id = create_chat_session(email)
            if not session_id:
                return None
        
        # Save the message
        message_data = {
            "session_id": session_id,
            "email": email,
            "message": message,
            "role": role,
            "timestamp": datetime.utcnow()
        }
        
        chat_collection.insert_one(message_data)
        
        # Update session metadata
        chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$inc": {"message_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return session_id
    except Exception as e:
        logger.error(f"Failed to save chat: {e}")
        return None

def get_chat_history(email, session_id=None):
    """Get chat history for a specific session or all sessions"""
    try:
        if session_id:
            # Get messages for specific session
            messages = list(chat_collection.find(
                {"session_id": session_id, "email": email},
                {"_id": 0, "message": 1, "role": 1, "timestamp": 1}
            ).sort("timestamp", 1))
        else:
            # Get messages for the most recent session
            latest_session = chat_sessions.find_one(
                {"email": email},
                sort=[("updated_at", -1)]
            )
            if latest_session:
                messages = list(chat_collection.find(
                    {"session_id": str(latest_session["_id"]), "email": email},
                    {"_id": 0, "message": 1, "role": 1, "timestamp": 1}
                ).sort("timestamp", 1))
            else:
                messages = []
        
        return [{"role": m["role"], "content": m["message"], "timestamp": m["timestamp"]} for m in messages]
    except Exception as e:
        logger.error(f"Failed to load chat history: {e}")
        return []

def get_user_sessions(email):
    """Get all chat sessions for a user"""
    try:
        sessions = list(chat_sessions.find(
            {"email": email},
            {"_id": 1, "name": 1, "created_at": 1, "updated_at": 1, "message_count": 1}
        ).sort("updated_at", -1))
        
        return [
            {
                "_id": str(session["_id"]),
                "name": session["name"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "message_count": session["message_count"]
            }
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        return []

def delete_chat_session(session_id, email):
    """Delete a specific chat session and all its messages"""
    try:
        # Delete all messages in the session
        chat_collection.delete_many({"session_id": session_id, "email": email})
        
        # Delete the session
        chat_sessions.delete_one({"_id": ObjectId(session_id), "email": email})
        
        return True
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}")
        return False

def ask_openrouter(user_input, language="en"):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # "HTTP-Referer": "http://localhost:5000",
        # "X-Title": "HealthBot"
    }
    # Language prompt
    lang_prompt = {
        "en": "You are a helpful health assistant. Reply in English. Give simple and safe advice for general health questions.",
        "hi": "You are a helpful health assistant. Reply in Hindi. Give simple and safe advice for general health questions.",
        "te": "You are a helpful health assistant. Reply in Telugu. Give simple and safe advice for general health questions."
    }
    system_prompt = lang_prompt.get(language, lang_prompt["en"])
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        else:
            return "Bot Error: No valid response from model."

    except Exception as e:
        return f"Bot Error: {str(e)}"

@app.route("/")
def home():
    return redirect(url_for("signup"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required", "error")
            return render_template("signup.html")

        if users.find_one({"email": email}):
            flash("Email already registered. Please log in.", "info")
            return redirect(url_for("login"))

        try:
            hashed_password = generate_password_hash(password)
            users.insert_one({
                "email": email,
                "password": hashed_password,
                "created_at": datetime.utcnow()
            })
            flash("Registration successful!", "success")
            session["email"] = email
            return redirect(url_for("chat"))
        except Exception as e:
            logger.error(f"Signup error: {e}")
            flash("Something went wrong during signup.", "error")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        try:
            user = users.find_one({"email": email})
            if user and check_password_hash(user["password"], password):
                session["email"] = email
                flash("Login successful!", "success")
                return redirect(url_for("chat"))
            else:
                flash("Invalid email or password", "error")
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash("Login failed. Please try again.", "error")

    return render_template("login.html")
@app.route("/new_chat")
def new_chat():
    if "email" not in session:
        return redirect(url_for("login"))
    
    # Create a new chat session
    session_id = create_chat_session(session["email"])
    if session_id:
        # Store the current session ID in Flask session
        session["current_session_id"] = session_id
        flash("New chat session created!", "success")
    else:
        flash("Failed to create new chat session.", "error")
    
    return redirect(url_for("chat"))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    from flask import jsonify
    if "email" not in session:
        if request.is_json:
            return jsonify({"status": "error", "message": "Not logged in"}), 401
        return redirect(url_for("login"))

    email = session["email"]

    if request.method == "POST":
        # Support both form and JSON
        if request.is_json:
            data = request.get_json()
            user_message = data.get("message", "").strip()
            language = data.get("language", "en")
        else:
            user_message = request.form.get("message", "").strip()
            language = request.form.get("language", "en")
        
        if user_message:
            # Get current session ID or create new one
            current_session_id = session.get("current_session_id")
            if not current_session_id:
                current_session_id = create_chat_session(email)
                session["current_session_id"] = current_session_id
            
            # Save user message
            save_chat_history(email, user_message, "user", current_session_id)
            
            # Get bot reply
            bot_reply = ask_openrouter(user_message, language=language)
            
            # Save bot reply
            save_chat_history(email, bot_reply, "bot", current_session_id)
            
            # Return JSON for AJAX
            return jsonify({
                "status": "success",
                "messages": [
                    {"role": "user", "content": user_message},
                    {"role": "bot", "content": bot_reply}
                ]
            })
        else:
            return jsonify({"status": "error", "message": "Empty message"})

    # Get current session ID
    current_session_id = session.get("current_session_id")
    
    # Get all user sessions
    sessions = get_user_sessions(email)
    
    # If no sessions exist, create one
    if not sessions:
        current_session_id = create_chat_session(email)
        session["current_session_id"] = current_session_id
        sessions = get_user_sessions(email)
    
    # Get messages for current session
    messages = get_chat_history(email, current_session_id)
    
    return render_template("chat.html", messages=messages, sessions=sessions, current_chat_id=current_session_id)

@app.route("/logout")
def logout():
    session.pop("email", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/clear_history")
def clear_history():
    if "email" not in session:
        return redirect(url_for("login"))

    try:
        # Clear current session messages
        current_session_id = session.get("current_session_id")
        if current_session_id:
            chat_collection.delete_many({"session_id": current_session_id, "email": session["email"]})
            # Update session metadata
            chat_sessions.update_one(
                {"_id": ObjectId(current_session_id)},
                {"$set": {"message_count": 0, "updated_at": datetime.utcnow()}}
            )
            flash("Current chat history cleared!", "success")
        else:
            flash("No active chat session to clear.", "info")
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        flash("Unable to clear history.", "error")

    return redirect(url_for("chat"))

@app.route("/load_chat/<session_id>")
def load_chat(session_id):
    if "email" not in session:
        return redirect(url_for("login"))
    
    email = session["email"]
    
    # Verify the session belongs to the user
    session_data = chat_sessions.find_one({"_id": ObjectId(session_id), "email": email})
    if not session_data:
        flash("Chat session not found.", "error")
        return redirect(url_for("chat"))
    
    # Set current session ID
    session["current_session_id"] = session_id
    
    flash(f"Loaded chat: {session_data['name']}", "success")
    return redirect(url_for("chat"))

@app.route("/delete_chat/<chat_id>")
def delete_chat(chat_id):
    if "email" not in session:
        return redirect(url_for("login"))
    
    email = session["email"]
    
    try:
        # Delete the specific chat session
        success = delete_chat_session(chat_id, email)
        
        if success:
            # If we deleted the current session, clear it from Flask session
            if session.get("current_session_id") == chat_id:
                session.pop("current_session_id", None)
            
            return {"status": "success", "redirect": url_for("chat")}
        else:
            return {"status": "error", "message": "Failed to delete chat session"}
    except Exception as e:
        logger.error(f"Delete chat error: {e}")
        return {"status": "error", "message": "Failed to delete chat"}

if __name__ == "__main__":
    app.run(debug=True)
















# <div class="chat-history">
#   <h2>Past Chats</h2>
#   <ul>
#     {% if chat_sessions %}
#       {% for chat_session in chat_sessions %}
#         <li>
#           <span class="chat-session-name"
#                 onclick="window.location.href=`{{ url_for('load_chat', session_id=chat_session['_id']) }}`">
#             {{ chat_session['name'] }}
#           </span>
#           <button class="delete-btn"
#                   onclick="event.stopPropagation(); confirmDelete(`{{ chat_session['_id'] | escape }}`, `{{ chat_session['name'] | escape }}`)">
#             <i class="fas fa-trash"></i>
#           </button>
#         </li>
#       {% endfor %}
#     {% else %}
#       <li style="color: #888;">No previous chats</li>
#     {% endif %}
#   </ul>
# </div>









# from flask import Flask, render_template, request, redirect, url_for, session, flash
# from werkzeug.security import generate_password_hash, check_password_hash
# from pymongo import MongoClient
# from pymongo.errors import ConnectionFailure, OperationFailure
# from bson import ObjectId
# from dotenv import load_dotenv
# import os
# import requests
# import logging
# from datetime import datetime

# # Setup logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Load environment variables from .env
# load_dotenv()

# app = Flask(__name__)
# app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# # MongoDB Connection
# try:
#     mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
#     client = MongoClient(mongo_uri)
#     db = client["healthbot"]
#     users = db["users"]
#     chat_collection = db["chat_history"]
#     client.admin.command("ping")
#     logger.info("✅ Successfully connected to MongoDB")
# except (ConnectionFailure, OperationFailure) as e:
#     logger.error(f"❌ MongoDB connection error: {e}")
#     raise

# # Load OpenRouter API Key
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# # Use a working model
# OPENROUTER_MODEL = "mistralai/mixtral-8x7b-instruct"

# def save_chat_history(email, message, role):
#     try:
#         chat_collection.insert_one({
#             "email": email,
#             "message": message,
#             "role": role,
#             "timestamp": datetime.utcnow()
#         })
#     except Exception as e:
#         logger.error(f"Failed to save chat: {e}")

# def get_chat_history(email):
#     try:
#         messages = list(chat_collection.find(
#             {"email": email},
#             {"_id": 0, "message": 1, "role": 1}
#         ).sort("timestamp", 1))
#         return [{"role": m["role"], "content": m["message"]} for m in messages]
#     except Exception as e:
#         logger.error(f"Failed to load chat history: {e}")
#         return []

# def ask_openrouter(user_input):
#     url = "https://openrouter.ai/api/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#         "Content-Type": "application/json",
#         "HTTP-Referer": "http://localhost:5000",
#         "X-Title": "HealthBot"
#     }
#     payload = {
#         "model": OPENROUTER_MODEL,
#         "messages": [
#             {"role": "system", "content": "You are a helpful health assistant. Give simple and safe advice for general health questions."},
#             {"role": "user", "content": user_input}
#         ]
#     }
#     try:
#         response = requests.post(url, headers=headers, json=payload)
#         response.raise_for_status()
#         data = response.json()
#         return data["choices"][0]["message"]["content"]
#     except requests.exceptions.RequestException as e:
#         logger.error(f"OpenRouter API error: {e}")
#         return "I'm having trouble getting a response from the health assistant. Please try again later."

# @app.route("/")
# def home():
#     return redirect(url_for("signup"))

# @app.route("/signup", methods=["GET", "POST"])
# def signup():
#     if request.method == "POST":
#         email = request.form.get("email", "").strip()
#         password = request.form.get("password", "").strip()

#         if not email or not password:
#             flash("Email and password are required", "error")
#             return render_template("signup.html")

#         if users.find_one({"email": email}):
#             flash("Email already registered. Please log in.", "info")
#             return redirect(url_for("login"))

#         try:
#             hashed_password = generate_password_hash(password)
#             users.insert_one({
#                 "email": email,
#                 "password": hashed_password,
#                 "created_at": datetime.utcnow()
#             })
#             flash("Registration successful! Please log in.", "success")
#             return redirect(url_for("login"))
#         except Exception as e:
#             logger.error(f"Signup error: {e}")
#             flash("Something went wrong during signup.", "error")

#     return render_template("signup.html")
# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         email = request.form.get("email", "").strip()
#         password = request.form.get("password", "").strip()

#         try:
#             user = users.find_one({"email": email})
#             if user and check_password_hash(user["password"], password):
#                 session["email"] = email
#                 flash("Login successful!", "success")
#                 return redirect(url_for("chat"))
#             else:
#                 flash("Invalid email or password", "error")
#         except Exception as e:
#             logger.error(f"Login error: {e}")
#             flash("Login failed. Please try again.", "error")

#     return render_template("login.html")

# @app.route("/chat", methods=["GET", "POST"])
# def chat():
#     if "email" not in session:
#         return redirect(url_for("login"))

#     email = session["email"]

#     if request.method == "POST":
#         user_message = request.form.get("message", "").strip()
#         if user_message:
#             save_chat_history(email, user_message, "user")
#             bot_reply = ask_openrouter(user_message)
#             save_chat_history(email, bot_reply, "bot")

#     messages = get_chat_history(email)
#     return render_template("index.html", messages=messages)
# # @app.route('/new_chat')
# # def new_chat():
# #     # You can clear previous messages, start a new session, etc.
# #     return redirect(url_for('chat'))
# @app.route('/new_chat')
# def new_chat():
#     if "email" not in session:
#         return redirect(url_for("login"))

#     try:
#         # Delete previous messages for the user
#         chat_collection.delete_many({"email": session["email"]})
#         flash("New chat started!", "info")
#     except Exception as e:
#         logger.error(f"New chat clear error: {e}")
#         flash("Unable to start new chat.", "error")

#     return redirect(url_for('chat'))

# @app.route("/logout")
# def logout():
#     session.pop("email", None)
#     flash("You have been logged out.", "info")
#     return redirect(url_for("login"))

# @app.route("/clear_history")
# def clear_history():
#     if "email" not in session:
#         return redirect(url_for("login"))

#     try:
#         chat_collection.delete_many({"email": session["email"]})
#         flash("Chat history cleared!", "success")
#     except Exception as e:
#         logger.error(f"Clear history error: {e}")
#         flash("Unable to clear history.", "error")

#     return redirect(url_for("chat"))

# if __name__ == "__main__":
#     app.run(debug=True)