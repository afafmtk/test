from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from chromadb import PersistentClient
from chromadb import HttpClient
from embedding import MyEmbeddingFunction
from prompts import PROMPT_TEMPLATE
from model import invoke_model_mistral
from load_and_prepare import RequestIDGenerator
import datetime

CHROMA_PATH = "chroma"

def response_save_query(query_text: str, document_name=None):
    """
    task ::: generation de réponse+ sauvegardement dans la base de données chromadb
    """

    # Se connecter au serveur ChromaDB lancé
    chroma_client = HttpClient(host="localhost", port=8000)
    qa_collection = chroma_client.get_or_create_collection(name="vector_store_qa")
    doc_collection = chroma_client.get_or_create_collection(name="vector_store_file")
    
    request_id = RequestIDGenerator.generate_req_res_id(document_name)
    
    embedding_function = MyEmbeddingFunction()
    question_embedding = embedding_function([query_text])[0]
    
    vec_results = doc_collection.query(
        query_embeddings=[question_embedding],
        n_results=5,
        include=["documents", "distances", "metadatas"]
    )
    
    retrieved_docs = vec_results.get("documents", [[]])[0]
    sources = [meta.get("id", "Inconnu") for meta in vec_results.get("metadatas", [{}])[0]]
    
    context_text = "\n\n---\n\n".join(retrieved_docs) if retrieved_docs else "Aucune information spécifique trouvée."
    
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    
    response_text = invoke_model_mistral(prompt)
    
    qa_collection.add(
        ids=[request_id],  
        embeddings=[question_embedding],  
        metadatas=[{
            "type": "qa",
            "question": query_text,
            "response_text": response_text,  
            "sources": ", ".join(sources) if sources else "Aucune source disponible.",
            "document_uploaded": document_name if document_name else "NAN"
        }]
    )
    
    response_data = {
        'request_id': request_id,
        'Timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Session_ID': None,  
        'Question': query_text,
        'Réponse': response_text,
        'document_uploaded': document_name,
        'sources': ", ".join(sources) if sources else "Aucune source disponible"
    }
    
    formatted_response = f"{response_text}\n\n📄 **Sources:** {', '.join(sources) if sources else 'Aucune source disponible.'}"
    
    return formatted_response, response_data