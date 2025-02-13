# api/index.py
import os
from slack_sdk import WebClient
from pathlib import Path
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from slack_sdk.errors import SlackApiError
from flask import Flask, request, Response
import json

# Initialize Flask
app = Flask(__name__)

class SlackTranslateBot:
    def __init__(self):
        self.token = os.environ.get('SLACK_TOKEN')
        if not self.token:
            raise ValueError("SLACK_TOKEN environment variable is not set")
            
        self.client = WebClient(token=self.token)
        self.translator = GoogleTranslator(source='auto', target='en')
        
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
    
    def handle_message(self, text, channel_id, user_id):
        """Handle incoming message events"""
        try:
            if not text:
                return False, "No text provided"
            
            print(f"Processing message from user: {user_id}")
            print(f"Channel: {channel_id}")
            print(f"Text: {text}")
            
            target_lang = 'en'
            
            try:
                translated = self.translator.translate(text)
                print(f"Translation: {translated}")
                
                response = self.client.chat_postMessage(
                    channel=channel_id,
                    text=f"{text}\n\nTranslation ({self.supported_languages[target_lang]}):\n```{translated}```"
                )
                return True, "Translation posted successfully"
                
            except Exception as e:
                print(f"Translation error: {e}")
                return False, f"Translation error: {str(e)}"
                
        except Exception as e:
            print(f"Message handling error: {e}")
            return False, f"Message handling error: {str(e)}"

@app.route('/api/slack/translate', methods=['POST'])
def slash_command():
    """Handle Slack slash commands"""
    try:
        print("Received request")
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        
        if request.content_type == 'application/json':
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        print(f"Request data: {data}")
        
        if not data:
            return Response("No data received", status=400)
            
        bot = SlackTranslateBot()
        
        success, message = bot.handle_message(
            text=data.get('text', ''),
            channel_id=data.get('channel_id'),
            user_id=data.get('user_id')
        )
        
        if success:
            return Response(message, status=200)
        else:
            return Response(message, status=400)
            
    except Exception as e:
        print(f"Slash command error: {e}")
        return Response(f"Error processing command: {str(e)}", status=500)

@app.route('/api/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}

@app.route('/', methods=['GET'])
def home():
    return "Slack Translator Bot is running!"
