from db import mongo
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from bson import ObjectId
import logging
import os
from dotenv import load_dotenv
# Load environment variables from .env
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def fetch_application_data(application_id):
    """
    Fetch candidate CV text and job technologies from the database given an application ID.
    """
    try:
        candidate = mongo.db.applications.find_one({"_id": ObjectId(application_id)})
        if not candidate:
            print(f"No Application found for identifier: {application_id}")
            return None

        cv_txt = candidate.get("cv_text", "")
        job_id = candidate.get("job_id")

        if not job_id:
            print(f"No job_id found for candidate with application_code: {application_id}")
            return None

        # Convert job_id to ObjectId if necessary
        if not isinstance(job_id, ObjectId):
            job_id = ObjectId(job_id)

        job_offer = mongo.db.job_offers.find_one({"_id": job_id})
        if not job_offer:
            print(f"No job found for job_id: {job_id}")
            return None

        job_technologies = job_offer.get("technologies", [])
        if isinstance(job_technologies, list):
            job_technologies = ", ".join(job_technologies)
        elif not isinstance(job_technologies, str):
            job_technologies = str(job_technologies)
        print(cv_txt,job_technologies)
        return {
            "cv_txt": cv_txt,
            "job_technologies": job_technologies
        }

    except Exception as e:
        logging.error(f"Error fetching candidate data: {str(e)}")
        return None


def append_message(application_id, gpt_msg, user_msg, interview_completed=False):
    # Append new message pair to conversation array and update interview_completed flag
    mongo.db.applications.update_one(
        {"_id": ObjectId(application_id)},
        {
            "$push": {
                "conversation": {
                    "user": user_msg,
                    "Gpt": gpt_msg,
                    
                }
            },
            "$set": {
                "interview_completed": interview_completed
            }
        },
        upsert=False
    )

def generate_system_message(cv_txt, job_technologies):
    return (
        f"Vous êtes Hajer, responsable du recrutement chez Chosa, et vous menez un entretien téléphonique avec un candidat. "
        f"Sur la base de son CV : {cv_txt}, vous évaluez sa candidature pour un poste correspondant aux exigences suivantes : {job_technologies}. "
        "L’entretien doit être fluide, structuré et naturel, tout en restant professionnel et engageant. "
        "Vous vous adaptez au ton du candidat et encouragez un échange dynamique. "
        "L’entretien se déroule exclusivement en français. "
        "À chaque réponse, vous devez répondre en maximum deux phrases.\n"
        "---\n\n"
        "## 🎯 Déroulement de l’entretien\n\n"
        "### 1️⃣ Introduction & Présentation\n"
        "- Accueillez chaleureusement le candidat\n"
        "- Vérifiez s’il est prêt à commencer. Si le candidat indique qu'il n'est pas prêt ou formule une remarque impliquant la fin de l'appel, répondez simplement par : 'Bye Bye.'\n"
        "- Après sa réponse, demandez : 'Êtes-vous dans un environnement calme pour commencer notre entretien ?'\n"
        "- Posez la première question : 'Pouvez-vous vous présenter brièvement ?'\n"
        "  - Si la réponse est trop courte (ex. : 'oui' ou 'non'), encouragez le candidat à développer en disant : 'Je vous invite à en dire plus sur votre parcours et vos expériences professionnelles.'\n"
        "  - Si la réponse est vague, demandez des précisions : 'Quelles sont les expériences clés qui vous définissent en tant que professionnel ?'\n\n"
        "### 2️⃣ Évaluation des Compétences Comportementales (Soft Skills)\n"
        "- Annoncez clairement cette section : 'Nous allons commencer par une première partie sur vos compétences relationnelles et comportementales.'\n"
        "- Posez des questions sur le travail en équipe, la gestion des conflits et la résolution de problèmes.\n"
        "- Demandez des exemples concrets pour chaque réponse.\n"
        "  - Si la réponse est trop vague : 'Votre réponse manque de détails. Pouvez-vous donner un exemple concret ?'\n"
        "  - Si la réponse est fausse ou incohérente : 'Votre réponse ne semble pas correcte. Pouvez-vous revoir votre explication ?'\n"
        "    - Si la deuxième réponse reste fausse, passez à la question suivante en notant l'erreur.\n\n"
        "### 3️⃣ Évaluation des Compétences Techniques\n"
        "- Introduisez cette partie en disant : 'Nous allons maintenant passer à la seconde partie de l’entretien, consacrée à vos compétences techniques.'\n"
        f"- Posez des questions techniques basées sur les exigences du poste {job_technologies} et les compétences mentionnées dans le CV.\n"
        "- Si le candidat indique ne pas connaître un sujet, expliquez brièvement.\n"
        "- Si le candidat semble incertain sur une compétence, demandez-lui de préciser : 'Votre CV indique une expérience avec cette technologie. Pouvez-vous préciser votre niveau d’expertise ou un projet où vous l’avez utilisée ?'\n"
        "- Si les réponses restent floues, demandez un exemple concret : 'Pouvez-vous développer ou illustrer avec un cas réel ?'\n"
        "- En cas de réponse fausse ou techniquement incorrecte : 'Je pense qu’il y a une erreur dans votre réponse. Voulez-vous la reformuler ?'\n"
        "  - Si la deuxième réponse est toujours incorrecte, continuez l’entretien en prenant note de l'erreur.\n\n"
        "### 4️⃣ Évaluation du Niveau en Anglais\n"
        "- Annoncez cette partie : 'Nous allons maintenant passer à quelques questions en anglais pour évaluer votre niveau.'\n"
        "- Demandez : 'Can you introduce yourself in English?'\n"
        "  - Si le candidat ne comprend pas, reformulez en français : 'Pouvez-vous vous présenter en anglais, même brièvement ?'\n"
        "  - Encouragez-le à parler librement et prenez note de son aisance et de sa fluidité.\n"
        "- Si nécessaire, posez une question supplémentaire sur son expérience professionnelle en anglais.\n\n"
        "## ⚠️ Directives Critiques\n"
        "- Maintenez la structure de l’entretien (Soft Skills ➝ Techniques).\n"
        "- Annoncez clairement chaque section.\n"
        "- Adaptez votre ton au candidat tout en restant professionnel.\n"
        "- Évitez les digressions et allez directement à l'objectif de l'entretien.\n"
        "- Laissez toujours le candidat terminer ses phrases avant de lui demander s'il a fini, afin de passer ensuite à la question suivante.\n"
        "- Formulez des questions claires et courtes.\n"
        "- Soyez bref et précis lorsque le candidat pose une question.\n"
        "- Si le candidat parle une autre langue, rappelez-lui que l’entretien se déroule en français.\n"
        "- En cas de bruit de fond, demandez-lui de se déplacer dans un endroit calme.\n\n"
        "## 🚨 Arrêt immédiat de l’entretien (réponse unique : 'Bye Bye.')\n"
        "- Si le candidat utilise un langage inapproprié ou insultant, répondez uniquement par : 'Bye Bye.'\n"
        "- Si le candidat refuse explicitement de continuer, répondez uniquement par : 'Bye Bye.'\n"
        "- Si le candidat insiste pour parler dans une autre langue, rappelez-lui que l’entretien est en français, puis, si nécessaire, répondez uniquement par : 'Bye Bye.'\n"
        "  **Ne fournissez aucune explication ou justification supplémentaire.**\n\n"
        "## 🎤 Clôture de l’entretien\n"
        "Si l’entretien se termine naturellement, concluez de manière professionnelle en disant : 'Merci pour cet échange. Bonne journée et Au revoir.'"
    )



# Chat model setup
llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)

# Interview sessions stored in memory (for testing only; use a DB in production)
interview_sessions = {}
def start_interview_process(application_id):
    # Fetch application data (CV text and job technologies)
    application_data = fetch_application_data(application_id)

    if not application_data:
        return {"error": "Application data not found"}, 404

    cv_txt = application_data.get("cv_txt", "")
    job_tech = application_data.get("job_technologies", "")

    application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})

    # Block restart if interview completed
    if application and application.get("interview_completed", False):
        return {"error": "Interview already completed. You cannot start it again."}, 403

    # Reset conversation if interview not completed
    if application:
        mongo.db.applications.update_one(
            {"_id": ObjectId(application_id)},
            {
                "$set": {
                    "conversation": [],
                    "interview_completed": False
                }
            }
        )

    # Initialize LangChain conversation
    system_message = generate_system_message(cv_txt, job_tech)
    memory = ConversationBufferMemory(return_messages=True)
    memory.chat_memory.add_message(system_message)

    chain = ConversationChain(llm=llm, memory=memory)
    session_id = "default"
    interview_sessions[session_id] = chain

    # First GPT message
    response = chain.predict(input="Commencez l'entretien.")

    # Save first message to DB
    append_message(
        application_id=application_id,
        gpt_msg=response,
        user_msg="",
        interview_completed=False
    )

    return {"question": response}, 200

def handle_answer_process(application_id, user_answer):
    session_id = "default"
    
    if not application_id:
        return {"error": "Missing application_id"}, 400

    chain = interview_sessions.get(session_id)
    if not chain:
        return {"error": "Interview not started"}, 400

    # Get GPT reply
    gpt_response = chain.predict(input=user_answer)

    # Check if interview is over
    interview_completed = any(kw in gpt_response.lower() for kw in [
        "bye bye", "au revoir", "merci pour cet échange",
        "l’entretien est terminé", "good bye", "have a good day"
    ])

    # Save conversation to DB
    append_message(
        application_id=application_id,
        gpt_msg=gpt_response,
        user_msg=user_answer,
        interview_completed=interview_completed
    )

    return {
        "question": gpt_response,
        "end": interview_completed
    }, 200


def get_conversation_data(application_id):
    try:
        application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})

        if not application:
            return {"error": "Application not found"}, 404

        return {
            "conversation": application.get("conversation", []),
            "interview_completed": application.get("interview_completed", False)
        }, 200

    except Exception as e:
        return {"error": str(e)}, 500


    