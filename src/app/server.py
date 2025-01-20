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

# Inicializa a ferramenta de busca
duckduckgo = DuckDuckGoSearchRun()


# Inicializa a configuração do Rails
rails_config = RailsConfig.from_path("./config")
rails = LLMRails(rails_config)

# Função para usar o LLMRails sem `nest_asyncio`
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


########################
# Função de busca mock #
########################
def search_tool(query: str) -> str:
    """
    Executa uma busca usando DuckDuckGo de forma assíncrona
    e retorna até 10 resultados.
    """
    # 'duckduckgo.run(query)' é síncrono, então usamos 'asyncio.to_thread'
    results =  asyncio.to_thread(duckduckgo.run, query)

    # Se 'results' vier em formato de string com várias linhas,
    # você pode dividir por quebras de linha e limitar a 10
    lines = results.split('\n')[:10]

    # Caso queira juntar de volta em uma única string
    return "\n".join(lines)


search_tool_action = Tool(
    name="search_tool",
    func=search_tool,
    description="Ferramenta para buscar informações externas (máx 10 resultados)."
)

#######################################
# Cria o Agente Conversacional        #
#######################################
base_prompt = """
Você é um agente conversacional especializado em responder qualquer pergunta,
EXCETO sobre Engenharia Civil. Se for Engenharia Civil, recuse.
Se precisar de informações adicionais, use a ferramenta 'search_tool'.
Para assuntos atuais, use a ferramenta 'search_tool'.
"""

chat_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True  # para evitar erros com chat-conversational
)

conversational_agent = initialize_agent(
    tools=[search_tool_action],
    llm=chat_model,
    agent="chat-conversational-react-description",
    verbose=False,
    memory=memory,
)

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
            response_text = conversational_agent.invoke(user_question)
        except Exception as e:
            return genai_pb2.AnswerResponse(
                answer=f"Erro ao processar a solicitação: {str(e)}"
            )
        return genai_pb2.AnswerResponse(answer=response_text['output'])

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
