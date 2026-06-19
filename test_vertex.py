from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

print("hello")
# Initialisation du modèle Gemini sur Vertex AI
llm = ChatVertexAI(
    model="gemini-3.1-flash-lite",
    project="project-cf4c8688-2144-4f95-a14",
    location="global",
)

# Envoi d'un message
response = llm.invoke([
    HumanMessage(content="hello")
])

print("response.content=>")
print(response.content)