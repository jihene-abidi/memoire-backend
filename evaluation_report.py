import os # Pour interagir avec les variables d'environnement
from flask import Flask, request, jsonify # Pour créer une API web
from dotenv import load_dotenv # Pour charger les variables d'environnement depuis un fichier .env
from langchain.prompts import ChatPromptTemplate # Pour créer un prompt structuré pour le modèle
from langchain_openai import ChatOpenAI  # Pour utiliser le modèle OpenAI via LangChain
from db import mongo # Connexion à la base de données MongoDB
from reportlab.lib.pagesizes import A4 # Format de page pour le PDF
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # Styles de texte pour PDF
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer # Eléments de base pour créer le PDF
from reportlab.lib import colors # Couleurs pour PDF
from bson import ObjectId # Pour gérer les IDs MongoDB
load_dotenv() # Charge les variables d'environnement depuis le fichier .env

# Initialisation du modèle GPT-4o-mini avec un certain degré de créativité (temperature = 0.8)
model = ChatOpenAI(model="gpt-4o-mini",temperature=0.8,openai_api_key=os.getenv("OPENAI_API_KEY"))

# Fonction pour récupérer les données d'une candidature
def fetch_application_data(application_id):
    # Recherche la candidature par ID dans MongoDB
    application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})
    if not application:
        raise Exception("Application not found.")

    # Récupère les champs de la candidature
    cv_text = application.get("cv_text", "")
    conversation = application.get("conversation", [])
    job_id = application.get("job_id")

    if not job_id:
        raise Exception("Job ID missing in application.")

    # Récupère l’offre d’emploi associée à cette candidature
    job = mongo.db.job_offers.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise Exception("Job not found.")

    job_description = job.get("job_description", "")

    # Retourne les données pertinentes
    return {
        "cv_txt": cv_text,
        "conversation": conversation,
        "job": job_description
    }

# Fonction pour générer le contenu du rapport d'entretien en texte
def generate_report(cv_text, chat_text, offer_text):
    # Messages de consigne pour le modèle GPT
	messages = [
		("system", "You are an experienced recruiter in human resources. Your job is to evaluate a candidate based on their CV, the job offer, and the interview transcript."),
		("human",
		 "Générez un **rapport d'entretien détaillé** pour le candidat en utilisant les éléments suivants :\n\n"
		 "**📌 Offre d'emploi :**\n{offer_text}\n\n"
		 "**📎 CV du candidat :**\n{cv_text}\n\n"
		 "**📝 Transcription de l’entretien :**\n{chat_text}\n\n"
		 "Le rapport doit suivre cette structure :\n\n"

		 "📋 **1. Informations du candidat**\n"
		 "- **Nom et Prénom** : [extrait le nom et le prénom à partir du cv]\n"
		 "- **Poste visé** : [Extrait de l’offre d’emploi]\n"
		 "- **Ressoure humaines** : Hajer \n\n"

		 "🛠 **2. Compétences techniques (Hard Skills)**\n"
		 "- Évaluer les compétences en lien avec le poste et les noter sur 100%.\n"
		 "  - **Maîtrise de [Logiciel/Technologie]** : XX%\n"
		 "  - **Expérience en [Domaine/Industrie]** : XX%\n"
		 "  - **Connaissance en [Sujet spécifique]** : XX%\n\n"

		 "💡 **3. Compétences comportementales (Soft Skills)**\n"
		 "- Identifier et évaluer les soft skills observées pendant l’entretien.\n"
		 "  - **Exemples** : Esprit d’équipe, Capacité d’adaptation, Leadership, Communication\n\n"

		" 🌍 **4. Niveau de langue**\n"
		"- **Évaluer le niveau de langue du candidat à partir de la conversation d’entretien**\n"
		"- Déterminer son niveau en fonction de la fluidité, de la précision grammaticale et de la richesse du vocabulaire.\n"
		"- Si un test de langue a été réalisé, attribuer un niveau spécifique.8\n"
		"- Utiliser cette échelle d’évaluation : **Débutant / Intermédiaire / Avancé / Courant**.\n"

		" 📌 **Langues détectées et évaluées** :\n"
		"- **Français** : [Débutant / Intermédiaire / Avancé / Courant]\n"
		"- **Autres langues mentionnées ou testées dans l’entretien** :\n"
		"- **Anglais** (si testé) : [Débutant / Intermédiaire / Avancé / Courant]\n"
	                          

		"🔍 **7. Conseils et axes d’amélioration**\n"
			 "- Suggérer des pistes d’amélioration pour le candidat.\n"
			 "  - Approfondir ses connaissances sur [Sujet]\n"
			 "  - Travailler sur [Compétence à améliorer]\n\n"
	
			 "📝 **8. Commentaire général sur l’entretien**\n"
			 "- Synthèse globale des performances du candidat.\n"
			 "- Points forts et axes d’amélioration.\n\n"
			 
			 "📊 **9. Score global et échelle d’évaluation**\n"
			 "- Donner un pourcentage global de réussite à l’entretien."
			 "- Indiquer l’échelle d’évaluation utilisée."
	
			 "✅ **10. Décision finale**\n"
			 "- réuisste ou refus \n"
			 " -pour en consédiration que le pourcentage supérieur ou égale de 70% est une réussite dans l'entretien sinon refus \n"


		 )
	]
      
    # Crée le prompt à envoyer au modèle à partir du template et des variables
	prompt_template = ChatPromptTemplate.from_messages(
		messages
	)

	prompt = prompt_template.invoke({
		"cv_text": cv_text,
		"chat_text": chat_text,
		"offer_text": offer_text
	})
      
    # Envoie le prompt au modèle et récupère la réponse
	result = model.invoke(prompt)
	return result.content



# Fonction qui génère un fichier PDF à partir du contenu texte
def generate_pdf(content, filename):

	doc = SimpleDocTemplate(str(filename), pagesize=A4,
	                        leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)

	elements = []
	styles = getSampleStyleSheet()

	# Style pour le titre du rapport
	title_style = ParagraphStyle(
		'TitleStyle', parent=styles['Title'], fontSize=14, spaceAfter=10, alignment=1
	)

	# Style pour le texte normal
	normal_style = ParagraphStyle(
		'NormalStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6
	)

	# Titre du rapport
	elements.append(Paragraph("📄 **Rapport d’Entretien**", title_style))
	elements.append(Spacer(1, 10))

	# Ajout de chaque paragraphe du contenu
	for paragraph in content.split("\n"):
		if paragraph.strip():
			elements.append(Paragraph(paragraph, normal_style))
			elements.append(Spacer(1, 4))

    # Fonction pour ajouter un pied de page avec numéro
	def footer(canvas, doc):
		canvas.setFont("Helvetica", 8)
		canvas.setFillColor(colors.grey)
		canvas.drawString(30, 20, f"Page {doc.page}/2")  # Max 2 pages

	doc.build(elements, onLaterPages=footer, onFirstPage=footer)


# Fonction principale pour générer un rapport PDF pour une candidature
def generate_candidate_report(application_id):
    
    # Étape 1 : Récupération des données
    
    candidate_data = fetch_application_data(application_id)
    cv_text = candidate_data['cv_txt']
    chat_text = candidate_data['conversation']
    offer_text = candidate_data['job']

	# Étape 2 : Génération du rapport avec GPT

    report_content = generate_report(cv_text, chat_text, offer_text)
    
	# Étape 3 : Définir le chemin du fichier PDF à générer
      
    upload_folder = os.getenv('', 'uploads/reports')  # Chemin de sauvegarde
    pdf_path = upload_folder +"/" + f"rapport_entretien-{application_id}.pdf" # concatination du nom du fichier
    
	# Étape 4 : Générer le PDF

    generate_pdf(report_content, pdf_path)

    # Étape 5 : Enregistrer le chemin du PDF dans la base de données

    # Mise à jour de la base de données avec le chemin du rapport
    mongo.db.applications.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"report_path": pdf_path}}
    )


    return pdf_path

