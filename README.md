# Projeto Chat X

Este projeto é um aplicativo de chat que utiliza várias tecnologias e bibliotecas para fornecer funcionalidades avançadas de moderação e busca na web.
# Algumas explicação. 

- Foi adotado o protocolo de comunicação gRPC em vez de API REST, pois ele oferece melhor latência na comunicação entre servidores.
- A escolha pelo NanoGuardRails foi feita em detrimento do LlamaGuard devido ao menor custo de implementação.
- O ideal seria que o servidor e o cliente estivessem em imagens separadas. Contudo, essa separação não foi implementada devido à limitação de tempo.
- A biblioteca duckduckgo_search foi utilizada por ser gratuita, evitando custos adicionais de implementação.
- A opção pelo serviço da Azure foi motivada pela agilidade no provisionamento de equipamentos, essencial dado o prazo reduzido.
- Foi utilizada uma instância spot devido ao menor custo; no entanto, essa escolha não é recomendada para ambientes de produção.
- O arquivo server.py é responsável por toda a comunicação com o chat (backend).
- O arquivo main.py é encarregado de orquestrar a entrada e saída de dados (frontend).
- O pacote UV foi utilizado para organizar a estrutura do projeto.
- Foi iniciada a implementação de uma rotina de testes. Contudo, o número de testes ainda é limitado devido à restrição de tempo.
- Gestão dos tokens pelo LangSmith. 

## Estrutura do Projeto

```txt
.
├── Dockerfile
├── README.md
├── app.log
├── config
│   ├── config.yml
│   ├── prompts.yml
│   └── rails
│       ├── blocked_terms.co
│       ├── disallowed_topics.co
│       ├── greetings.co
│       └── input_output_checks.co
├── database.db
├── estrutura.txt
├── logs
│   └── chat_app.log
├── pyproject.toml
├── pytest.ini
├── src
│   └── app
│       ├── auth.py
│       ├── authenticate.py
│       ├── chat.py
│       ├── client.py
│       ├── genai.proto
│       ├── genai_pb2.py
│       ├── genai_pb2_grpc.py
│       ├── main.py
│       ├── message_handler.py
│       ├── server.py
│       └── utils.py
├── start.sh
├── tests
│   └── test_route_query.py
└── uv.lock
.streamlit
└── config.toml
.vscode
└── launch.json
