import argparse
import os
import shutil
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
import logging

#from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from datetime import datetime
from pypdf import PdfReader
from chromadb import PersistentClient

CHROMA_PATH = "chroma"
DATA_PATH = "data"

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


class RequestIDGenerator:
    _counter = 0

    @staticmethod
    def generate_req_res_id(document_name=None):
        """
        Génère un ID unique pour une requête juridique.

        Args:
            document_name (str, optional): Nom du document juridique (par défaut 'NAN').

        Returns:
            str: ID au format "query/response:YYYYMMDD:NUM:DocumentName"
        """
        current_date = datetime.now().strftime("%Y%m%d")
        RequestIDGenerator._counter += 1
        counter_str = str(RequestIDGenerator._counter)

        if document_name is None or not document_name.strip():
            document_name = "NAN"
        else:
            document_name = document_name.strip().replace(" ", "-")

        return f"query/response:{current_date}:{counter_str}:{document_name}"




def calculate_vecteur_ids(chunks):

    # This will create IDs like "data/monopoly.pdf:6:2"
    # Page Source : Page Number : Chunk Index
    
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add it to the page meta-data.
        chunk.metadata["id"] = chunk_id

    return chunks


def clear_database():
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)



