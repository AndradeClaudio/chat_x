## Importar bibliotecas necessárias
from typing import Dict, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

#from IPython.display import display, Image
from langchain_core.runnables.graph import MermaidDrawMethod
from dotenv import load_dotenv
import streamlit as st
from nemoguardrails import RailsConfig, LLMRails
import nest_asyncio

nest_asyncio.apply()
rails_config = RailsConfig.from_path("./config")
rails = LLMRails(rails_config)

# Defina o favicon
st.set_page_config(
    page_title="Clinica VitaSlim",
    page_icon="hospital",  # Caminho do ícone
)
# Carregar variáveis de ambiente e definir a chave da API OpenAI
load_dotenv()

class State(TypedDict):
    query: str
    categoria: str
    sentimento: str
    resposta: str
    valid_input: bool
    
def categorize(state: State) -> State:
    """Categoriza a consulta do cliente em Técnica, Faturamento ou Geral."""
    prompt = ChatPromptTemplate.from_template(
    """Analise a categoria da consulta do cliente: 
        "Responda apenas com umas das opções:'Técnica', 'Faturamento', 'Funcionamento','Especialidades','Empresa','Médico' ou 'Geral'. 
        Consulta: {query}"""
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    categoria = chain.invoke({"query": state["query"]}).content
    return {"categoria": categoria}

def guardrails_input_handler(consulta: str, bot: bool) -> Dict[bool, str]:
        """Handles guardrails on the user input.
        Args:
        - user_input: str the user input to be checked by guardrails
        """
        tipo = "bot" if bot else "user"
        #self.logger.info("Checking guardrails on user input")
        response = rails.generate(
            messages=[
                {
                    "role": tipo,
                    "content": consulta,
                }
            ]
        )
        info = rails.explain()
        if "bot refuse" in info.colang_history:
            #self.logger.info(f"Guardrails refused the input. Colang history:\n{info.colang_history}")
            return {"valid_input": False, "messages": response.get("content")}
        else:
            #self.logger.info(f"Guardrails accepted the input.")
            return {"valid_input": True}


def analyze_sentiment(state: State) -> State:
    """Analisa o sentimento da consulta do cliente como Positivo, Neutro ou Negativo."""
    prompt = ChatPromptTemplate.from_template(
        "Analise o sentimento da seguinte consulta do cliente. "
        "Responda com 'Positivo', 'Neutro' ou 'Negativo'. Consulta: {query}"
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    sentimento = chain.invoke({"query": state["query"]}).content
    return {"sentimento": sentimento}

def handle_technical(state: State) -> State:
    """Fornece uma resposta de suporte técnico para a consulta."""
    prompt = ChatPromptTemplate.from_template(
        "Forneça uma resposta de suporte técnico para a seguinte consulta: {query}"
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    resposta = chain.invoke({"query": state["query"]}).content
    return {"resposta": resposta}

def handle_billing(state: State) -> State:
    """Fornece uma resposta de suporte de faturamento para a consulta."""
    prompt = ChatPromptTemplate.from_template(
        "Forneça uma resposta de suporte de faturamento para a seguinte consulta: {query}"
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    resposta = chain.invoke({"query": state["query"]}).content
    return {"resposta": resposta}

def handle_general(state: State) -> State:
    """Fornece uma resposta de suporte geral para a consulta."""
    prompt = ChatPromptTemplate.from_template(
        "Responda que não poderá ajudar, pois não tem conhecimento sobre assunto. Somente sobre a Clínica VitaSlim"
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    resposta = chain.invoke({"query": state["query"]}).content
    return {"resposta": resposta}
def handle_operation(state: State) -> State:
    """Fornece uma resposta de suporte geral para a consulta."""
    return {"resposta": 
            """
            Olá!
                Obrigado por entrar em contato. Nossos horários de funcionamento são os seguintes:
                Segunda a Quinta: das 9h às 20h
                Sexta-Feira, Sábado e Domingo: Fechado
                Se precisar de mais informações ou tiver alguma outra dúvida, fique à vontade para perguntar!
                Atenciosamente,
            """}
def handle_business(state: State) -> State:
    """Fornece uma resposta de suporte geral para a consulta."""
    prompt = ChatPromptTemplate.from_template(
        """A Clínica Médica VitaSlim é um centro de referência no tratamento e acompanhamento do processo de emagrecimento saudável. 
            Nossa missão é promover o bem-estar integral dos nossos pacientes, aliando ciência, tecnologia e humanização no cuidado com a saúde. 
            Acreditamos que o emagrecimento eficaz é aquele que respeita o ritmo de cada pessoa, envolvendo reeducação alimentar, acompanhamento psicológico 
            e o suporte de uma equipe médica altamente qualificada. 
            Localizada em um ambiente moderno e confortável, a VitaSlim oferece programas personalizados
            , sempre visando o equilíbrio entre corpo e mente.
            Forneça uma resposta sobre a empresa para a seguinte consulta: {query}
        """
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    resposta = chain.invoke({"query": state["query"]}).content
    return {"resposta": resposta}
def handle_specialist(state: State) -> State:
    """Fornece uma resposta de suporte geral para a consulta."""
    prompt = ChatPromptTemplate.from_template(
        """Especialidades
A clínica abrange uma abordagem multidisciplinar, com o objetivo de oferecer um plano de emagrecimento completo e eficaz. As especialidades disponíveis incluem:

Endocrinologia
Monitoramento de doenças metabólicas e hormonais que afetam o peso e o bem-estar, com tratamentos individualizados para distúrbios como obesidade, diabetes e disfunções hormonais.

Nutrição
Desenvolvimento de planos alimentares personalizados, baseados em análise corporal e necessidades nutricionais, com foco em reeducação alimentar, melhora metabólica e sustentação do emagrecimento a longo prazo.

Psicologia
Acompanhamento psicológico para entender os fatores emocionais e comportamentais envolvidos no processo de emagrecimento, promovendo mudanças de hábitos e fortalecimento emocional.

Medicina Esportiva
Prescrição de exercícios físicos adequados à condição física de cada paciente, com foco em aumento da massa muscular, perda de gordura corporal e melhoria da qualidade de vida.

Cirurgia Bariátrica
Para casos em que o emagrecimento clínico não alcança os resultados esperados, oferecemos acompanhamento completo para o processo de cirurgia bariátrica, desde a preparação pré-operatória até o pós-operatório.

Estética Médica
Tratamentos estéticos como drenagem linfática, radiofrequência e criolipólise, para auxiliar na redução de gordura localizada e melhorar a autoestima dos pacientes durante o processo de emagrecimento.
            Forneça uma resposta sobre a empresa para a seguinte consulta: {query}
        """
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    resposta = chain.invoke({"query": state["query"]}).content
    return {"resposta": resposta}
def handle_doctors(state: State) -> State:
    """Fornece uma resposta de suporte geral para a consulta."""
    prompt = ChatPromptTemplate.from_template(
        """Equipe Médica
        Dra. Carolina Almeida
        Endocrinologista

        Formação: Graduada em Medicina pela Universidade de São Paulo (USP), com Residência em Endocrinologia no Hospital das Clínicas da USP.
        Currículo: Dra. Carolina possui mais de 15 anos de experiência no tratamento de doenças metabólicas e hormonais. Atua com foco no emagrecimento saudável, tratamento da obesidade, diabetes e distúrbios da tireoide. Já participou de congressos internacionais de Endocrinologia e realiza atendimentos focados em terapias individualizadas, sempre considerando o equilíbrio hormonal como chave para o sucesso no emagrecimento.
        Dr. Felipe Antunes
        Médico Esportivo

        Formação: Graduado em Medicina pela Universidade Federal do Rio de Janeiro (UFRJ), com especialização em Medicina Esportiva pela Universidade de Barcelona.
        Currículo: Com mais de 10 anos de experiência, Dr. Felipe é especialista na prescrição de atividades físicas para pacientes com diferentes perfis, incluindo aqueles que buscam emagrecimento. Além de realizar avaliações físicas detalhadas, ele acompanha atletas e pessoas que desejam melhorar o condicionamento físico de maneira saudável e segura. Seu foco é integrar exercícios com a saúde metabólica.
        Dra. Mariana Ribeiro
        Nutricionista Clínica Funcional

        Formação: Graduada em Nutrição pela Universidade Estadual de Campinas (UNICAMP), com pós-graduação em Nutrição Funcional pela VP Centro de Nutrição Funcional.
        Currículo: Dra. Mariana é especialista em nutrição para emagrecimento e bem-estar. Seu método envolve uma abordagem funcional e personalizada, onde os alimentos são usados como ferramentas para reequilibrar o metabolismo, melhorar a qualidade de vida e promover a perda de peso de forma sustentável. Atua com foco em reeducação alimentar, intolerâncias alimentares e nutrição preventiva.
        Dr. Gustavo Vasconcelos
        Cirurgião Bariátrico

        Formação: Graduado em Medicina pela Universidade Federal de Minas Gerais (UFMG), com especialização em Cirurgia Bariátrica e Metabólica pelo Hospital Alemão Oswaldo Cruz.
        Currículo: Com mais de 12 anos de experiência em cirurgias metabólicas, Dr. Gustavo é um dos principais especialistas em cirurgia bariátrica no Brasil. Participou de mais de 500 procedimentos bariátricos e segue protocolos de segurança reconhecidos mundialmente. Ele também oferece acompanhamento pós-operatório completo, incluindo a reeducação alimentar e suporte emocional.
        Dra. Patrícia Moraes
        Psicóloga Clínica

        Formação: Graduada em Psicologia pela Pontifícia Universidade Católica de São Paulo (PUC-SP), com especialização em Psicologia Comportamental pelo Instituto de Psiquiatria da USP.
        Currículo: Dra. Patrícia é especialista em Transtornos Alimentares e possui mais de 8 anos de experiência no acompanhamento psicológico de pacientes em processos de emagrecimento. Ela trabalha com terapias cognitivas-comportamentais para ajudar pacientes a lidarem com a ansiedade, compulsão alimentar e questões emocionais que impactam o peso e a saúde.
            Forneça uma resposta sobre a empresa para a seguinte consulta: {query}
        """
    )
    chain = prompt | ChatOpenAI(temperature=0,model='gpt-4o-mini')
    resposta = chain.invoke({"query": state["query"]}).content
    return {"resposta": resposta}
def escalate(state: State) -> State:
    """Escala a consulta para um agente humano devido ao sentimento negativo."""
    return {"resposta": "Esta consulta foi escalada para um agente humano devido ao seu sentimento negativo."}


def route_query(state: State) -> str:
    """Roteia a consulta com base em seu sentimento e categoria."""
    if state["sentimento"] == "Negativo":
        return "escalate"
    elif state["categoria"] == "Técnica":
        return "handle_technical"
    elif state["categoria"] == "Faturamento":
        return "handle_billing"
    elif state["categoria"] == "Funcionamento":
        return "handle_operation"
    elif state["categoria"] == "Empresa":
        return "handle_business"
    elif state["categoria"] == "Especialidades":
        return "handle_specialist"
    elif state["categoria"] == "Médico":
        return "handle_doctors"
    else:
        return "handle_general"

# Criar o grafo
workflow = StateGraph(State)

# Adicionar nós
workflow.add_node("categorize", categorize)
workflow.add_node("analyze_sentiment", analyze_sentiment)
workflow.add_node("handle_technical", handle_technical)
workflow.add_node("handle_billing", handle_billing)
workflow.add_node("handle_general", handle_general)
workflow.add_node("handle_operation", handle_operation)
workflow.add_node("handle_business", handle_business)
workflow.add_node("handle_specialist",handle_specialist)
workflow.add_node("handle_doctors",handle_doctors)
workflow.add_node("escalate", escalate)

# Adicionar arestas
workflow.add_edge("categorize", "analyze_sentiment")
workflow.add_conditional_edges(
    "analyze_sentiment",
    route_query,
    {
        "handle_technical": "handle_technical",
        "handle_billing": "handle_billing",
        "handle_general": "handle_general",
        "handle_operation": "handle_operation",
        "handle_business": "handle_business",
        "handle_specialist": "handle_specialist",
        "handle_doctors":"handle_doctors",
        "escalate": "escalate"
    }
)
workflow.add_edge("handle_technical", END)
workflow.add_edge("handle_billing", END)
workflow.add_edge("handle_general", END)
workflow.add_edge("handle_operation", END)
workflow.add_edge("handle_business", END)
workflow.add_edge("handle_specialist", END)
workflow.add_edge("handle_doctors", END)
workflow.add_edge("escalate", END)

# Definir ponto de entrada
workflow.set_entry_point("categorize")

# Compilar o grafo
app = workflow.compile()
def executar_suporte_ao_cliente(consulta: str) -> Dict[str, str]:
    """Processa uma consulta do cliente através do fluxo de trabalho LangGraph.

    Args:
        consulta (str): A consulta do cliente

    Returns:
        Dict[str, str]: Um dicionário contendo a categoria, o sentimento e a resposta da consulta
    """
    guardrail = guardrails_input_handler(consulta,False)
    if guardrail['valid_input']:
        resultados = app.invoke({"query": consulta})
        guardrail = guardrails_input_handler(resultados["resposta"],False)
        if guardrail['valid_input']:
            return {
                "categoria": resultados["categoria"],
                "sentimento": resultados["sentimento"],
                "resposta": resultados["resposta"]
            }
        else:
            return {
                "categoria": "guadrail",
                "sentimento": "negativo",
                "resposta": guardrail['messages']
            }        
    else:
        return {
            "categoria": "guadrail",
            "sentimento": "negativo",
            "resposta": guardrail['messages']
        }
app.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )

# Testes

USER_AVATAR = "🧑‍⚕️"
BOT_AVATAR = "🩺"

st.title("🏥 Clínica VitaSlim - Suporte")
load_dotenv()
# Initialize or load chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])  
if consulta := st.chat_input("Como posso te ajudar?"):
    st.session_state.messages.append({"role": "user", "content": consulta})
    if "typing_message" not in st.session_state:
        st.session_state["typing_message"] = "Digitando..."
    # Inicia a thread de simulação de digitação
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(consulta)
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        full_response = ""
        with st.spinner('Processando...'):
            resultado = executar_suporte_ao_cliente(consulta)
        message_placeholder.markdown(f"{resultado['resposta']}")
        #message_placeholder.markdown(f"{resultado['resposta']}")
        st.session_state.messages.append({"role": "assistant", "content": f"{resultado['resposta']}"})
