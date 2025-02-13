import os
from slack_sdk import WebClient
from pathlib import Path
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from slack_sdk.errors import SlackApiError
from flask import Flask, request, Response
import json

# Load environment variables
env_path = Path('..') / '.env'
load_dotenv(env_path)

app = Flask(__name__)

class SlackTranslateBot:
    def __init__(self):
        self.client = WebClient(token=os.environ['SLACK_TOKEN'])
        self.translator = GoogleTranslator(source='auto', target='en')
        
        self.token = os.environ.get('SLACK_TOKEN')
        if not self.token:
            raise ValueError("SLACK_TOKEN environment variable is not set")
        
        self.signing_secret = os.environ.get('SLACK_SIGNING_SECRET')
        if not self.signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET environment variable is not set")
        
        self.supported_languages = {
            'en': 'English',
            'ja': 'Japanese',
            'si': 'Sinhala',
            'ta': 'Tamil',
            'ko': 'Korean',
            'zh': 'Chinese (Simplified)',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'ru': 'Russian',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'pt': 'Portuguese',
            'vi': 'Vietnamese',
            'th': 'Thai'
        }
        
        self.user_languages = {}
    
    def handle_message(self, text, channel_id, user_id):
        """Handle incoming message events"""
        try:
            if not text:
                return
            
            print("user: ", user_id)
            target_lang = 'en'

            translated = self.translator.translate(text)
            print(translated)
                
            self.client.chat_postMessage(
                channel=channel_id,
                text=f"{text} \n\nTranslation ({self.supported_languages[target_lang]}):\n```{translated}```"
            )
                
        except Exception as e:
            print(f"Error handling message: {e}")
            
        
@app.route('/slack/translate', methods=['POST'])
def slash_command():
    """Handle Slash Commands"""
    try: 
        data = request.form
    except Exception as e:
        print(f"Error parsing form data: {e}")
        return Response('Error parsing form data'), 400
    
    bot = SlackTranslateBot()
    bot.handle_message(data['text'], data['channel_id'], data['user_id'])
    
    return Response(), 200


@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    app.run()    