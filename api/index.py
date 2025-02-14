import os
from slack_sdk import WebClient
from pathlib import Path
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from slack_sdk.errors import SlackApiError
from flask import Flask, request, Response
from langdetect import detect, LangDetectException
from slackeventsapi import SlackEventAdapter
import sqlite3
from functools import lru_cache
import json

env_path = Path('.') / '.env'
load_dotenv(env_path)

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(
    os.environ.get('SLACK_SIGNING_SECRET'),
    '/api/slack/events',
    app
)

def init_db():
    conn = sqlite3.connect('translator_settings.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS channel_settings
        (channel_id TEXT PRIMARY KEY, target_language TEXT DEFAULT 'en')
    ''')
    conn.commit()
    conn.close()

class SlackTranslateBot:
    def __init__(self):
        self.token = os.environ.get('SLACK_TOKEN')
        self.signing_secret = os.environ.get('SLACK_SIGNING_SECRET')
        
        if not self.token:
            raise ValueError("SLACK_TOKEN environment variable is not set")
        if not self.signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET environment variable is not set")
            
        self.client = WebClient(token=self.token)
        self.translator = GoogleTranslator(source='auto', target='en')
        
        self.BOT_ID = self.client.auth_test()['user_id']
        self.processed_messages = set()
        self.supported_languages = GoogleTranslator().get_supported_languages(as_dict=True)
        init_db()
        
    def handle_message(self, event_data):
        """Handle message events"""
        try:
            if (
                'bot_id' in event_data or 
                'subtype' in event_data or 
                event_data.get('type') != 'message'
            ):
                return
            
            text = event_data.get('text', '')
            if not text:
                return
                
            channel_id = event_data['channel']
            message_ts = event_data['ts']
            user_id = event_data.get('user', '')
            
            # Ignore translating the messages from the bot itself
            if user_id == self.BOT_ID:
                return
            
            message_key = f"{channel_id}-{message_ts}"
            if message_key in self.processed_messages:
                return
            self.processed_messages.add(message_key)
            
            try:
                source_lang = detect(text)
                print(f"Detected language: {source_lang}")
                
                if source_lang != 'en':
                    translated = self.translator.translate(text)
                    print(f"Translated text: {translated}")
                    
                    try:
                        self.client.chat_update(
                            channel=channel_id,
                            ts=message_ts,
                            text=f"{text}\n\n🌐 English:\n```{translated}```"
                        )
                    except SlackApiError as e:
                        if e.response['error'] == 'cant_update_message':
                            self.client.chat_postMessage(
                                channel=channel_id,
                                thread_ts=message_ts,
                                text=f"🌐 English:\n```{translated}```"
                            )
                        else:
                            raise e
                    
            except LangDetectException as e:
                print(f"Language detection error: {e}")
            except Exception as e:
                print(f"Translation error: {e}")
                
        except Exception as e:
            print(f"Error handling message: {e}")


bot = SlackTranslateBot()

@slack_events_adapter.on("message")
def handle_message(event_data):
    """Event handler for messages"""
    bot.handle_message(event_data["event"])

@app.route('/api/slack/interactions', methods=['POST'])
def handle_interaction():
    """Handle interactions from modals and other interactive components"""
    try:
        payload = request.form.get('payload')
        print("json payload: ", payload)
        if not payload:
            return Response("Invalid payload", status=400)
        
        payload = json.loads(payload)
        
    except Exception as e:
        print(f"Error parsing payload: {e}")
        return Response("Invalid payload", status=400)
    
    # print("payload", payload)    
    # if not payload:
    #     return Response("Invalid payload", status=400)
    
    return Response("", status=200)

@app.route('/api/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}

@app.route('/', methods=['GET'])
def home():
    return "Slack Translator Bot is running!"


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True)