import asyncio
import logging
from typing import Dict, TypedDict

from dotenv import load_dotenv
from duckduckgo_search import DDGS
from grpc import aio  # API assíncrona do gRPC
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.graph import MermaidDrawMethod
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from nemoguardrails import RailsConfig, LLMRails

import genai_pb2
import genai_pb2_grpc

# =============================================================================
# Configuração de Logging
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Carrega variáveis de ambiente
# =============================================================================
load_dotenv()

# =============================================================================
# Configuração do Nemo Guardrails
# =============================================================================
rails_config = RailsConfig.from_path("./config")
rails = LLMRails(rails_config)


# =============================================================================
# Funções de moderação (Guardrails)
# =============================================================================
async def guard_moderation_async(consulta: str, bot: bool) -> bool:
    """
    Realiza a verificação de moderação de conteúdo de forma assíncrona.

    Args:
        consulta (str): Conteúdo a ser analisado.
        bot (bool): Indica se a origem da mensagem é do bot ou do usuário.

    Returns:
        bool: True se a mensagem for aprovada; False caso contrário.
    """
    logger.info(
        "Iniciando moderação (assíncrona). Tipo: %s, Conteúdo: %.50s",
        "bot" if bot else "user",
        consulta.replace("\n", " ")[:50],
    )

    tipo = "bot" if bot else "user"

    await rails.generate_async(
        messages=[
            {
                "role": tipo,
                "content": consulta,
            }
        ]
    )
    info = rails.explain()
    if "bot refuse" in info.colang_history:
        logger.warning("Conteúdo bloqueado pela moderação.")
        return False

    logger.info("Conteúdo aprovado pela moderação.")
    return True


def guard_moderation(consulta: str, bot: bool) -> bool:
    """
    Função síncrona de moderação de conteúdo, útil para ambientes que não suportam
    async/await diretamente.

    Args:
        consulta (str): Conteúdo a ser analisado.
        bot (bool): Indica se a origem da mensagem é do bot ou do usuário.

    Returns:
        bool: True se a mensagem for aprovada; False caso contrário.
    """
    logger.info("Iniciando moderação (síncrona).")
    return asyncio.run(guard_moderation_async(consulta, bot))


# =============================================================================
# Definição do estado do fluxo (grafo)
# =============================================================================
class State(TypedDict):
    query: str
    categoria: str
    resposta: str
    history: str


# =============================================================================
# Funções utilitárias
# =============================================================================
def web_search(query: str) -> str:
    """
    Obtém informações gerais usando DuckDuckGo.

    Args:
        query (str): Termo de pesquisa.

    Returns:
        str: Texto contendo títulos, trechos e URLs dos resultados da busca.
    """
    logger.info("Iniciando pesquisa na web para a query: %s", query)
    try:
        results = DDGS().text(query, max_results=10)
    except Exception as e:
        logger.error("Falha ao realizar a pesquisa na web: %s", str(e))
        # Re-levanta a exceção para que o fluxo principal possa tratar
        raise

    contexts = "\n---\n".join(
        [
            "\n".join([item["title"], item["body"], item["href"]])
            for item in results
        ]
    )
    logger.info("Pesquisa na web concluída, %d resultados retornados.", len(results))
    return contexts


# =============================================================================
# Funções de nós (para o fluxo da LangGraph)
# =============================================================================
def categorize(state: State) -> State:
    """
    Categoriza a consulta em 'simples' ou 'complexa'.

    - 'complexa' sempre que a consulta for relacionada a datas recentes (2 anos),
      perguntas de tempo (dia, hora, mês, ano) ou temas que exijam pesquisa mais profunda.
    - Caso contrário, 'simples'.

    Args:
        state (State): Dicionário que contém os dados atuais do fluxo.

    Returns:
        State: Dicionário contendo 'categoria' como 'simples' ou 'complexa'.
    """
    logger.debug("Iniciando categorização. Consulta: %s", state["query"])
    prompt = ChatPromptTemplate.from_template(
        """
        Você deve analisar a seguinte conversa (histórico) e a última pergunta 
        do usuário para decidir se a consulta é 'simples' ou 'complexa'.

        Histórico da conversa:
        {history}

        Última consulta do usuário:
        {query}

        Instrução:
        - Sempre que for relacionada a ‘dia’, ‘hora’, ‘mês’, ‘ano’, ou termos relacionados a tempo, 
          responda "complexa".
        - Se for uma pergunta relacionada aos últimos 2 anos, responda "complexa".
        - Se for um tema complexo, responda "complexa".
        - Se for uma simples conversa informal, responda "simples".
        - Responda APENAS com 'simples' ou 'complexa'.
        """
    )
    chain = prompt | ChatOpenAI(temperature=0, model="gpt-4o-mini")
    categoria = chain.invoke(
        {
            "history": state["history"],
            "query": state["query"]
        }
    ).content.strip().lower()

    logger.debug("Categoria definida como: %s", categoria)
    return {"categoria": categoria}


def handle_technical(state: State) -> State:
    """
    Fornece uma resposta para consultas 'simples', considerando o histórico.

    Args:
        state (State): Dicionário com dados do estado, incluindo histórico e consulta.

    Returns:
        State: Dicionário contendo a resposta gerada.
    """
    logger.debug("Iniciando manuseio 'simples'. Consulta: %s", state["query"])
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
    resposta = chain.invoke(
        {
            "history": state["history"],
            "query": state["query"]
        }
    ).content
    logger.debug("Resposta (simples) gerada com sucesso.")
    return {"resposta": resposta}


def handle_web_search(state: State) -> State:
    """
    Node responsável por buscar informações na web e gerar uma resposta usando o LLM
    para questões consideradas 'complexas'.

    Args:
        state (State): Dicionário com dados do estado, incluindo histórico e consulta.

    Returns:
        State: Dicionário contendo a resposta gerada.
    """
    logger.debug("Iniciando manuseio 'complexo'. Consulta: %s", state["query"])
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
    resposta = chain.invoke(
        {
            "search_content": search_content,
            "history": state["history"],
            "query": state["query"]
        }
    ).content
    logger.debug("Resposta (complexa) gerada com sucesso.")
    return {"resposta": resposta}


def route_query(state: State) -> str:
    """
    Roteia a consulta para o nó de resposta simples ou para o nó que faz pesquisa,
    com base na categoria definida na função 'categorize'.

    Args:
        state (State): Estado que contém 'categoria'.

    Returns:
        str: Nome do próximo nó no fluxo.
    """
    logger.debug("Roteando consulta. Categoria: %s", state["categoria"])
    if state["categoria"] == "simples":
        return "handle_technical"
    return "handle_web_search"


# =============================================================================
# Construção do fluxo (StateGraph)
# =============================================================================
workflow = StateGraph(State)

# Adiciona nós
workflow.add_node("categorize", categorize)
workflow.add_node("handle_technical", handle_technical)
workflow.add_node("handle_web_search", handle_web_search)

# Adiciona transições condicionais
workflow.add_conditional_edges(
    "categorize",
    route_query,
    {
        "handle_technical": "handle_technical",
        "handle_web_search": "handle_web_search",
    },
)

# Encerrar o fluxo
workflow.add_edge("handle_technical", END)
workflow.add_edge("handle_web_search", END)

# Define ponto de entrada
workflow.set_entry_point("categorize")

# Compila o grafo
app = workflow.compile()

# (Opcional) Desenha a estrutura do grafo como imagem
app.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)


# =============================================================================
# Função de execução do suporte ao cliente
# =============================================================================
def executar_suporte_ao_cliente(consulta: str) -> Dict[str, str]:
    """
    Processa a consulta do cliente através do fluxo de trabalho LangGraph.

    Args:
        consulta (str): Consulta realizada pelo usuário.

    Returns:
        Dict[str, str]: Dicionário contendo a categoria e a resposta final.
    """
    logger.info("Executando fluxo de suporte ao cliente para consulta: %.50s",
                consulta.replace("\n", " ")[:50])

    history_str = ""  # Pode ser preenchido com um histórico real, se disponível
    input_data = {
        "query": consulta,
        "categoria": "",
        "resposta": "",
        "history": history_str,
    }

    resultados = app.invoke(input_data)
    logger.info(
        "Fluxo concluído. Categoria: %s, Resposta: %.50s",
        resultados["categoria"],
        resultados["resposta"].replace("\n", " ")[:50]
    )

    return {
        "categoria": resultados["categoria"],
        "resposta": resultados["resposta"],
    }


# =============================================================================
# Classe do Servidor gRPC
# =============================================================================
class GenAiServiceServicer(genai_pb2_grpc.GenAiServiceServicer):
    """
    Classe que implementa o serviço gRPC para processamento de perguntas via LLMs.
    """

    async def AskQuestion(self, request, context):
        """
        Método gRPC que recebe a pergunta e retorna a resposta do Agente de forma assíncrona.

        Args:
            request (genai_pb2.QuestionRequest): Objeto contendo a pergunta do usuário.
            context (grpc.aio.ServicerContext): Contexto de execução do gRPC.

        Returns:
            genai_pb2.AnswerResponse: Resposta a ser enviada ao cliente.
        """
        user_question = request.question
        logger.info("Recebida pergunta via gRPC: %s", user_question)

        # Moderação inicial
        if not await guard_moderation_async(user_question, bot=False):
            logger.warning("Pergunta bloqueada pela moderação.")
            return genai_pb2.AnswerResponse(
                answer="Desculpe, sua pergunta contém conteúdo bloqueado."
            )

        try:
            response_text = executar_suporte_ao_cliente(user_question)
            resposta_final = response_text["resposta"]
        except Exception as e:
            logger.error("Erro ao processar a solicitação: %s", str(e))
            resposta_final = f"Erro ao processar a solicitação: {str(e)}"

        logger.info("Resposta final enviada ao cliente: %.50s",
                    resposta_final.replace("\n", " ")[:50])
        return genai_pb2.AnswerResponse(answer=resposta_final)


# =============================================================================
# Função principal de execução do servidor
# =============================================================================
async def serve() -> None:
    """
    Inicializa e executa o servidor gRPC de forma assíncrona, 
    lidando com Ctrl+C e interrompendo o loop corretamente.
    """
    server = aio.server()
    genai_pb2_grpc.add_GenAiServiceServicer_to_server(
        GenAiServiceServicer(), server
    )

    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)

    logger.info("Servidor configurado para escutar em %s", listen_addr)

    try:
        # Inicia o servidor
        await server.start()
        logger.info("Servidor iniciado com sucesso em %s", listen_addr)

        # Aguarda até que o servidor seja encerrado (p. ex., sinal de interrupção)
        await server.wait_for_termination()

    except asyncio.CancelledError:
        # Captura quando o loop do asyncio foi cancelado (por ex. Ctrl+C)
        logger.info("Serviço gRPC cancelado. Iniciando desligamento...")

    except OSError as e:
        logger.error("Falha ao iniciar o servidor: %s", str(e))
        raise

    except Exception as e:
        logger.error("Erro inesperado na execução do servidor: %s", str(e))
        raise

    finally:
        logger.info("Desligando servidor gRPC...")
        try:
            # Protege a chamada de shutdown contra cancelamentos
            await asyncio.shield(server.stop(grace=5))
            logger.info("Servidor gRPC desligado com sucesso.")
        except asyncio.CancelledError:
            logger.warning("Shutdown interrompido novamente (Ctrl+C duplo?).")
            # Não re-levanta para evitar traceback


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Interrupção manual do servidor (KeyboardInterrupt).")
