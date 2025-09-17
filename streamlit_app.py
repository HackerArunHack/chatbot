# streamlit_app.py
import os
import time
import streamlit as st
from langdetect import detect
from rag_utils import init_gemini_client, process_documents, rag_query

# ---------------- Init Gemini Client ----------------
genai_client = init_gemini_client()

st.set_page_config(page_title="PUTHIRAN AI", layout="wide")

# ---------------- Admin credentials (env or defaults) ----------------
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Sidebar navigation
menu = st.sidebar.radio("Navigation", ["User", "Admin"])

# ---------------- Admin Page ----------------
if menu == "Admin":
    st.title("📂 Admin Panel")

    # Initialize admin auth session state
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if "admin_username" not in st.session_state:
        st.session_state["admin_username"] = ""
    if "uploaded_files" not in st.session_state:
        st.session_state["uploaded_files"] = []  # list of dicts: {"name":..., "data":...}

    # Admin login
    if not st.session_state["admin_authenticated"]:
        st.subheader("Admin login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login"):
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    st.session_state["admin_authenticated"] = True
                    st.session_state["admin_username"] = username
                    st.success("Login successful — you can now manage documents.")
                    st.stop()  # stops execution, next run shows upload UI
                else:
                    st.error("Invalid username or password.")
        with col2:
            if st.button("Cancel"):
                st.info("Login cancelled.")
    else:
        st.markdown(f"**Logged in as:** `{st.session_state['admin_username']}`")
        if st.button("Logout"):
            st.session_state["admin_authenticated"] = False
            st.session_state["admin_username"] = ""
            st.success("Logged out.")
            st.stop()

        # ---------------- Upload New Files ----------------
        st.subheader("Upload New Documents")
        uploaded_files = st.file_uploader(
            "Upload files (PDF, CSV, XLSX, TXT)",
            type=["pdf", "csv", "xlsx", "txt"],
            accept_multiple_files=True
        )

        if uploaded_files:
            for f in uploaded_files:
                st.session_state["uploaded_files"].append({"name": f.name, "data": f})
            st.success(f"✅ Uploaded {len(uploaded_files)} file(s).")

        # ---------------- List Uploaded Files ----------------
        st.subheader(f"Uploaded Files ({len(st.session_state['uploaded_files'])})")

        if st.session_state["uploaded_files"]:
            for idx, file_dict in enumerate(st.session_state["uploaded_files"]):
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.text(file_dict["name"])
                with col2:
                    if st.button(f"Delete {file_dict['name']}", key=f"del_{idx}"):
                        st.session_state["uploaded_files"].pop(idx)
                        st.success(f"Deleted {file_dict['name']}")
                        st.stop()
                with col3:
                    if st.button(f"Process {file_dict['name']}", key=f"proc_{idx}"):
                        try:
                            chunks = process_documents([file_dict["data"]])
                            st.success(f"✅ Processed {chunks} text chunks from {file_dict['name']}")
                        except Exception as e:
                            st.error(f"Error processing {file_dict['name']}: {e}")
                        st.stop()
        else:
            st.info("No files uploaded yet.")

# ---------------- User Page ----------------
else:
    st.title("WELCOME TO PUTHIRAN AI")

    # CSS for chat bubble styling
    st.markdown(
        """
        <style>
        .user-bubble {
            background-color: #d4f8d4;
            color: black;
            padding: 10px;
            border-radius: 10px;
            margin: 5px;
            max-width: 80%;
        }
        .bot-bubble {
            background-color: #f8d4d4;
            color: black;
            padding: 10px;
            border-radius: 10px;
            margin: 5px;
            max-width: 80%;
        }
        pre {
            background-color: #1e1e1e !important;
            color: #d4d4d4 !important;
            padding: 10px;
            border-radius: 8px;
            overflow-x: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Init session states
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "user_lang" not in st.session_state:
        st.session_state["user_lang"] = "en"

    # Detect language
    def detect_lang(text: str) -> str:
        try:
            return detect(text)
        except Exception:
            return "en"

    # Show chat history
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>USER --> {msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>CHAT BOT --> {msg['content']}</div>", unsafe_allow_html=True)

    # User input box
    user_input = st.chat_input("Type your question…")

    if user_input:
        # Detect language
        user_lang = detect_lang(user_input)
        st.session_state["user_lang"] = user_lang

        # Save user message
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Show "thinking..." while waiting
        with st.spinner("🤖 PUTHIRAN is thinking..."):
            try:
                answer = rag_query(genai_client, user_input)
            except Exception as e:
                answer = f"⚠️ Error: {e}"

        # Progressive typing effect
        placeholder = st.empty()
        typed_answer = ""
        for char in answer:
            typed_answer += char
            placeholder.markdown(f"<div class='bot-bubble'>CHAT BOT --> {typed_answer}</div>", unsafe_allow_html=True)
            time.sleep(0.01)  # typing speed

        # Save final bot message
        st.session_state["messages"].append({"role": "bot", "content": answer})

    # Utility buttons
    colA, colB = st.columns(2)
    with colA:
        if st.button("🗑️ Clear chat"):
            st.session_state["messages"] = []
            st.stop()  # refresh page
    with colB:
        if st.button("🔁 Reset language"):
            st.session_state["user_lang"] = "en"
            st.success("Language reset.")
