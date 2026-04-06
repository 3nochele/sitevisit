import requests
import random
import time
import csv
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

SITES_FILE = 'sites.txt'
SUMMARY_REPORT = 'report.csv'
PROBLEM_REPORT = 'detailed_status.csv'
MAX_WORKERS = 3 

SUB_PAGES = ['', '/about-us', '/contact-us']

def is_valid_url(url):
    if '.' not in url or ' ' in url or '↑' in url:
        return False
    if url.startswith(('/', '.', '#')):
        return False
    return True

def ping_url(original_url):
    url = original_url.strip()
    if not url or not is_valid_url(url):
        return None

    if not url.startswith('http'):
        formatted_url = 'http://' + url
    else:
        formatted_url = url
        
    if formatted_url.endswith('/'):
        formatted_url = formatted_url[:-1]
    
    target_url = f"{formatted_url}{random.choice(SUB_PAGES)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    
    time.sleep(random.uniform(2, 5)) 
    
    try:
        response = requests.get(target_url, headers=headers, timeout=20, allow_redirects=True)
        final_url = response.url.lower()
        
        # রিডাইরেক্ট চেক করার লজিক (HTTP থেকে HTTPS বা ডব্লিউডব্লিউডব্লিউ বাদে বড় পরিবর্তন খুঁজবে)
        history = response.history
        redirected = len(history) > 0
        
        # সাসপেন্ডেড কি না চেক
        if redirected and ("suspended" in final_url or "limit" in final_url or "notify" in final_url):
            return original_url, response.status_code, "Suspended", response.url
        
        # যদি সাকসেসফুল হয় (Status 200) কিন্তু রিডাইরেক্ট হয়ে অন্য ডোমেইনে চলে যায়
        elif redirected and response.status_code == 200:
            # শুধু স্লাশ বা http/https এর পরিবর্তন হলে সেটাকে রিডাইরেক্ট ধরবে না
            orig_clean = url.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
            final_clean = response.url.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
            
            if orig_clean != final_clean:
                return original_url, response.status_code, "Redirected", response.url
            else:
                return original_url, response.status_code, "Success", response.url
        
        elif response.status_code == 200:
            return original_url, response.status_code, "Success", response.url
        else:
            return original_url, response.status_code, f"Error_{response.status_code}", response.url
            
    except Exception:
        return original_url, 0, "Invalid/Down", "N/A"

def start_process():
    if not os.path.exists(SITES_FILE): return

    with open(SITES_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    random.shuffle(urls)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(ping_url, urls))

    results = [r for r in results if r is not None]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # রিপোর্ট ফাইল তৈরি (Final_URL কলামসহ)
    with open(PROBLEM_REPORT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Exact_URL_from_List", "Status_Code", "Issue_Type", "Final_URL", "Checked_At"])
        for url, code, status, final_u in results:
            if status != "Success":
                writer.writerow([url, code, status, final_u, now])

    success_count = sum(1 for _, _, s, _ in results if s == "Success")
    suspended_count = sum(1 for _, _, s, _ in results if s == "Suspended")
    redirect_count = sum(1 for _, _, s, _ in results if s == "Redirected")
    failed_count = len(results) - (success_count + suspended_count + redirect_count)

    file_exists = os.path.exists(SUMMARY_REPORT)
    with open(SUMMARY_REPORT, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Total", "Success", "Suspended", "Redirected", "Failed"])
        writer.writerow([now, len(results), success_count, suspended_count, redirect_count, failed_count])

if __name__ == "__main__":
    start_process()
