import streamlit as st 

from authenticate import authenticate_user,get_thread_key,input_data,put_thread_key,get_data,get_limit_message,set_initial_limit,update_limit_counter
import time
from typing import Optional
import asyncio
import grpc
from grpc import aio
import genai_pb2
import genai_pb2_grpc

USER_AVATAR = "🧑‍⚕️"
BOT_AVATAR = "🩺"

# Authentication logic
def format_messages(messages:Optional[list]):
    try:
        formatted_messages = []
        for message in messages:
            role = list(message.keys())[0]
            content = message[role]
            formatted_messages.append((role, content))
        return formatted_messages
    except:
        return "No History Found"

async def question(user_question):
    async with aio.insecure_channel("localhost:50051") as channel:
        stub = genai_pb2_grpc.GenAiServiceStub(channel)
        request = genai_pb2.QuestionRequest(question=user_question)
        # Faz chamada assíncrona ao servidor
        response = await stub.AskQuestion(request)
        return {"resposta": response.answer}
        
st.title("Chat X - Onde podemos conversar de Quase Tudo ")
st.sidebar.title("Chat X ")
st.sidebar.markdown("---")
st.sidebar.header("Você é novo por aqui?")
asking=st.sidebar.radio("Usuário: ",["Use seu e-mail de registro","Novo Usuário"])

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

if not st.session_state.is_logged_in:
    if asking == "Novo Usuário":
        useremail:str = st.sidebar.text_input("Digite seu e-mail")
        if st.sidebar.button("Login"):
            if useremail:
                try:
                    is_registered = get_data(useremail=useremail)
                    if not is_registered:  # If not registered, proceed with registration
                        data_inserted = input_data(useremail=useremail)
                        if data_inserted:
                            st.sidebar.success("Successfully registered!")
                            set_initial_limit(useremail=useremail)
                            key=None
                            st.session_state.is_logged_in = True
                            st.session_state.authentic = True
                        else:
                            st.sidebar.write("Already registered")
                    else:
                        st.sidebar.error("Already Registered")
                        st.sidebar.write("Try Another Code Digit")
                except:
                    st.sidebar.error("An error occurred. Please try again.")
    else:
        pass 
if not st.session_state.is_logged_in and asking=="Use seu e-mail de registro":
    useremail = st.sidebar.text_input("Enter useremail")
    if st.sidebar.button("Login"):
        if authenticate_user(useremail=useremail):
            st.sidebar.success("Login successful!")
            key=get_thread_key(useremail=useremail)
            # OpenAi.get_thread()
            st.session_state.is_logged_in = True
            st.session_state.authentic = True  # Set authenticated state
        else:
            st.sidebar.error("Invalid credentials. Please try again.")
if st.session_state.is_logged_in==True:
    st.sidebar.empty() 
    if "useremail" not in st.session_state:
        st.session_state.useremail=useremail
    if "thread_key" not in st.session_state:
        st.session_state.thread_key=key
    st.sidebar.text("Usuário"+ st.session_state.useremail)
    counter,value=get_limit_message(st.session_state.useremail)
    st.sidebar.text(f"Sua cota de prompt é: {20-value}")
    messages = []
    formatted_messages = format_messages(messages)
    with st.sidebar.expander("See History"):
        try:
            for role, content in formatted_messages:
                if role == "user":
                    with st.container():
                        st.markdown(f":bust_in_silhouette: **User:** {content}")
                else:
                    with st.container():
                        st.markdown(f":robot_face: **AI:** {content}")
        except:
            with st.container():
               st.write("No History Found")
    if st.session_state.is_logged_in:
        counter,value=get_limit_message(st.session_state.useremail)
        if counter and value < 20: 
            if "messages" not in st.session_state:
                st.session_state.messages = []
            for message in st.session_state.messages:
                avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])  
            if user_question := st.chat_input("Como posso te ajudar?"):
                st.session_state.messages.append({"role": "user", "content": user_question})
                if "typing_message" not in st.session_state:
                    st.session_state["typing_message"] = "Digitando..."
                with st.chat_message("user", avatar=USER_AVATAR):
                    st.markdown(user_question)
                with st.chat_message("assistant", avatar=BOT_AVATAR):
                    message_placeholder = st.empty()
                    full_response = ""
                    with st.spinner('Processando...'):
                        resultado = asyncio.run(question(user_question))
                    message_placeholder.markdown(f"{resultado['resposta']}")
                    update_limit_counter(st.session_state.phone,value+1)
                    st.session_state.messages.append({"role": "assistant", "content": f"{resultado['resposta']}"})
        else:
            st.error("You have reached the limit of text-based communication today.")
