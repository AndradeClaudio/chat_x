import asyncio
import grpc
from grpc import aio  # A API assíncrona do gRPC

import genai_pb2
import genai_pb2_grpc

# Imports LangChain
from langchain.agents import Tool, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory

#######################
# Mock de LlamaGuard  #
#######################
def llama_guard_moderation(content: str) -> bool:
    """
    Retorna True se conteúdo for permitido, False caso contrário.
    """
    blocked_words = ["ofensa", "palavrão", "terrorismo"]
    for bw in blocked_words:
        if bw in content.lower():
            return False
    return True

########################
# Função de busca mock #
########################
def search_tool(query: str) -> str:
    """
    Simula uma busca e retorna até 10 resultados (mock).
    """
    fake_results = [
        "Resultado 1 sobre o assunto...",
        "Resultado 2 sobre o assunto...",
        "Resultado 3 sobre o assunto..."
    ]
    results_limited = fake_results[:10]
    return "\n".join(results_limited)

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
        if not llama_guard_moderation(user_question):
            return genai_pb2.AnswerResponse(
                answer="Desculpe, sua pergunta contém conteúdo bloqueado."
            )

        # Bloqueio sobre Engenharia Civil
        if "engenharia civil" in user_question.lower():
            return genai_pb2.AnswerResponse(
                answer="Desculpe, não estou habilitado a falar sobre Engenharia Civil."
            )

        try:
            # No LangChain atual, a chamada .run() em si não é async.
            # Se você tiver um LLM ou ferramenta I/O-bound e um wrapper async, poderia usar await. 
            # Aqui seguimos com a chamada síncrona mas dentro de um método gRPC assíncrono.
            response_text = conversational_agent.run(user_question)
        except Exception as e:
            return genai_pb2.AnswerResponse(
                answer=f"Erro ao processar a solicitação: {str(e)}"
            )

        # Moderação da resposta
        if not llama_guard_moderation(response_text):
            return genai_pb2.AnswerResponse(
                answer="Desculpe, a resposta contém conteúdo bloqueado."
            )

        return genai_pb2.AnswerResponse(answer=response_text)


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
