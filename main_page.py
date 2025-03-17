import streamlit as st
from streamlit_feedback import streamlit_feedback

import os
import csv
import datetime
from pathlib import Path

from retrieve import response_save_query
from pages.LawFile import save_uploaded_file,load_documents,get_doc_chunks,is_file_vectorized,vectorize_chunks,store_vectors_in_chroma
from load_and_prepare import RequestIDGenerator


from dotenv import load_dotenv
from email_utils import EmailSender
from chromadb import PersistentClient


load_dotenv()
email_sender = EmailSender(os.getenv('SENDER_EMAIL_ADDRESS'), os.getenv('EMAIL_PASSWORD'))
CHROMA_PATH="chroma"


emoji2str = {"👍": "Positive", "👎": "Négative"}

def save_feedback():
    feedback_dir = Path('feedbacks')
    feedback_dir.mkdir(exist_ok=True)  

    filepath = feedback_dir / f'{st.session_state.session_id}.csv'
    
    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Question", "Réponse", "Valeur", "Commentaire", "Fichier Uploader", "Sources"])  
        
        for feedback in st.session_state.feedback_history:
            writer.writerow([
                feedback.get('Question', ''),
                feedback.get('Réponse', ''),
                feedback.get('feedbacks', {}).get('valeur', ''),  
                feedback.get('feedbacks', {}).get('text', ''),  
                feedback.get('document_uploaded', 'NAN'),  
                feedback.get('sources', 'NAN')
            ])

    return filepath

def structure_feedback(response):
    if not st.session_state.feedback_history:
        st.warning("Aucune interaction disponible pour ajouter un feedback.")
        return

    chroma_client = PersistentClient(path="CHROMA_PATH")
    qa_collection = chroma_client.get_or_create_collection(name="vector_store_qa")

    last_feedback_entry = st.session_state.feedback_history[-1]
    request_id = last_feedback_entry.get("request_id", "NAN")

    feedback_text = response.get("text", "").strip() if response.get("text") else "NAN"
    feedback_data = {
        "valeur": emoji2str.get(response.get("score"), "NAN"),
        "text": feedback_text
    }

    # ajout de ces données dans la dbv
    qa_collection.update(
        ids=[request_id],
        metadatas=[{
            "feedback_text": feedback_data["text"],
            "feedback_valeur": feedback_data["valeur"]
        }]
    )

    last_feedback_entry.update({'feedbacks': feedback_data})

    # Sauvegarde immédiate du feedback
    #save_feedback()

    st.success("Feedback sauvegardé avec succès !")

def initialize_session_state():
    #Générer un identifiant unique pour chaque session for the user 
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  

    st.session_state.setdefault("messages", [])  
    st.session_state.setdefault("feedback_history", [])  
    st.session_state.setdefault("file_processed", False)  
    st.session_state.setdefault("chat_history", [])  
    st.session_state.setdefault("uploaded_file", None)  
    st.session_state.setdefault("file_uploader_key", 0)  
    st.session_state.setdefault("conversation", None)  
    st.session_state.setdefault("document_uploaded", None)  


def reset_conversation(email_sender):
    """
    Réinitialise l'état de la session pour démarrer une nouvelle conversation,
    tout en sauvegardant les feedbacks et en envoyant un email si nécessaire.
    """
    if len(st.session_state.feedback_history) > 0:
        feedback_file = save_feedback()  # Sauvegarde les feedbacks de l'utilisateur

        # Envoi du feedback par email
        email_sender.send_feedback_email(os.getenv('RECIP_EMAIL_ADDRESS'), feedback_file)

        st.success(f"Email envoyé avec succès au client avec le fichier {feedback_file.name} !")

    
    initialize_session_state()  
    st.session_state["file_uploader_key"] += 1  
    st.rerun() 

def main():

    try:
        initialize_session_state()
        st.set_page_config(layout="wide", page_title="LAW_GPT DXC CDG")

        st.sidebar.image("static/logo_dxc.jpg", width=600)
        st.sidebar.warning(
            " **Bienvenue sur LAWGPT !** \n\n"
            "- Vous pouvez poser une question juridique **avec ou sans fichier**.\n"
            "- Si vous **uploadez un fichier**, le chatbot s'appuiera sur son contenu.\n"
            "- Si vous cliquez sur **'Uploader un nouveau fichier'**, la partie d'upload va être réinitialisée.\n"
            "- Si vous cliquez sur **'Initialiser la conversation'**, la conversation sera réinitialisée."
        )

        # Bouton de réinitialisation total de la conversation
        if st.sidebar.button("🔄 Initialiser la conversation"):
            reset_conversation(email_sender)
            st.rerun()
        
        if st.sidebar.button("📂 Uploader un nouveau fichier"):
            initialize_session_state()
            st.session_state["document_uploaded"] = None
            st.session_state["file_uploader_key"] += 1  
            st.rerun()

        # Upload du fichier (pdf,des lois ,contrat)
        uploaded_file = st.sidebar.file_uploader(
            "Déposez un fichier PDF (optionnel)", type=["pdf"], key=st.session_state["file_uploader_key"]
        )

        if uploaded_file is not None:
            file_path = save_uploaded_file(uploaded_file)
            st.session_state["document_uploaded"] = uploaded_file.name

            if is_file_vectorized(file_path):
                st.warning(f"📂 Le fichier **{uploaded_file.name}** existe déjà ")
            else:
                documents = load_documents()
                text_chunks = get_doc_chunks(documents)
                embedded_vectors = vectorize_chunks(text_chunks)
                store_vectors_in_chroma(text_chunks, embedded_vectors, file_path)

        st.markdown("<h1 style='color: purple;'><i class='fas fa-balance-scale'></i> LAWGPT </h1>", unsafe_allow_html=True)

        # Affichage les messages d'avant dans la conversation
        if not st.session_state["messages"]:
            st.session_state["messages"].append({"role": "assistant", "content": "Hello, I am your legal chatbot! 😊"})

        for msg in st.session_state["messages"]:
            st.chat_message(msg["role"]).write(msg["content"])

        document_name = st.session_state.get("document_uploaded", None)

        # Zone where the user ask
        if prompt := st.chat_input("Posez votre question juridique ici..."):
            st.session_state["messages"].append({
                "role": "user",
                "content": prompt,
                "document_uploaded": document_name
            })
            st.chat_message("user").write(prompt)

            # invokation de la fonction qui génére de la réponse
            with st.spinner("Recherche en cours..."):
                formatted_response, response_data = response_save_query(prompt, document_name)

            # Ajout de la réponse à l'historique et sauvegarde
            response_data["Session_ID"] = st.session_state.session_id
            st.session_state["feedback_history"].append(response_data)
            save_feedback()

            st.session_state["messages"].append({
                "role": "assistant",
                "content": formatted_response,
                "document_uploaded": document_name
            })
            st.chat_message("assistant").write(formatted_response)

        # Gestion des feedbacks
        if len(st.session_state["feedback_history"]) > 0:
            feedback_response = streamlit_feedback(
                feedback_type="thumbs",
                optional_text_label="[Optional] Explain your choice.",
                key=f"fb_{len(st.session_state['feedback_history'])}",
            )
            if feedback_response:
                structure_feedback(feedback_response)

    except Exception as e:
        error_message = f"Erreur : {e}"
        st.error("L'opération a échoué.")
        email_sender.send_error_email(os.getenv('RECIP_EMAIL_ADDRESS'), error_message)

if __name__ == "__main__":
    main()
