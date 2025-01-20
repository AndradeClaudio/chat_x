import asyncio
from grpc import aio  # A API assíncrona do gRPC

import genai_pb2
import genai_pb2_grpc

from langchain.agents import Tool, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from nemoguardrails import RailsConfig, LLMRails
from langchain.tools import DuckDuckGoSearchRun

from typing import Dict, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from duckduckgo_search import DDGS
from langchain_core.runnables.graph import MermaidDrawMethod
from dotenv import load_dotenv



# Inicializa a configuração do Rails
rails_config = RailsConfig.from_path("./config")
rails = LLMRails(rails_config)

async def guard_moderation_async(consulta: str, bot: bool) -> bool:
    tipo = "bot" if bot else "user"
    response = await rails.generate_async(
        messages=[
            {
                "role": tipo,
                "content": consulta,
            }
        ]
    )
    info = rails.explain()
    if "bot refuse" in info.colang_history:
        return False
    return True


# Função síncrona para lidar com ambientes que não são totalmente assíncronos
def guard_moderation(consulta: str, bot: bool) -> bool:
    return asyncio.run(guard_moderation_async(consulta, bot))

class State(TypedDict):
    query: str
    categoria: str
    resposta: str
    history: str  # Novo campo para armazenar o histórico de mensagens

# ------------------------------------------------------------------------------------
# Funções de suporte
# ------------------------------------------------------------------------------------
def format_history(messages) -> str:
    """
    Converte a lista de mensagens do chat em uma string única,
    para fornecer ao modelo como contexto.
    """
    formatted = []
    for msg in messages:
        role = "Usuário" if msg["role"] == "user" else "Assistente"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)

def web_search(query: str) -> str:
    """
    Obtém informações gerais usando o DuckDuckGo.
    Pode ser usado para complementar conhecimento em perguntas complexas.
    """
    # Realiza a pesquisa no DuckDuckGo, retornando no máximo 5 resultados
    results = DDGS().text(query, max_results=10)
    
    # Monta a string de contexto
    contexts = "\n---\n".join(
        ["\n".join([item["title"], item["body"], item["href"]]) for item in results]
    )
    return contexts

# ------------------------------------------------------------------------------------
# Funções de nós do fluxo (grafo)
# ------------------------------------------------------------------------------------
def categorize(state: State) -> State:
    """
    Categoriza a consulta do cliente em 'simples' ou 'complexa'.
    Agora, consideramos também o histórico de mensagens no prompt, caso seja útil.
    """
    prompt = ChatPromptTemplate.from_template(
    """
    Você deve analisar a seguinte conversa (histórico) e a última pergunta do usuário
    para decidir se a consulta é 'simples' ou 'complexa'.

    Histórico da conversa:
    {history}

    Última consulta do usuário:
    {query}

    Instrução:
    - Sempre que você for relacionada ‘dia’, ‘hora’, ‘mês’, ‘ano’, ou termos relacionados a tempo, responda "complexa”
    - se for uma pergunta relacionado aos ultimos 2 anos responda "complexa".
    - Se for um tema complexo, responda "complexa".
    - Se for uma simples conversa informal, responda "simples".
    - Responda APENAS com 'simples' ou 'complexa'.
    """
    )
    chain = prompt | ChatOpenAI(temperature=0, model="gpt-4o-mini")
    categoria = chain.invoke({
        "history": state["history"],
        "query": state["query"]
    }).content.strip().lower()
    print(categoria)
    return {"categoria": categoria}

def handle_technical(state: State) -> State:
    """
    Fornece uma resposta 'simples' para a consulta, levando em conta o histórico.
    """
    prompt = ChatPromptTemplate.from_template(
        """
        Você é um assistente que deve considerar o histórico de conversa abaixo
        e a nova pergunta do usuário. Forneça a melhor resposta possível para
        questões consideradas 'simples'.

        Histórico da conversa:
        {history}

        Pergunta atual:
        {query}

        Responda de maneira objetiva e clara.
        """
    )
    chain = prompt | ChatOpenAI(temperature=0, model="gpt-4o-mini")
    resposta = chain.invoke({
        "history": state["history"],
        "query": state["query"]
    }).content
    return {"resposta": resposta}

def handle_web_search(state: State) -> State:
    """
    Node responsável por buscar informações na web e gerar uma resposta usando o LLM
    para questões consideradas 'complexas'.
    """
    # Realiza a pesquisa usando DuckDuckGo
    search_content = web_search(state["query"])
    
    prompt = ChatPromptTemplate.from_template(
        """
        Você obteve as seguintes informações de uma pesquisa na web:
        {search_content}

        Aqui está o histórico da conversa:
        {history}

        Com base nisso, responda de forma objetiva a pergunta do usuário:
        {query}
        """
    )
    chain = prompt | ChatOpenAI(temperature=0, model="gpt-4o-mini")
    resposta = chain.invoke({
        "search_content": search_content,
        "history": state["history"],
        "query": state["query"]
    }).content

    return {"resposta": resposta}

def route_query(state: State) -> str:
    """
    Roteia a consulta para o nó de resposta simples ou para o nó que faz pesquisa,
    com base na categoria definida na função 'categorize'.
    """
    if state["categoria"] == "simples":
        return "handle_technical"
    else:
        return "handle_web_search"

# ------------------------------------------------------------------------------------
# Construindo o fluxo (grafo)
# ------------------------------------------------------------------------------------
workflow = StateGraph(State)

# Adicionar nós
workflow.add_node("categorize", categorize)
workflow.add_node("handle_technical", handle_technical)
workflow.add_node("handle_web_search", handle_web_search)

# Adicionar transições condicionais
workflow.add_conditional_edges(
    "categorize",
    route_query,
    {
        "handle_technical": "handle_technical",
        "handle_web_search": "handle_web_search",
    }
)

# Encerrar o fluxo
workflow.add_edge("handle_technical", END)
workflow.add_edge("handle_web_search", END)

# Definir o ponto de entrada do fluxo
workflow.set_entry_point("categorize")

# Compilar o grafo
app = workflow.compile()

# (Opcional) Desenha a estrutura do grafo como imagem
app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.API,
)

# ------------------------------------------------------------------------------------
# Função para executar o fluxo de suporte ao cliente
# ------------------------------------------------------------------------------------
def executar_suporte_ao_cliente(consulta: str) -> Dict[str, str]:
    """
    Processa a consulta do cliente através do fluxo de trabalho LangGraph,
    repassando também o histórico de conversa.
    """
    # Formata o histórico para enviar no estado
    #history_str = format_history(st.session_state.messages)
    history_str = ""
    
    # Monta o dicionário de entrada para o fluxo
    input_data = {
        "query": consulta,
        "categoria": "",  # Inicialmente vazio (será definido no grafo)
        "resposta": "",   # Inicialmente vazio (será definido no grafo)
        "history": history_str
    }
    resultados = app.invoke(input_data)
    return {
        "categoria": resultados["categoria"],
        "resposta": resultados["resposta"]
    }


#########################################
# Servidor gRPC (assíncrono)           #
#########################################
class GenAiServiceServicer(genai_pb2_grpc.GenAiServiceServicer):
    async def AskQuestion(self, request, context):
        """
        Método gRPC que recebe a pergunta e retorna a resposta do Agente de forma assíncrona.
        """
        user_question = request.question

        # Moderação inicial
        if not await guard_moderation_async(user_question, bot=False):
            return genai_pb2.AnswerResponse(
                answer="Desculpe, sua pergunta contém conteúdo bloqueado."
            )
        try:
            response_text = executar_suporte_ao_cliente(user_question)
        except Exception as e:
            return genai_pb2.AnswerResponse(
                answer=f"Erro ao processar a solicitação: {str(e)}"
            )
        return genai_pb2.AnswerResponse(answer=response_text['resposta'])


async def serve():
    server = aio.server()
    genai_pb2_grpc.add_GenAiServiceServicer_to_server(
        GenAiServiceServicer(), server
    )
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    await server.start()
    print(f"Servidor gRPC (assíncrono) iniciado em {listen_addr}")
    # Mantém o servidor rodando até ser interrompido
    await server.wait_for_termination()
if __name__ == "__main__":
    asyncio.run(serve())
