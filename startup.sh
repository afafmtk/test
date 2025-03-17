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

#  Vérifier si ChromaDB tourne bien
echo "🔍 Vérification du serveur ChromaDB..."
RESPONSE=$(curl -s http://localhost:8000/api/v1/heartbeat | grep '"status": "ok"')

if [ -z "$RESPONSE" ]; then
    echo "❌ Erreur : ChromaDB n'est pas lancé correctement."
    exit 1
fi

echo "✅ ChromaDB est bien actif !"

#  Lancer l'application Streamlit
echo "✅ Lancement de l'application Streamlit..."
streamlit run main_page.py
