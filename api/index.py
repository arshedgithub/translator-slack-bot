import os
from slack_sdk import WebClient
from pathlib import Path
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from slack_sdk.errors import SlackApiError
from flask import Flask, request, Response
from langdetect import detect, LangDetectException
from slackeventsapi import SlackEventAdapter

env_path = Path('.') / '.env'
load_dotenv(env_path)

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(
    os.environ.get('SLACK_SIGNING_SECRET'),
    '/api/slack/events',
    app
)

class SlackTranslateBot:
    def __init__(self):
        self.token = os.environ.get('SLACK_TOKEN')
        self.signing_secret = os.environ.get('SLACK_SIGNING_SECRET')
        
        if not self.token:
            raise ValueError("SLACK_TOKEN environment variable is not set")
        if not self.signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET environment variable is not set")
            
        self.client = WebClient(token=self.token)
        self.BOT_ID = self.client.auth_test()['user_id']
        self.processed_messages = set()

    def translate_message(self, text, source_lang, target_lang):
        """Translate text from source_lang to target_lang"""
        if source_lang == target_lang:
            return None
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = translator.translate(text)
            print(f"Translated from {source_lang} to {target_lang}: {translated}")
            return translated
        except Exception as e:
            print(f"Translation error: {e}")
            return None
    
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
            sender_id = event_data.get('user', '')
            
            if sender_id == self.BOT_ID:
                return
            
            message_key = f"{channel_id}-{message_ts}"
            if message_key in self.processed_messages:
                return
            self.processed_messages.add(message_key)
            
            try:
                source_lang = detect(text)
                print(f"Detected language: {source_lang}")

                if source_lang == 'ja':
                    translated_text = self.translate_message(text, 'ja', 'en')
                elif source_lang == 'en':
                    translated_text = self.translate_message(text, 'en', 'ja')
                else:
                    print("Message is neither Japanese nor English. No translation needed.")
                    return

                if translated_text:
                    try:
                        response = self.client.chat_postMessage(
                            channel=channel_id,
                            thread_ts=message_ts,
                            text=f"Translated:\n```{translated_text}```"
                        )
                        print(f"Posted translation message: {response}")
                    except SlackApiError as e:
                        print(f"Error posting translation: {e}")
                    
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
    
@app.route("/", methods=['GET'])
def get():
    return "Tranlation Bot server-side is running!"

if __name__ == "__main__":
    if os.environ.get("VERCEL_ENV") != "production":
        app.run(debug=True)

handler = app  # vercel entry point