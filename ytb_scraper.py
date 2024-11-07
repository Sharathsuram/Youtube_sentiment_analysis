import os
import sys
import json
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pytube import YouTube
from googleapiclient.discovery import build

# Configuration
FILE_NAME = 'ytb_comments.csv'
DEBUG = True
SCROLL_PAUSE_TIME = 2
MAX_SCROLL_ATTEMPTS = 50  # Increase this for more comments

# You'll need to get this from Google Cloud Console
API_KEY = 'AIzaSyDoAUnQwlL0t38f4tOk6wB-p4tooA3Slnw'  # Replace with your API key

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG {datetime.now()}] {message}")

def get_video_id(url):
    if 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    elif 'youtube.com' in url:
        if 'v=' in url:
            return url.split('v=')[1].split('&')[0]
    return url

def get_video_info(url):
    try:
        yt = YouTube(url)
        return {
            'title': yt.title,
            'author': yt.author,
            'publish_date': yt.publish_date,
            'views': yt.views,
            'length': yt.length,
            'description': yt.description
        }
    except Exception as e:
        debug_print(f"Error getting video info: {str(e)}")
        return None

def setup_selenium():
    """Setup Selenium WebDriver with Chrome"""
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scroll_to_load_comments(driver, url):
    """Scroll the page to load more comments"""
    debug_print("Starting comment loading process...")
    
    try:
        # Load the page
        driver.get(url)
        time.sleep(SCROLL_PAUSE_TIME)  # Wait for initial load
        
        # Scroll to focus on comments section
        driver.execute_script("window.scrollTo(0, window.scrollY + 700);")
        time.sleep(SCROLL_PAUSE_TIME)
        
        comments = []
        prev_comments_count = 0
        scroll_attempts = 0
        no_new_comments_count = 0
        
        while scroll_attempts < MAX_SCROLL_ATTEMPTS:
            try:
                # Wait for comments to be visible
                comment_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-comment-thread-renderer"))
                )
                
                # Get current comments
                current_comments = []
                for comment in comment_elements:
                    try:
                        author = comment.find_element(By.CSS_SELECTOR, "#author-text").text.strip()
                        text = comment.find_element(By.CSS_SELECTOR, "#content-text").text.strip()
                        likes_element = comment.find_element(By.CSS_SELECTOR, "#vote-count-middle").text.strip()
                        likes = int(likes_element) if likes_element.isdigit() else 0
                        
                        current_comments.append({
                            'author': author,
                            'text': text,
                            'likes': likes,
                            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'replies': 0  # Default value as getting replies requires additional scrolling
                        })
                    except Exception as e:
                        debug_print(f"Error parsing comment: {str(e)}")
                        continue
                
                # Check if we got new comments
                if len(current_comments) > prev_comments_count:
                    comments = current_comments
                    prev_comments_count = len(comments)
                    no_new_comments_count = 0
                    print(f"Found {len(comments)} comments...")
                else:
                    no_new_comments_count += 1
                    if no_new_comments_count >= 3:  # If no new comments after 3 attempts, stop
                        break
                
                # Scroll to load more
                driver.execute_script(
                    "window.scrollTo(0, document.documentElement.scrollHeight);"
                )
                time.sleep(SCROLL_PAUSE_TIME)
                scroll_attempts += 1
                
            except TimeoutException:
                debug_print("Timeout while waiting for comments")
                break
            except Exception as e:
                debug_print(f"Error during scrolling: {str(e)}")
                break
        
        return comments
    
    except Exception as e:
        debug_print(f"Error in scroll_to_load_comments: {str(e)}")
        return []

def get_api_comments(video_id):
    """Get comments using YouTube Data API as backup"""
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        comments = []
        
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,
            order='relevance',
            textFormat='plainText'
        )
        
        while request:
            try:
                response = request.execute()
                items = response.get('items', [])
                
                for item in items:
                    comment = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'author': comment['authorDisplayName'],
                        'text': comment['textDisplay'],
                        'time': comment['publishedAt'],
                        'likes': comment['likeCount'],
                        'replies': item['snippet']['totalReplyCount']
                    })
                
                if 'nextPageToken' in response:
                    request = youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        pageToken=response['nextPageToken'],
                        maxResults=100,
                        textFormat='plainText'
                    )
                else:
                    request = None
                
                time.sleep(1)
            
            except Exception as e:
                debug_print(f"API error: {str(e)}")
                break
        
        return comments
    
    except Exception as e:
        debug_print(f"Error in get_api_comments: {str(e)}")
        return []

def main(url):
    try:
        debug_print(f"Starting comment collection for: {url}")
        start_time = time.time()
        
        # Get video ID and info
        video_id = get_video_id(url)
        video_info = get_video_info(url)
        if video_info:
            print("\nVideo Information:")
            print(json.dumps(video_info, indent=2, default=str))
        
        # Initialize Selenium
        print("\nInitializing browser...")
        driver = setup_selenium()
        
        # Get comments using Selenium
        print("\nFetching comments using web scraping (this may take several minutes)...")
        selenium_comments = scroll_to_load_comments(driver, url)
        
        # Get comments using API as backup
        print("\nFetching additional comments using API...")
        api_comments = get_api_comments(video_id)
        
        # Combine comments from both sources
        all_comments = selenium_comments + [
            comment for comment in api_comments 
            if not any(s_comment['text'] == comment['text'] 
                      for s_comment in selenium_comments)
        ]
        
        # Close Selenium driver
        driver.quit()
        
        if all_comments:
            # Create DataFrame
            df_comments = pd.DataFrame(all_comments)
            
            # Remove duplicates if any
            df_comments = df_comments.drop_duplicates(subset=['text', 'author'])
            
            print(f"\nTotal unique comments collected: {len(df_comments)}")
            print(f"\nComment DataFrame Preview:\n{df_comments.head()}")
            
            # Save to CSV with headers
            df_comments.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding='utf-8')
            print(f"\nComments saved to {FILE_NAME}")
        else:
            print("\nNo comments were retrieved")
        
        print(f'\n[{time.time() - start_time:.2f} seconds] Done!')
        
    except Exception as e:
        debug_print(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import selenium
        import pytube
        from googleapiclient.discovery import build
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("Installing required packages...")
        os.system('pip install selenium pytube google-api-python-client webdriver-manager')
        import selenium
        import pytube
        from googleapiclient.discovery import build
        from webdriver_manager.chrome import ChromeDriverManager

    video_url = "https://youtu.be/ST8w_7YFtOc?si=0BlbgNG0ppAkUUpE"
    main(video_url)