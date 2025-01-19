import os
from flask import Flask, request, jsonify

# Imports LangChain (para agents, chains, etc.)
from langchain.agents import Tool, AgentExecutor, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

# LangGraph - aqui seria para orquestrar e visualizar fluxos.
# No exemplo, usaremos apenas a notação para integrar depois.
# from langgraph import some_graph_library (Placeholder)

#################################################
# Mock do LlamaGuard (placeholder de moderação) #
#################################################

def llama_guard_moderation(content: str) -> bool:
    """
    Retorna True se o conteúdo estiver permitido, False caso contrário.
    Aqui é um mock simples. Em produção, integraria com LlamaGuard de fato.
    """
    blocked_words = ["ofensa", "palavrão", "terrorismo"]  # Exemplo
    for bw in blocked_words:
        if bw in content.lower():
            return False
    return True

###################################
# Agente de Busca (Tool / Action) #
###################################

def search_tool(query: str) -> str:
    """
    Função que simula uma busca. Em produção, integrar com Google, Bing ou outro.
    Para este exemplo, retorna apenas um texto fixo ou simula resultados.
    """
    # Exemplo simples: imagine que consultamos um backend ou API, retornando máx 10 resultados.
    # Aqui, retornaremos uma string como se fosse um conjunto de resultados.
    fake_results = [
        "Resultado 1 sobre o assunto: ...",
        "Resultado 2 sobre o assunto: ...",
        "Resultado 3 sobre o assunto: ...",
        # ...
    ]
    # Limitar a 10 resultados
    results_limited = fake_results[:10]
    return "\n".join(results_limited)

search_tool_action = Tool(
    name="search_tool",
    func=search_tool,
    description="Use esta ferramenta para buscar informações externas quando necessário. Limite de 10 resultados."
)

###########################################
# Agente Conversacional (LangChain Agent) #
###########################################

# Prompt base do agente, incluindo regra sobre Engenharia Civil
base_prompt = """
Você é um agente conversacional especializado em responder qualquer pergunta, 
EXCETO sobre Engenharia Civil. Se o tema for Engenharia Civil, você deve recusar.
Se precisar de informações extras de uma fonte externa, utilize a ferramenta 'search_tool'.
"""

prompt = PromptTemplate(
    template=base_prompt,
    input_variables=[]
)

# Configuração do modelo (exemplo com ChatOpenAI)
# Em produção, configure chave e versão adequadas (OpenAI, Azure, etc.)
chat_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# Memória de conversa, para manter contexto de maneira simples
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# Inicializa o agente com a ferramenta de busca
conversational_agent = initialize_agent(
    tools=[search_tool_action],
    llm=chat_model,
    agent="chat-conversational-react-description",  # Exemplo de agente
    verbose=True,
    memory=memory,
    # Caso queira passar um PromptTemplate custom:
    # prompt=...
)

#################
# Criação Flask #
#################

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask_agent():
    """
    Endpoint principal: recebe JSON com a pergunta do usuário,
    passa ao agente conversacional, e retorna resposta em JSON.
    """
    data = request.get_json()
    user_question = data.get("question", "")

    # 1. Verifica moderação da entrada (exemplo)
    if not llama_guard_moderation(user_question):
        return jsonify({"answer": "Desculpe, a pergunta contém conteúdo bloqueado."}), 400

    # 2. Verifica se é sobre Engenharia Civil (bloqueia explicitamente)
    if "engenharia civil" in user_question.lower():
        return jsonify({"answer": "Desculpe, não estou habilitado a falar sobre Engenharia Civil."})

    # 3. Caso permitido, passa a pergunta ao agente conversacional
    try:
        response = conversational_agent.run(user_question)
    except Exception as e:
        return jsonify({"answer": f"Erro ao processar a solicitação: {str(e)}"}), 500

    # 4. Verifica moderação da resposta (se quiser moderar a saída também)
    if not llama_guard_moderation(response):
        return jsonify({"answer": "Desculpe, a resposta contém conteúdo bloqueado."}), 400

    return jsonify({"answer": response})


if __name__ == "__main__":
    # Em produção, pode-se usar gunicorn ou outro WSGI server
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
