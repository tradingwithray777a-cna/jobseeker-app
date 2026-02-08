from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import re
import asyncio
from io import BytesIO
from openpyxl import Workbook
from urllib.parse import quote

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'jobseeker_db')]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_title: str
    employer: str
    job_description: str
    date_posted: str
    salary_range: str
    employer_website: str
    ats_keywords: List[str]
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class JobSearchRequest(BaseModel):
    job_title: str

class FavoriteJobCreate(BaseModel):
    job_id: str

class EmailAlertCreate(BaseModel):
    email: str
    job_title: str

# Helper function
def extract_ats_keywords(description: str) -> List[str]:
    keywords = ['python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node', 
                'sql', 'mysql', 'postgresql', 'mongodb', 'aws', 'azure', 'gcp', 'docker', 
                'kubernetes', 'agile', 'scrum', 'api', 'rest', 'testing', 'git', 'html', 'css',
                'machine learning', 'data science', 'analytics', 'devops', 'ci/cd', 'excel',
                'tableau', 'powerbi', 'salesforce', 'sap', 'marketing', 'sales', 'finance']
    found = [kw for kw in keywords if kw.lower() in description.lower()]
    return list(set(found))[:10]

# HTTP-based scrapers (no Playwright needed)
async def scrape_mycareersfuture(job_title: str) -> List[Job]:
    """Scrape jobs from MyCareersFuture using HTTP requests"""
    jobs = []
    try:
        logger.info(f"HTTP scraping MyCareersFuture for: {job_title}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        search_query = quote(job_title)
        url = f"https://www.mycareersfuture.gov.sg/search?search={search_query}&sortBy=new_posting_date"
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for job cards in the HTML
            job_cards = soup.find_all('div', {'id': lambda x: x and x.startswith('job-card')})
            
            logger.info(f"Found {len(job_cards)} job cards on MCF")
            
            for card in job_cards[:50]:
                try:
                    title_elem = card.find('a', {'data-testid': lambda x: x and 'job-card-title' in x}) or card.find('h3') or card.find('a')
                    company_elem = card.find(attrs={'data-testid': lambda x: x and 'company' in x})
                    salary_elem = card.find(attrs={'data-testid': lambda x: x and 'salary' in x})
                    link_elem = card.find('a', href=lambda x: x and '/job/' in x)
                    
                    title_text = title_elem.get_text(strip=True) if title_elem else ""
                    company_text = company_elem.get_text(strip=True) if company_elem else ""
                    salary_text = salary_elem.get_text(strip=True) if salary_elem else "Competitive"
                    job_link = link_elem['href'] if link_elem else ""
                    
                    if title_text and company_text:
                        if job_link and not job_link.startswith('http'):
                            job_link = f"https://www.mycareersfuture.gov.sg{job_link}"
                        
                        job = Job(
                            job_title=title_text,
                            employer=company_text,
                            job_description=f"Position at {company_text}. Visit job page for details.",
                            date_posted=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            salary_range=salary_text,
                            employer_website=job_link or url,
                            ats_keywords=extract_ats_keywords(f"{title_text} {company_text}"),
                            source="MyCareersFuture"
                        )
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing MCF card: {str(e)}")
                    continue
        
        logger.info(f"Scraped {len(jobs)} jobs from MyCareersFuture")
        
    except Exception as e:
        logger.error(f"Error in MCF scraper: {str(e)}")
    
    return jobs

async def scrape_jobstreet(job_title: str) -> List[Job]:
    """Scrape jobs from JobStreet using HTTP requests"""
    jobs = []
    try:
        logger.info(f"HTTP scraping JobStreet for: {job_title}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        search_query = job_title.replace(' ', '-').lower()
        url = f"https://www.jobstreet.com.sg/{search_query}-jobs"
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for job cards
            job_cards = soup.find_all('article', {'data-testid': 'job-card'})
            if not job_cards:
                job_cards = soup.find_all('div', {'data-card-type': 'JobCard'})
            
            logger.info(f"Found {len(job_cards)} job cards on JobStreet")
            
            for card in job_cards[:50]:
                try:
                    title_elem = card.find('a', {'data-automation': 'job-list-item-link-overlay'}) or card.find('h1') or card.find('h2') or card.find('a')
                    company_elem = card.find(attrs={'data-automation': 'jobCardCompanyName'})
                    salary_elem = card.find(attrs={'data-automation': 'job-card-salary'})
                    link_elem = card.find('a', href=lambda x: x and '/job/' in x)
                    
                    title_text = title_elem.get_text(strip=True) if title_elem else ""
                    company_text = company_elem.get_text(strip=True) if company_elem else ""
                    salary_text = salary_elem.get_text(strip=True) if salary_elem else "Competitive"
                    job_link = link_elem['href'] if link_elem else ""
                    
                    if title_text and company_text:
                        if job_link and not job_link.startswith('http'):
                            job_link = f"https://www.jobstreet.com.sg{job_link}"
                        
                        job = Job(
                            job_title=title_text,
                            employer=company_text,
                            job_description=f"Opportunity at {company_text}. Click to view details.",
                            date_posted=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            salary_range=salary_text,
                            employer_website=job_link or url,
                            ats_keywords=extract_ats_keywords(f"{title_text} {company_text}"),
                            source="JobStreet"
                        )
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing JobStreet card: {str(e)}")
                    continue
        
        logger.info(f"Scraped {len(jobs)} jobs from JobStreet")
        
    except Exception as e:
        logger.error(f"Error in JobStreet scraper: {str(e)}")
    
    return jobs

# Routes
@api_router.get("/")
async def root():
    return {"message": "Job Seeker API"}

@api_router.post("/jobs/search")
async def search_jobs(request: JobSearchRequest):
    logger.info(f"Searching for: {request.job_title}")
    await db.jobs.delete_many({"created_at": {"$lt": datetime.now(timezone.utc) - timedelta(hours=1)}})
    
    mcf_jobs, js_jobs = await asyncio.gather(
        scrape_mycareersfuture(request.job_title),
        scrape_jobstreet(request.job_title)
    )
    
    all_jobs = mcf_jobs + js_jobs
    all_jobs = all_jobs[:200]
    
    if all_jobs:
        jobs_dict = []
        for job in all_jobs:
            job_dict = job.model_dump()
            job_dict['created_at'] = job_dict['created_at'].isoformat()
            jobs_dict.append(job_dict)
        await db.jobs.insert_many(jobs_dict)
    
    return {"success": True, "count": len(all_jobs), "message": f"Found {len(all_jobs)} jobs"}

@api_router.get("/jobs", response_model=List[Job])
async def get_jobs(employer: Optional[str] = None, source: Optional[str] = None):
    query = {}
    if employer:
        query["employer"] = {"$regex": employer, "$options": "i"}
    if source:
        query["source"] = source
    
    jobs = await db.jobs.find(query, {"_id": 0}).to_list(200)
    for job in jobs:
        if isinstance(job['created_at'], str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
    return jobs

@api_router.post("/jobs/favorite")
async def add_favorite(request: FavoriteJobCreate):
    existing = await db.favorites.find_one({"job_id": request.job_id, "user_id": "default_user"}, {"_id": 0})
    if existing:
        return existing
    
    favorite = {
        "id": str(uuid.uuid4()),
        "job_id": request.job_id,
        "user_id": "default_user",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.favorites.insert_one(favorite)
    return favorite

@api_router.delete("/jobs/favorite/{job_id}")
async def remove_favorite(job_id: str):
    result = await db.favorites.delete_one({"job_id": job_id, "user_id": "default_user"})
    return {"success": result.deleted_count > 0}

@api_router.get("/jobs/favorites")
async def get_favorites():
    favorites = await db.favorites.find({"user_id": "default_user"}, {"_id": 0}).to_list(1000)
    job_ids = [fav['job_id'] for fav in favorites]
    jobs = await db.jobs.find({"id": {"$in": job_ids}}, {"_id": 0}).to_list(1000)
    for job in jobs:
        if isinstance(job['created_at'], str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
    return jobs

@api_router.post("/alerts")
async def create_alert(request: EmailAlertCreate):
    alert = {
        "id": str(uuid.uuid4()),
        "email": request.email,
        "job_title": request.job_title,
        "user_id": "default_user",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.alerts.insert_one(alert)
    return alert

@api_router.get("/alerts")
async def get_alerts():
    alerts = await db.alerts.find({"user_id": "default_user"}, {"_id": 0}).to_list(1000)
    return alerts

@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    result = await db.alerts.delete_one({"id": alert_id, "user_id": "default_user"})
    return {"success": result.deleted_count > 0}

@api_router.get("/jobs/export")
async def export_jobs():
    jobs = await db.jobs.find({}, {"_id": 0}).to_list(200)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Jobs"
    
    headers = ['Job Title', 'Employer', 'Job Description', 'Date Posted', 'Salary Range', 'Employer Website', 'ATS Keywords', 'Source']
    ws.append(headers)
    
    for job in jobs:
        ws.append([
            job.get('job_title', ''),
            job.get('employer', ''),
            job.get('job_description', ''),
            job.get('date_posted', ''),
            job.get('salary_range', ''),
            job.get('employer_website', ''),
            ', '.join(job.get('ats_keywords', [])),
            job.get('source', '')
        ])
    
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=jobs_export.xlsx"}
    )

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
