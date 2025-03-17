#!/bin/bash

echo " Démarrage des services pour l'application..."

#  Démarrer Ollama en arrière-plan
echo " Lancement de Ollama..."
ollama serve &

#  Attendre quelques secondes pour s'assurer qu'Ollama est bien lancé
sleep 5

#  Démarrer le serveur ChromaDB en arrière-plan
echo " Lancement de ChromaDB..."
chromadb run --path ./chroma &

#  Attendre quelques secondes pour s'assurer que ChromaDB est bien lancé
sleep 5

#  Lancer l'application Streamlit
echo "✅ Lancement de l'application Streamlit..."
streamlit run main_page.py
