from selenium import webdriver # permet de contrôler Chrome (ou un autre navigateur).
from selenium.webdriver.common.by import By # pour localiser des éléments sur la page (par ID, classe,..)
from selenium.webdriver.common.keys import Keys # permet de simuler des frappes clavier (ex : ENTER).
from selenium.webdriver.chrome.service import Service # pour configurer le driver Chrome
from selenium.webdriver.support.ui import WebDriverWait # permet d'attendre que certains éléments soient présents.
from selenium.webdriver.support import expected_conditions as EC # conditions d’attente, comme attendre la présence d’un élément.
import time # utilisé pour ajouter des délais.
import os # permet d'accéder aux variables d’environnement.
from dotenv import load_dotenv # charge un fichier .env 

from selenium.webdriver.chrome.options import Options # permet de configurer Chrome

options = Options() # Création d'une instance d'options pour Chrome
options.add_argument('--headless')  # mode sans interface graphique 
load_dotenv() # # Charge les variables d’environnement depuis le fichier .env

def login_to_linkedin(driver):
    driver.get("https://www.linkedin.com/login") # Va à la page de login LinkedIn
    username = driver.find_element(By.ID, "username") # Trouve le champ email
    password = driver.find_element(By.ID, "password") # Trouve le champ mot de passe
    LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL') # Récupère l'email depuis .env
    LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD') # Récupère le mdp depuis .env
    username.send_keys(LINKEDIN_EMAIL) # Saisit l'email
    password.send_keys(LINKEDIN_PASSWORD) # Saisit le mot de passe
    password.send_keys(Keys.RETURN) # Appuie sur Entrée
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "global-nav-search"))) # Attend que la barre de recherche soit chargée
    print("Logged in successfully.") # Affiche un message si tout va bien

# Extraction de la société et du titre du poste
def extract_company_and_title(driver):
    company_name = "N/A"
    job_title = "N/A"
    try:
        company_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-details-jobs-unified-top-card__company-name"))
        ) # il retourne tout le body html
        company_name = company_elem.text # Récupère le texte de la balise
    except Exception as e:
        print("Could not find company name:", e)

    try:
        title_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "t-24.t-bold.inline"))
        )
        job_title = title_elem.text
    except Exception as e:
        print("Could not find job title:", e)

    return company_name, job_title

# Extraction de la localisation
def extract_location(driver):
    location = "N/A"
    try:
        tertiary_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-details-jobs-unified-top-card__tertiary-description-container"))
        ) # dans le div il y a plusieurs span je dois extraire seulement le span de localisation
        spans = tertiary_container.find_elements(By.CLASS_NAME, "tvm__text--low-emphasis")
        if spans:
            location = spans[0].text # il faut prendre que le contenue de la premiere span car ils ont tous le meme nom de classe
    except Exception as e:
        print("Could not extract location:", e)
    return location

# Extraction des insights du poste (type, contrat, niveau)
def extract_job_insights(driver):
    work_type = "None"
    contract_type = "None"
    level = "None"
    try:
        insights = driver.find_elements(By.CSS_SELECTOR, "li.job-details-jobs-unified-top-card__job-insight span")
        job_info = [i.text.strip() for i in insights if i.text.strip() != ""] #strip pour nettoyer le contenu from les espaces
        # c'est une liste donc il faut accéder à chaque element de cette liste et extraire le texte
        if len(job_info) > 0: # element job_info[0] contient une icone donc je commence par le deuxieme element
            work_type = job_info[1] if len(job_info) > 1 else "None"
            contract_type = job_info[2] if len(job_info) > 2 else "None"
            level = job_info[3] if len(job_info) > 3 else "None"
    except Exception as e:
        print("Could not extract job type/contract/level:", e)
    return work_type, contract_type, level

# Extraction de la description du poste
def extract_job_description(driver):
    job_description = "N/A"
    full_text = ""
    try:
        description_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "job-details"))
        )
        full_text = description_container.text
        start_marker = "Description du poste"
        end_marker = "Profil"
        start_index = full_text.find(start_marker)
        end_index = full_text.find(end_marker)
        if start_index != -1:
            if end_index != -1 and end_index > start_index:
                job_description = full_text[start_index + len(start_marker):end_index].strip()
            else:
                job_description = full_text[start_index + len(start_marker):].strip()
    except Exception as e:
        print("Could not extract job description:", e)
    return job_description, full_text

# === GLOBAL FUNCTION ===
def scrape_linkedin_job_details(job_url):
    driver = webdriver.Chrome(options=options) # Démarre Chrome sans interface
    job_data = {}

    try:
        login_to_linkedin(driver) # Se connecte à LinkedIn
        driver.get(job_url) # Ouvre l’URL de l’offre
        time.sleep(5) # Attend que la page charge

        company, title = extract_company_and_title(driver)
        location = extract_location(driver)
        work_type, contract_type, level = extract_job_insights(driver)
        job_description, full_text = extract_job_description(driver)

        job_data = {
            "Company Name": company,
            "Job Title": title,
            "Location": location,
            "Job Type": work_type,
            "Contract Type": contract_type,
            "Level": level,
            "Job Description": job_description,
            "Full Text": full_text
        }

    finally:
        driver.quit() # Ferme le navigateur

    return job_data

# juste pour tester sans frontend
"""
JOB_URL = 'https://www.linkedin.com/jobs/search/?currentJobId=4252510465&distance=25&geoId=102134353&keywords=D%C3%A9veloppement%20De%20Logiciels&origin=JOBS_HOME_SEARCH_CARDS'
job_info = scrape_linkedin_job_details(JOB_URL)

# Print the scraped details
for key, value in job_info.items():
    print(f"{key}: {value}\n")
"""