import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from db import mongo
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib import colors
from bson import ObjectId
load_dotenv()
model = ChatOpenAI(model="gpt-4o-mini",temperature=0.8,openai_api_key=os.getenv("OPENAI_API_KEY"))

def fetch_application_data(application_id):
    # Get application data
    application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})
    if not application:
        raise Exception("Application not found.")

    cv_text = application.get("cv_text", "")
    conversation = application.get("conversation", [])
    job_id = application.get("job_id")

    if not job_id:
        raise Exception("Job ID missing in application.")

    # Get job data
    job = mongo.db.job_offers.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise Exception("Job not found.")

    job_description = job.get("job_description", "")

    return {
        "cv_txt": cv_text,
        "conversation": conversation,
        "job": job_description
    }


def generate_report(cv_text, chat_text, offer_text):
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
		 "- **Date de l’entretien** : [date du géneration du reponse]\n"
		 "- **Intervenants** : [Nom du recruteur / Manager]\n\n"

		 "📎 **2. CV du candidat**\n"
		 "- Lien ou pièce jointe du CV : [Indiquer si disponible]\n\n"

		 "🎤 **3. Enregistrement de l’entretien**\n"
		 "- Lien vers l’enregistrement : [Insérer le lien si fourni]\n\n"

		 "🛠 **4. Compétences techniques (Hard Skills)**\n"
		 "- Évaluer les compétences en lien avec le poste et les noter sur 100%.\n"
		 "  - **Maîtrise de [Logiciel/Technologie]** : XX%\n"
		 "  - **Expérience en [Domaine/Industrie]** : XX%\n"
		 "  - **Connaissance en [Sujet spécifique]** : XX%\n\n"

		 "💡 **5. Compétences comportementales (Soft Skills)**\n"
		 "- Identifier et évaluer les soft skills observées pendant l’entretien.\n"
		 "  - **Exemples** : Esprit d’équipe, Capacité d’adaptation, Leadership, Communication\n\n"

		" 🌍 **6. Niveau de langue**\n"
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

	prompt_template = ChatPromptTemplate.from_messages(
		messages
	)

	prompt = prompt_template.invoke({
		"cv_text": cv_text,
		"chat_text": chat_text,
		"offer_text": offer_text
	})
	result = model.invoke(prompt)

	return result.content




def generate_pdf(content, filename):

	doc = SimpleDocTemplate(str(filename), pagesize=A4,
	                        leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)

	elements = []
	styles = getSampleStyleSheet()

	title_style = ParagraphStyle(
		'TitleStyle', parent=styles['Title'], fontSize=14, spaceAfter=10, alignment=1
	)

	normal_style = ParagraphStyle(
		'NormalStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6
	)

	elements.append(Paragraph("📄 **Rapport d’Entretien**", title_style))
	elements.append(Spacer(1, 10))

	for paragraph in content.split("\n"):
		if paragraph.strip():
			elements.append(Paragraph(paragraph, normal_style))
			elements.append(Spacer(1, 4))

	def footer(canvas, doc):
		canvas.setFont("Helvetica", 8)
		canvas.setFillColor(colors.grey)
		canvas.drawString(30, 20, f"Page {doc.page}/2")  # Max 2 pages

	doc.build(elements, onLaterPages=footer, onFirstPage=footer)


def generate_candidate_report(application_id):
    candidate_data = fetch_application_data(application_id)
    cv_text = candidate_data['cv_txt']
    chat_text = candidate_data['conversation']
    offer_text = candidate_data['job']

    report_content = generate_report(cv_text, chat_text, offer_text)
    upload_folder = os.getenv('UPLOAD_report_FOLDER', 'uploads/report')  # fallback folder
    pdf_path = os.path.join(upload_folder, f"rapport_entretien-{application_id}.pdf")
    
    generate_pdf(report_content, pdf_path)

    # Update the application document with the report path
    mongo.db.applications.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"report_path": pdf_path}}
    )


    return pdf_path


