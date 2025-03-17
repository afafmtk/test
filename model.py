from langchain_community.llms.ollama import Ollama


def invoke_model_mistral(query_text: str):
    model = Ollama(model="mistral")
    response_text = model.invoke(query_text)
    return response_text


def invoke_model_ollama(query_text: str):
    model = Ollama(model="llama3.2")
    response_text = model.invoke(query_text)
    return response_text

