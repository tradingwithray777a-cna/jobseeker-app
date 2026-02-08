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
from playwright.async_api import async_playwright
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
                'machine learning', 'data science', 'analytics', 'devops', 'ci/cd']
    found = [kw for kw in keywords if kw.lower() in description.lower()]
    return list(set(found))[:10]

# Real Scraper functions
async def scrape_mycareersfuture(job_title: str) -> List[Job]:
    """Scrape REAL jobs from MyCareersFuture using Playwright"""
    jobs = []
    try:
        logger.info(f"Live scraping MyCareersFuture for: {job_title}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            search_query = quote(job_title)
            url = f"https://www.mycareersfuture.gov.sg/search?search={search_query}&sortBy=new_posting_date"
            
            try:
                await page.goto(url, timeout=30000, wait_until="networkidle")
                await asyncio.sleep(3)
                
                job_elements = await page.query_selector_all('div[id^="job-card"]')
                
                logger.info(f"Found {len(job_elements)} job elements on MCF")
                
                for idx, elem in enumerate(job_elements[:50]):
                    try:
                        title_text = ""
                        company_text = ""
                        salary_text = "Competitive"
                        
                        title_elem = await elem.query_selector('a[data-testid*="job-card-title"], h3, a')
                        if title_elem:
                            title_text = (await title_elem.inner_text()).strip()
                        
                        company_elem = await elem.query_selector('[data-testid*="company"], .company')
                        if company_elem:
                            company_text = (await company_elem.inner_text()).strip()
                        
                        salary_elem = await elem.query_selector('[data-testid*="salary"], .salary')
                        if salary_elem:
                            salary_text = (await salary_elem.inner_text()).strip()
                        
                        link_elem = await elem.query_selector('a[href*="/job/"]')
                        job_link = ""
                        if link_elem:
                            job_link = await link_elem.get_attribute('href')
                            if job_link and not job_link.startswith('http'):
                                job_link = f"https://www.mycareersfuture.gov.sg{job_link}"
                        
                        if title_text and company_text:
                            job = Job(
                                job_title=title_text,
                                employer=company_text,
                                job_description=f"Position available at {company_text}. Visit the job page for full details.",
                                date_posted=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                salary_range=salary_text,
                                employer_website=job_link or f"https://www.mycareersfuture.gov.sg/search?search={search_query}",
                                ats_keywords=extract_ats_keywords(f"{title_text} {company_text}"),
                                source="MyCareersFuture"
                            )
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Error parsing MCF job card: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"Error loading MCF page: {str(e)}")
            
            await browser.close()
        
        logger.info(f"Scraped {len(jobs)} real jobs from MyCareersFuture")
        
    except Exception as e:
        logger.error(f"Error in MCF scraper: {str(e)}")
    
    return jobs

async def scrape_jobstreet(job_title: str) -> List[Job]:
    """Scrape REAL jobs from JobStreet using Playwright"""
    jobs = []
    try:
        logger.info(f"Live scraping JobStreet for: {job_title}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            search_query = quote(job_title)
            url = f"https://www.jobstreet.com.sg/{job_title.replace(' ', '-').lower()}-jobs"
            
            try:
                await page.goto(url, timeout=30000, wait_until="networkidle")
                await asyncio.sleep(3)
                
                job_elements = await page.query_selector_all('article[data-testid="job-card"], div[data-card-type="JobCard"]')
                
                logger.info(f"Found {len(job_elements)} job elements on JobStreet")
                
                for idx, elem in enumerate(job_elements[:50]):
                    try:
                        title_text = ""
                        company_text = ""
                        salary_text = "Competitive"
                        
                        title_elem = await elem.query_selector('a[data-automation="job-list-item-link-overlay"], h1, h2, a')
                        if title_elem:
                            title_text = (await title_elem.inner_text()).strip()
                        
                        company_elem = await elem.query_selector('[data-automation="jobCardCompanyName"], .company-name')
                        if company_elem:
                            company_text = (await company_elem.inner_text()).strip()
                        
                        salary_elem = await elem.query_selector('[data-automation="job-card-salary"], .salary')
                        if salary_elem:
                            salary_text = (await salary_elem.inner_text()).strip()
                        
                        link_elem = await elem.query_selector('a[href*="/job/"]')
                        job_link = ""
                        if link_elem:
                            job_link = await link_elem.get_attribute('href')
                            if job_link and not job_link.startswith('http'):
                                job_link = f"https://www.jobstreet.com.sg{job_link}"
                        
                        if title_text and company_text:
                            job = Job(
                                job_title=title_text,
                                employer=company_text,
                                job_description=f"Opportunity at {company_text}. Click to view full job description.",
                                date_posted=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                salary_range=salary_text,
                                employer_website=job_link or f"https://www.jobstreet.com.sg/{job_title.replace(' ', '-').lower()}-jobs",
                                ats_keywords=extract_ats_keywords(f"{title_text} {company_text}"),
                                source="JobStreet"
                            )
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Error parsing JobStreet job card: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"Error loading JobStreet page: {str(e)}")
            
            await browser.close()
        
        logger.info(f"Scraped {len(jobs)} real jobs from JobStreet")
        
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
