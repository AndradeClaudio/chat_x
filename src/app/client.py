import asyncio
import grpc
from grpc import aio

import genai_pb2
import genai_pb2_grpc

async def main():
        async with aio.insecure_channel("localhost:50051") as channel:
            stub = genai_pb2_grpc.GenAiServiceStub(channel)
            user_question = "Qual a capital da França?"
            request = genai_pb2.QuestionRequest(question=user_question)
            # Faz chamada assíncrona ao servidor
            response = await stub.AskQuestion(request)
            print("Resposta do servidor:", response.answer)

if __name__ == "__main__":
    asyncio.run(main())
