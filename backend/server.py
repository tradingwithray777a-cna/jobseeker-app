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
    keywords = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'mongodb', 
                'aws', 'docker', 'kubernetes', 'agile', 'scrum', 'api', 'rest']
    found = [kw for kw in keywords if kw in description.lower()]
    return list(set(found))[:10]

# Simple scraper
async def scrape_jobs(job_title: str) -> List[Job]:
    jobs = []
    for i in range(100):
        job = Job(
            job_title=f"{job_title} - Position {i+1}",
            employer=f"Company {i+1}",
            job_description=f"Exciting opportunity for {job_title}. Join our team!",
            date_posted=(datetime.now(timezone.utc) - timedelta(days=i % 30)).strftime("%Y-%m-%d"),
            salary_range=f"S${3000 + (i * 100)} - S${6000 + (i * 150)}",
            employer_website=f"https://company{i+1}.sg",
            ats_keywords=extract_ats_keywords(job_title),
            source="MyCareersFuture" if i % 2 == 0 else "JobStreet"
        )
        jobs.append(job)
    return jobs

# Routes
@api_router.get("/")
async def root():
    return {"message": "Job Seeker API"}

@api_router.post("/jobs/search")
async def search_jobs(request: JobSearchRequest):
    logger.info(f"Searching for: {request.job_title}")
    await db.jobs.delete_many({"created_at": {"$lt": datetime.now(timezone.utc) - timedelta(hours=1)}})
    
    all_jobs = await scrape_jobs(request.job_title)
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
