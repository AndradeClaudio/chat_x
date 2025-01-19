from curses import KEY_MESSAGE
from openai import OpenAI
from openai.types.beta import Assistant
from openai.types.beta import Thread
#from openai.types.beta.threads.thread_message import ThreadMessage
from openai.types.beta.threads.run import Run
from dotenv import load_dotenv
import os 
from typing import Any
import time
from authenticate import put_thread_key
from typing import Optional


class messageItem:
    """
    Represents a message item with role and content attributes.

    Attributes:
    - role (str): The role associated with the message item.
    - content (Union[str, Any]): The content of the message item, which can be a string or any other type of object.
    """
    def __init__(self,role,content:str| Any):
        self.role=role
        self.content:str=content
        print(role)



class OpenAi:
    """
    Class to interact with the OpenAI assistant service.
    """
    def checking_assistant(self):
        """
        Retrieves assistant details from the OpenAI service.

        Returns:
        - str: ID of the assistant.
        """
        self.checking=self.client.beta.assistants.retrieve(assistant_id="asst_FQmqADjiuIMmY5j9Ytn3YGge")
        return self.checking.id

    def checking_thread(self,thread_key):
        """
        Retrieves thread details based on the thread key.

        Args:
        - thread_key (str): The thread key to retrieve details.

        Returns:
        - Any: Details of the thread.
        """
        self.thread=self.client.beta.threads.retrieve(thread_id=f"{thread_key}")
        return self.thread

    def __init__(self,name:str,instruction:str,
thread_key: Optional[str],phonenumber,model:str="gpt-3.5-turbo") -> None:
        """
        Initializes the OpenAI class.

        Args:
        - name (str): Name of the AI.
        - instruction (str): Instructions for the AI.
        - thread_key (Optional[str]): Optional thread key.
        - phonenumber: The phone number associated with the AI.
        - model (str): The AI model to be used (default is 'gpt-3.5-turbo').
        """

        self.name=name
        self.instruction=instruction
        self.model:str=model
        load_dotenv()
        self.client:OpenAI=OpenAI(api_key=os.getenv("Basit_key"))
        self.assistant_id=self.checking_assistant()
        # self.assistant:Assistant=self.client.beta.assistants.create(
        #     name=self.name,
        #     instructions=self.instruction,
        #     tools=[{"type": "code_interpreter"}],
        #     model=self.model,
        # )

        # self.thread:Thread=self.client.beta.threads.create()
        try:
            self.thread=self.checking_thread(thread_key=thread_key)
        except:
            self.thread:Thread=self.client.beta.threads.create()
            inserted=put_thread_key(phonenumber=int(phonenumber),thread_key=f"'{self.thread.id}'")
            if not inserted:
                print("Failed to insert thread key into database.")
            

        self.messages:list[messageItem]=[]
        # self.previous_message=(self.client.beta.threads.messages.list(
        #     thread_id=self.thread.id
        # ))
        
        
    def send_message(self,message:str):
        """
        Sends a message within the conversation thread via the OpenAI service.

        Args:
        - message (str): The message to be sent.

        Returns:
        - str: Indicates the status of the message sending process (e.g., 'completed').
        """
        #lastest_message:ThreadMessage=self.client.beta.threads.messages.create(
        #        thread_id=self.thread.id,
        #        role="user",
        #        content=message
        #    )
        
        
        self.latest_run:Run=self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_id
        )

        self.addMessage(messageItem("user",message))
        return "completed"

    def isCompleted(self)->bool:
        """
        Checks if the latest interaction with the OpenAI service is completed.

        Returns:
        - bool: Returns True if the interaction is completed, else returns False.
        """
        
        while self.latest_run.status != "completed":
            print("Going to sleep")
            time.sleep(1)
            self.latest_run : Run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=self.latest_run.id
            )
            # print("Latest Status: ", self.latest_run.status)
        return True
    def get_latest_responce(self)->messageItem:
        latest_responce:Run=self.client.beta.threads.messages.list(
            thread_id=self.thread.id
        )
        print("Response: ", latest_responce.data[0].content[0].text.value)
        m = messageItem(latest_responce.data[0].role, latest_responce.data[0].content[0].text.value)
        self.addMessage(m)
        return m

    def get_name(self):
        return self.name

    def addMessage(self, message: messageItem)->None: 
        self.messages.append(message)

    def get_message(self)->messageItem:
        return self.messages
   
    # def get_thread(self):
    #     return self.thread.id
# def your_previous_message(key:str):
#     client2 = OpenAI(api_key=os.getenv("Basit_key"))
#     messages = client2.beta.threads.messages.list(thread_id=key)

#     messages_dict = {}
#     for message in reversed(messages.data):
#         role = message.role
#         content = message.content[0].text.value
#         messages_dict[role] = content
    
#     return messages_dict

def get_message_by_thread(thread_key:Optional[str]):
    if thread_key!=None:
       load_dotenv()
       client:OpenAI=OpenAI(api_key=os.getenv("Basit_key"))
       data_retreive=client.beta.threads.messages.list(
        thread_id=thread_key
       )
       t=[]
       for i in range(len(data_retreive.data)):   
           t.append({data_retreive.data[i].role:data_retreive.data[i].content[0].text.value})
           
       return t

        