from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import quote
from datetime import datetime

def extract_keywords(text):
    keywords = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws']
    found = [kw for kw in keywords if kw.lower() in text.lower()]
    return list(set(found))[:10]

async def scrape_mcf(job_title):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        url = f"https://www.mycareersfuture.gov.sg/search?search={quote(job_title)}"
        await page.goto(url, timeout=30000)
        await asyncio.sleep(3)
        
        job_elements = await page.query_selector_all('div[id^="job-card"]')
        
        for elem in job_elements[:50]:
            try:
                title_elem = await elem.query_selector('h3, a')
                company_elem = await elem.query_selector('[class*="company"]')
                salary_elem = await elem.query_selector('[class*="salary"]')
                
                title = await title_elem.inner_text() if title_elem else ""
                company = await company_elem.inner_text() if company_elem else ""
                salary = await salary_elem.inner_text() if salary_elem else "Competitive"
                
                if title and company:
                    jobs.append({
                        "job_title": title.strip(),
                        "employer": company.strip(),
                        "salary_range": salary.strip(),
                        "source": "MyCareersFuture",
                        "date_posted": datetime.now().strftime("%Y-%m-%d"),
                        "job_description": f"Position at {company}",
                        "employer_website": url,
                        "ats_keywords": extract_keywords(f"{title} {company}")
                    })
            except:
                continue
        
        await browser.close()
    return jobs

async def scrape_jobstreet(job_title):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        url = f"https://www.jobstreet.com.sg/{job_title.replace(' ', '-').lower()}-jobs"
        await page.goto(url, timeout=30000)
        await asyncio.sleep(3)
        
        job_elements = await page.query_selector_all('article[data-testid="job-card"]')
        
        for elem in job_elements[:50]:
            try:
                title_elem = await elem.query_selector('h1, h2, a')
                company_elem = await elem.query_selector('[data-automation*="company"]')
                salary_elem = await elem.query_selector('[class*="salary"]')
                
                title = await title_elem.inner_text() if title_elem else ""
                company = await company_elem.inner_text() if company_elem else ""
                salary = await salary_elem.inner_text() if salary_elem else "Competitive"
                
                if title and company:
                    jobs.append({
                        "job_title": title.strip(),
                        "employer": company.strip(),
                        "salary_range": salary.strip(),
                        "source": "JobStreet",
                        "date_posted": datetime.now().strftime("%Y-%m-%d"),
                        "job_description": f"Opportunity at {company}",
                        "employer_website": url,
                        "ats_keywords": extract_keywords(f"{title} {company}")
                    })
            except:
                continue
        
        await browser.close()
    return jobs

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        job_title = data.get('job_title', '')
        
        if not job_title:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "job_title required"}).encode())
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        mcf_jobs, js_jobs = loop.run_until_complete(asyncio.gather(
            scrape_mcf(job_title),
            scrape_jobstreet(job_title)
        ))
        
        all_jobs = mcf_jobs + js_jobs
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "success": True,
            "count": len(all_jobs),
            "jobs": all_jobs
        }
        
        self.wfile.write(json.dumps(response).encode())
