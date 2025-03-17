import streamlit as st
import pandas as pd
import os
import shutil
import logging
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from load_and_prepare import calculate_vecteur_ids
from chromadb import PersistentClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from itertools import islice

from embedding import MyEmbeddingFunction

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "data"
CHROMA_PATH = "chroma"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHROMA_PATH, exist_ok=True)

def save_uploaded_file(uploaded_file):
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    return file_path

def load_documents():
    document_loader = PyPDFDirectoryLoader(UPLOAD_FOLDER)
    return document_loader.load()

def get_doc_chunks(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


def batched(lst, batch_size):
    it = iter(lst)
    return iter(lambda: list(islice(it, batch_size)), [])



def vectorize_chunks(text_chunks, batch_size=1000):
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")  
    
    embedded_vectors = []
    for batch in batched(text_chunks, batch_size):
        batch_vectors = [embeddings.embed_query(chunk.page_content) for chunk in batch]
        embedded_vectors.extend(batch_vectors)
    
    return embedded_vectors


def store_vectors_in_chroma(text_chunks, embedded_vectors, file_path):
    chroma_client = PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name="vector_store_file")
    
    chunks_with_ids = calculate_vecteur_ids(text_chunks)
    existing_items = collection.get(include=["metadatas"])  
    existing_ids = set(meta["id"] for meta in existing_items["metadatas"] if "id" in meta)
    logger.info(f"📂 Nombre de documents existants dans ChromaDB : {len(existing_ids)}")
    
    new_chunks = [chunk for chunk in chunks_with_ids if chunk.metadata["id"] not in existing_ids]

    if new_chunks:
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        logger.info(f"✅ Ajout de {len(new_chunks)} nouveaux embeddings à ChromaDB.")

        collection.add(
    documents=[chunk.page_content for chunk in new_chunks],  
    metadatas=[chunk.metadata for chunk in new_chunks],  
    embeddings=[embedded_vectors[idx] for idx in range(len(new_chunks))],  
    ids=new_chunk_ids
)



        return True
    else:
        logger.info("⚠️ Aucun nouvel embedding à ajouter.")
        return False



def is_file_vectorized(file_path):
    chroma_client = PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name="vector_store_file")
    existing_items = collection.get(include=[])
    existing_ids = set(existing_items["ids"])
    
    return any(file_path in chunk_id for chunk_id in existing_ids)


def initialize_session_state():
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

def reset_conversation():
    st.session_state.uploaded_file = None
    st.session_state.file_uploader_key += 1       


def main():
    initialize_session_state()
    st.markdown("""<h1 style='color: purple;'>📂 Download and Process Files</h1>""", unsafe_allow_html=True)
    st.sidebar.title("Options")
 

    if st.sidebar.button("📂 Uploader un nouveau fichier"):
        reset_conversation()
        st.rerun()

    uploaded_file = st.file_uploader("Upload a file :", type=["pdf"], key=st.session_state.file_uploader_key)
    
    if uploaded_file:
        st.session_state['file_uploaded'] = True
        file_path = save_uploaded_file(uploaded_file)

        if is_file_vectorized(file_path):
            st.success(f"📄 Le fichier '{uploaded_file.name}' est déjà vectorisé !")
        else:
            st.success(f"📄 Fichier '{uploaded_file.name}' uploadé avec succès !")

            documents = load_documents()
            chunks = get_doc_chunks(documents)
            embedded_vectors = vectorize_chunks(chunks)

            if store_vectors_in_chroma(chunks, embedded_vectors, file_path):
                st.success("✅ Le fichier a été traité et ses données vectorisées sont enregistrées dans ChromaDB.")
            else:
                st.error("❌ Le fichier n'a pas pu être correctement stocké dans ChromaDB.")

    # Affichage des fichiers déjà vectorisés
    chroma_client = PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name="vector_store_file")
    existing_items = collection.get(include=["metadatas"])
    vectorized_files = set(meta["source"] for meta in existing_items["metadatas"] if "source" in meta)
    
    
    if vectorized_files:
        st.subheader("📂 Fichiers déjà vectorisés")
        df_files = pd.DataFrame(sorted(vectorized_files), columns=["Vectorized Files"])
        st.dataframe(df_files)

        

if __name__ == "__main__":
    main()
