# streamlit_app.py
import os
import time
import streamlit as st
import sqlite3
from langdetect import detect
from rag_utils import init_gemini_client, process_documents, rag_query

# ---------------- Init Gemini Client ----------------
genai_client = init_gemini_client()

st.set_page_config(page_title="PUTHIRAN AI", layout="wide")

# ---------------- Database ----------------
def init_db():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    role TEXT,
                    content TEXT,
                    FOREIGN KEY(chat_id) REFERENCES chats(id)
                )""")
    conn.commit()
    conn.close()

def create_chat(name="New Chat"):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO chats (name) VALUES (?)", (name,))
    conn.commit()
    chat_id = c.lastrowid
    conn.close()
    return chat_id

def get_chats():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT id, name FROM chats")
    chats = c.fetchall()
    conn.close()
    return chats

def rename_chat(chat_id, new_name):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("UPDATE chats SET name=? WHERE id=?", (new_name, chat_id))
    conn.commit()
    conn.close()

def delete_chat(chat_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def save_message(chat_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
    conn.commit()
    conn.close()

def get_messages(chat_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE chat_id=?", (chat_id,))
    messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return messages

# Init DB
init_db()

# ---------------- Admin credentials ----------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ---------------- Header navigation ----------------
st.markdown("""
    <style>
    .header-button {
        background-color: #4CAF50; color: white; padding: 8px 16px;
        border: none; border-radius: 5px; margin: 2px; cursor: pointer;
    }
    .header-button:hover {
        background-color: #45a049;
    }
    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 6])
with col1:
    if st.button("🏠 User", key="nav_home"):
        st.session_state["page"] = "User"
with col2:
    if st.button("🔧 Admin", key="nav_admin"):
        st.session_state["page"] = "Admin"
with col3:
    st.markdown("<h3 style='margin:0; padding-left:10px;'>WELCOME TO PUTHIRAN AI</h3>", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = "User"

menu = st.session_state["page"]

# ---------------- Admin Page ----------------
if menu == "Admin":
    st.title("📂 Admin Panel")

    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False

    if not st.session_state["admin_authenticated"]:
        st.subheader("Admin login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.success("Login successful")
            else:
                st.error("Invalid username or password.")
    else:
        if st.button("Logout"):
            st.session_state["admin_authenticated"] = False
            st.success("Logged out.")
            st.stop()

        st.subheader("Upload New Documents")
        uploaded_files = st.file_uploader("Upload files (PDF, CSV, XLSX, TXT)",
                                          type=["pdf", "csv", "xlsx", "txt"],
                                          accept_multiple_files=True)
        if uploaded_files:
            for f in uploaded_files:
                try:
                    chunks = process_documents([f])
                    st.success(f"✅ Processed {chunks} text chunks from {f.name}")
                except Exception as e:
                    st.error(f"Error processing {f.name}: {e}")

# ---------------- User Page ----------------
else:
    #st.title("WELCOME TO PUTHIRAN AI")

    # Sidebar Chat Management
    st.sidebar.subheader("💬 Chats")
    chats = get_chats()

    if "current_chat" not in st.session_state:
        if chats:
            st.session_state["current_chat"] = chats[0][0]
        else:
            st.session_state["current_chat"] = create_chat("Chat 1")

    if st.sidebar.button("➕ Create New Chat"):
        new_id = create_chat("New Chat")
        st.session_state["current_chat"] = new_id
        st.rerun()

    for chat_id, chat_name in chats:
        with st.sidebar.expander(chat_name if chat_id != st.session_state["current_chat"] else f"⭐ {chat_name}", expanded=False):
            if st.button("📂 Open Chat", key=f"select_{chat_id}"):
                st.session_state["current_chat"] = chat_id
                st.rerun()
            new_name = st.text_input("✏️ Rename chat", value=chat_name, key=f"input_{chat_id}")
            if st.button("💾 Save Rename", key=f"save_{chat_id}"):
                rename_chat(chat_id, new_name)
                st.rerun()
            if st.button("🗑️ Delete Chat", key=f"delete_{chat_id}"):
                delete_chat(chat_id)
                st.rerun()

    # CSS for chat bubbles + code
    st.markdown("""
        <style>
        .chat-container { display: flex; flex-direction: column; }
        .user-bubble {
            background-color: #d4f8d4; color: black;
            padding: 10px; border-radius: 10px; margin: 5px;
            max-width: 70%; align-self: flex-end; white-space: pre-wrap;
        }
        .bot-bubble {
            background-color: #f8d4d4; color: black;
            padding: 10px; border-radius: 10px; margin: 5px;
            max-width: 70%; align-self: flex-start; white-space: pre-wrap;
        }
        pre {
            background-color: #1e1e1e; color: #d4d4d4;
            padding: 10px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap;
        }
        code {
            color: #f8f8f2; background-color: #272822;
            padding: 2px 4px; border-radius: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Load messages
    messages = get_messages(st.session_state["current_chat"])
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for msg in messages:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            if "```" in msg["content"] or "def " in msg["content"] or "import " in msg["content"] or "class " in msg["content"]:
                code_content = msg["content"].replace("```", "")
                st.markdown(f"<div class='bot-bubble'><pre><code>{code_content}</code></pre></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Init pause state
    if "pause_bot" not in st.session_state:
        st.session_state["pause_bot"] = False

    # User input
    user_input = st.chat_input("Type your question…")

    # Pause / Resume buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⏸️ Pause Bot"):
            st.session_state["pause_bot"] = True
    with col2:
        if st.button("▶️ Resume Bot"):
            st.session_state["pause_bot"] = False

    if user_input:
        save_message(st.session_state["current_chat"], "user", user_input)
        with st.spinner("🤖 PUTHIRAN is thinking..."):
            try:
                answer = rag_query(genai_client, user_input)
            except Exception as e:
                answer = f"⚠️ Error: {e}"

        placeholder = st.empty()
        typed_answer = ""
        for char in answer:
            if st.session_state["pause_bot"]:
                break
            typed_answer += char
            if "```" in answer or "def " in answer or "import " in answer or "class " in answer:
                code_content = typed_answer.replace("```", "")
                placeholder.markdown(f"<div class='bot-bubble'><pre><code>{code_content}</code></pre></div>", unsafe_allow_html=True)
            else:
                placeholder.markdown(f"<div class='bot-bubble'>{typed_answer}</div>", unsafe_allow_html=True)
            time.sleep(0.01)

        save_message(st.session_state["current_chat"], "bot", typed_answer)
        st.rerun()
