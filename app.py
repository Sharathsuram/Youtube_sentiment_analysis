from flask import Flask, request, jsonify, render_template
from ytb_scraper import main as scrape_comments
import pandas as pd
import google.generativeai as genai

# Initialize Flask app
app = Flask(__name__)

# Google Gemini API key
GOOGLE_API_KEY = 'AIzaSyA3fwvPcM190F3aNkPeK9AeF8hoZ51lKR4'
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Function to perform sentiment analysis
def get_sentiment(info, comment):
    prompt = f"{info} so please analyze the sentiment of this text: '{comment}'. Give answer only in one word like Positive, Negative, etc."
    try:
        response = model.generate_content(prompt)
        return response.text.strip().upper()
    except:
        return 'NEUTRAL'

# Route for homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle form submission and process YouTube comments
@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    url = data.get('url')
    info = data.get('info')

    # Scrape comments using ytb_scraper
    scrape_comments(url)

    # Load scraped comments
    comments_df = pd.read_csv('ytb_comments.csv')
    comments_df['sentiment'] = comments_df['text'].apply(lambda x: get_sentiment(info, x))

    # Calculate sentiment percentages
    sentiment_counts = comments_df['sentiment'].value_counts(normalize=True) * 100
    result = sentiment_counts.to_dict()

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
