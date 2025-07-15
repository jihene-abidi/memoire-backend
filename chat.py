
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory # Permet de garder l’historique de la conversation.
from langchain.chains import ConversationChain # Permet de simuler une discussion fluide.
from langchain.schema import SystemMessage, AIMessage
from langchain.schema import HumanMessage
import json
import fitz # pour faire l'extraction du texte depuis pdf
import os
import re
from dotenv import load_dotenv # Permet de charger les clés API stockées dans un fichier .env.
# Load environment variables from .env
load_dotenv()



OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY) # On instancie un objet ChatOpenAI avec GPT-4o (version optimisée de GPT-4).

# Dictionary to store separate memory per CV ID
memory_store = {} # dictionnaire pour stocker la mémoire de chaque cv et chaque user

# discusion entre IA et candidat pour ameliorer son CV
def get_cv_chat_response(cv_id, cv_text, question):
    # Création d’une mémoire dédiée au CV.
    if cv_id not in memory_store:
        memory_store[cv_id] = ConversationBufferMemory(memory_key="history", return_messages=True)
    memory = memory_store[cv_id]

    system_prompt = (
        "You are a helpful assistant that helps users improve their CVs based on the provided CV text. "
        "You can only respond to questions about the CV and should politely refuse unrelated questions. "
        "If the user asks something not related to improving the CV, respond: "
        "'I can only provide guidance related to your CV and job search strategies. If you have questions on those topics, feel free to ask!'"
    )

    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=False,
    )

    # Add system prompt + CV text if memory is empty
    if not memory.buffer: #.buffer pour acceder au memoire
        conversation.memory.chat_memory.add_message(
            SystemMessage(content=system_prompt + f"\n\nHere is the user's CV:\n{cv_text}")
        )
        conversation.memory.chat_memory.add_message(
            AIMessage(content="Thank you for sharing your CV! How can I help you improve it?")
        )

    # Get response
    answer = conversation.run(question)

    # Return only human and assistant messages
    chat_history = [
        {"role": "user", "content": msg.content} if isinstance(msg, HumanMessage)
        else {"role": "assistant", "content": msg.content}
        for msg in memory.chat_memory.messages
        if isinstance(msg, (HumanMessage, AIMessage))
    ]

    return answer, chat_history




def analyze_cv_text(cv_text):
    system_prompt = (
        "You are a helpful assistant that performs structured analysis on CVs. "
        "Given the CV text, respond in JSON format with the following keys:\n"
        "- skills_match (as percentage)\n"
        "- experience_level (as percentage)\n"
        "- education_match (as percentage)\n"
        "- language_level (as percentage)"
    )

    analysis_question = (
        "Please analyze the CV and return a JSON with the keys: "
        "skills_match, experience_level, education_match, language_level. "
        "Each as a percentage."
    )

    memory = ConversationBufferMemory(return_messages=True)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=False,
    )

    memory.chat_memory.add_message(SystemMessage(content=system_prompt + f"\n\nCV:\n{cv_text}"))
    memory.chat_memory.add_message(AIMessage(content="Understood. Ready to analyze."))

    answer = conversation.run(analysis_question)

    #  Remove backticks and code block formatting if present
    cleaned_answer = re.sub(r"```(?:json)?\n(.*?)\n```", r"\1", answer, flags=re.DOTALL).strip()

    try:
        analysis_json = json.loads(cleaned_answer)
    except Exception:
        raise ValueError(f"Could not parse analysis response:\n{answer}")

    return analysis_json


def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print("File does not exist!")
        return None

    print(f"Trying to open PDF: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
        print("PDF opened successfully.")
        text = ""
        for i, page in enumerate(doc): # je vais parcourir le pdf page par page pour extracter le text
            page_text = page.get_text()

            text += page_text



        print("text extracted successfully")
        return text

    except Exception as e:
        print(f"Error: {e}")
        return None

def analyze_cv_text_skills(cv_text):
    system_prompt = (
        "You are an expert that extracts owner name, technologies, skills, education, languages, snapshot, hashtags, certifications, atouts, experience, email, and phone number from text."
    )

    analysis_question = (
      ''' Analyse ce CV et retourne uniquement ce JSON :
    
    {
      "owner": "",                   // nom complet du propriétaire du CV
      "contact": {
        "email": "",                 // extrait l'email
        "phone_number": ""           // extrait le numéro de téléphone
      },
      "technologies": ["python", "java", ...],
      "skills": ["résolution de problèmes", "travail en équipe", ...],
      "experience": [
        {
          "company": "",
          "duration": "",
          "position": ""
        }
      ],
      "levels": {
        "education_level": 0,        // évalue le niveau d'éducation entre 0 et 100%
        "experience_level": 0,       // évalue le niveau d’expérience pro en %
        "skills_level": 0,           // estime la polyvalence et la qualité des compétences
        "language_level": 0          // estime la maîtrise des langues mentionnées
      },
      "education": [
        {
          "degree": "",
          "institution": "",
          "year": ""
        }
      ],
      "languages": ["Français (Courant)", "Anglais (Courant)", ...],
      "snapshot": "",               // extrait le résumé professionnel
      "hashtags": ["#DevOps", "#Automation", ...],
      "certifications": ["AWS Certified Solutions Architect", "FinOps Cloud & AI", ...],
      "atouts": ["Automatisation des infrastructures", "CI/CD avancé", "Leadership", ...]
    }
    
    **Base-toi uniquement sur les infos disponibles dans le CV**, et ne retourne **que du JSON** (pas de texte autour).
    '''

    )

    memory = ConversationBufferMemory(return_messages=True)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=False,
    )

    memory.chat_memory.add_message(SystemMessage(content=system_prompt + f"\n\nCV:\n{cv_text}. Now, {analysis_question}"))
    memory.chat_memory.add_message(AIMessage(content="Understood. Ready to analyze."))

    answer = conversation.run(analysis_question)

    # Clean the response if it has code formatting
    cleaned_answer = re.sub(r"```(?:json)?\n(.*?)\n```", r"\1", answer, flags=re.DOTALL).strip()

    try:
        analysis_json = json.loads(cleaned_answer)
    except Exception:
        raise ValueError(f"Could not parse analysis response:\n{answer}")

    return analysis_json


def extract_job_info_from_description(job_text):
    system_prompt = (
        "You are an expert HR assistant helping to extract structured information from job descriptions. "
        "Given a full job description, return the following:"
        "1. A short summary of the job description (3-5 lines)"
        "2. A list of required technologies"
        "3. A list of required skills"
        "Respond in JSON format like: "
        '{"summary": "....","technologies": ["tech1", "tech2", ...],"skills": ["skill1", "skill2", ...]}'
      
    )

    # Build messages : juste préparer la disccusion avec chat
    messages = [
        SystemMessage(content=system_prompt), # ce que je vais envoyer au chatgpt
        HumanMessage(content=f"Here is the job description:{job_text}") # le message de l'humain qui se change
    ]# f utiliser pour formater le format du variable qui est en {}

    # Run LLM without history/memory
    response = llm.invoke(messages) # pour communiquer avec caht
    # reponse retourne le contenue json, date d'envoie et de reception de message, tokens envoyer et token de son reponse
    # Try parsing the response as JSON
    try:
        #  Remove backticks and code block formatting if present
        cleaned_answer = re.sub(r"```(?:json)?\n(.*?)\n```", r"\1", response.content, flags=re.DOTALL).strip()
        parsed = json.loads(cleaned_answer) # jsonify la reponse
        print (parsed)
        return parsed
    except Exception as e:
        return {"error": "Could not parse LLM output as JSON", "raw_response": response.content, "exception": str(e)}