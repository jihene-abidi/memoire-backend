from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from dotenv import load_dotenv

from selenium.webdriver.chrome.options import Options

options = Options() # pour désactiver chrome
options.add_argument('--headless')  # Run in headless mode (no GUI)
load_dotenv()

def login_to_linkedin(driver):
    driver.get("https://www.linkedin.com/login")
    username = driver.find_element(By.ID, "username")
    password = driver.find_element(By.ID, "password")
    LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL')
    LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')
    username.send_keys(LINKEDIN_EMAIL)
    password.send_keys(LINKEDIN_PASSWORD)
    password.send_keys(Keys.RETURN)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "global-nav-search")))
    print("Logged in successfully.")

def extract_company_and_title(driver):
    company_name = "N/A"
    job_title = "N/A"
    try:
        company_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-details-jobs-unified-top-card__company-name"))
        ) # il retourne tout le body html
        company_name = company_elem.text # ilfaut extraire que le texte c.a.d le contenu
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

def extract_job_insights(driver):
    work_type = "None"
    contract_type = "None"
    level = "None"
    try:
        insights = driver.find_elements(By.CSS_SELECTOR, "li.job-details-jobs-unified-top-card__job-insight span")
        job_info = [i.text.strip() for i in insights if i.text.strip() != ""] #strip pour nettoyer le contenu from les espaces
        # c'est une liste donc il faut accéder à chaque element de cette liste et extraire le texte
        if len(job_info) > 0: # element job_info[0] contient licone donc je commence par le deuxieme element
            work_type = job_info[1] if len(job_info) > 1 else "None"
            contract_type = job_info[2] if len(job_info) > 2 else "None"
            level = job_info[3] if len(job_info) > 3 else "None"
    except Exception as e:
        print("Could not extract job type/contract/level:", e)
    return work_type, contract_type, level

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
    driver = webdriver.Chrome(options=options)
    job_data = {}

    try:
        login_to_linkedin(driver)
        driver.get(job_url)
        time.sleep(5)

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
        driver.quit()

    return job_data

"""
JOB_URL = 'https://www.linkedin.com/jobs/search/?currentJobId=4252510465&distance=25&geoId=102134353&keywords=D%C3%A9veloppement%20De%20Logiciels&origin=JOBS_HOME_SEARCH_CARDS'
job_info = scrape_linkedin_job_details(JOB_URL)

# Print the scraped details
for key, value in job_info.items():
    print(f"{key}: {value}\n")
"""