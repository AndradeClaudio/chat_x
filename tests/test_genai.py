import pytest
import asyncio
from grpc import aio
# Imports gerados do protobuf
from src.app import genai_pb2
from src.app import genai_pb2_grpc

# Precisamos importar a função ou classe que inicia o servidor
# por exemplo, serve() que criamos em server.py.
# Vamos supor que chamamos `async def serve_test()` para ambiente de teste.
from src.app.server import serve, GenAiServiceServicer

@pytest.fixture(scope="session")
def event_loop():
    """
    Pytest por padrão cria um event_loop function-level.
    Para testes assíncronos de todo o módulo, usamos esse session-level.
    """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()
@pytest.fixture(scope="module")
async def grpc_server() -> asyncio.Generator[str, asyncio.Any, None]:

    server = aio.server()

    genai_pb2_grpc.add_GenAiServiceServicer_to_server(
        GenAiServiceServicer(), server
    )

    port = 50055
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)

    await server.start()
    print(f"[TEST] Servidor gRPC de teste iniciado em {listen_addr}")

    # IMPORTANTE: aqui retornamos a string do endereço que o teste vai usar
    yield f"localhost:{port}"

    await server.stop(0)
    print("[TEST] Servidor gRPC encerrado.")


@pytest.mark.asyncio
async def test_simple_question(grpc_server):
    async with aio.insecure_channel(grpc_server) as channel:
        stub = genai_pb2_grpc.GenAiServiceStub(channel)

        request = genai_pb2.QuestionRequest(question="Qual a capital da França?")
        response = await stub.AskQuestion(request)
        
        # Valida que existe 'Paris' na resposta
        assert "Paris" in response.answer

@pytest.mark.asyncio
async def test_engineering_block(grpc_server):
    """
    Verifica se o servidor bloqueia questões sobre Engenharia Civil.
    """
    async with aio.insecure_channel(grpc_server) as channel:
        stub = genai_pb2_grpc.GenAiServiceStub(channel)

        request = genai_pb2.QuestionRequest(question="Me fale sobre Engenharia Civil")
        response = await stub.AskQuestion(request)

        assert "não estou habilitado" in response.answer.lower(), \
            f"Esperado bloqueio sobre Engenharia Civil, mas resposta foi: {response.answer}"

@pytest.mark.asyncio
async def test_moderation_block(grpc_server):
    """
    Verifica se o mock de LlamaGuard bloqueia perguntas ofensivas.
    """
    async with aio.insecure_channel(grpc_server) as channel:
        stub = genai_pb2_grpc.GenAiServiceStub(channel)

        # 'palavrão' está na lista de bloqueio
        request = genai_pb2.QuestionRequest(question="Isso é um palavrão?")
        response = await stub.AskQuestion(request)

        assert "contém conteúdo bloqueado" in response.answer.lower(), \
            f"Esperado bloqueio por moderação, mas resposta foi: {response.answer}"

@pytest.mark.asyncio
async def test_needs_search_tool(grpc_server):
    """
    Verifica se o Agente possivelmente usa a ferramenta de busca quando a pergunta é
    mais complexa ou demanda dados externos. (No mock, não temos logs automáticos,
    mas podemos ao menos checar se a resposta faz menção aos 'fake_results'.)
    """
    async with aio.insecure_channel(grpc_server) as channel:
        stub = genai_pb2_grpc.GenAiServiceStub(channel)

        request = genai_pb2.QuestionRequest(question="Qual foi o último resultado do campeonato brasileiro?")
        response = await stub.AskQuestion(request)

        # Dependendo do LLM/prompt, a resposta mock pode incluir "Resultado 1 sobre o assunto..."
        assert "Resultado 1" in response.answer or "resultado 1" in response.answer.lower(), \
            f"Esperado alguma menção aos 'fake_results', mas resposta foi: {response.answer}"
