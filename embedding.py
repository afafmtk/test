from langchain_ollama import OllamaEmbeddings
from typing import List

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
#from ollama import OllamaEmbeddings  

# Définir une classe personnalisée pour les embeddings avec Ollama
class MyEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name="mxbai-embed-large"):
        self.embeddings = OllamaEmbeddings(model=model_name)
    
    def __call__(self, inputs: Documents) -> Embeddings:
        return [self.embeddings.embed_query(text) for text in inputs]



"""def get_embedding_function_Ollama(input_text):
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")  
    vector = embeddings.embed_query(input_text) 
    return vector
"""