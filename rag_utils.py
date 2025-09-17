# rag_utils.py
from typing import List
from google import genai
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import pandas as pd
from PyPDF2 import PdfReader

# 🔑 Put your Gemini API key here
#API_KEY = "AIzaSyD5Q15Y0mbecpCrzJV2Q2-VBMIL-Yzd6Pc"
API_KEY="AIzaSyD33kWbvrYjO-LjReIve4ifX9wlSckfkSo"

def init_gemini_client():
    """
    Initialize the Google GenAI client using direct API key.
    """
    client = genai.Client(api_key=API_KEY)
    return client

def embed_texts(texts: List[str], persist_directory="./chroma_db"):
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = Chroma.from_texts(
        texts,
        embedding=embedding_model,
        persist_directory=persist_directory
    )
    vectordb.persist()
    return vectordb

def load_vectorstore(persist_directory="./chroma_db"):
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding_model
    )
    return vectordb

def process_documents(uploaded_files, persist_directory="./chroma_db"):
    """
    Extract text from uploaded files (PDF, CSV, Excel, TXT).
    """
    docs = []

    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            docs.append(text)

        elif uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            docs.append(df.to_string())

        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
            docs.append(df.to_string())

        elif uploaded_file.name.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8")
            docs.append(text)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = []
    for doc in docs:
        chunks.extend(text_splitter.split_text(doc))

    embed_texts(chunks, persist_directory)
    return len(chunks)

def rag_query(client, query, persist_directory="./chroma_db", k=3):
    """
    Query the RAG system using Gemini 2.0 Flash-Lite.
    """
    vectordb = load_vectorstore(persist_directory)
    docs = vectordb.similarity_search(query, k=k)
    context = "\n".join([doc.page_content for doc in docs])

    prompt = f"Context:\n{context}\n\nUser Question: {query}\n\nAnswer:"
    resp = client.models.generate_content(
        model="gemini-2.0-flash-lite",  # ✅ fixed model
        contents=prompt,
    )
    return resp.text
