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
    # Updated schema to store per-user settings
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings
        (user_id TEXT PRIMARY KEY, preferred_language TEXT DEFAULT 'en')
    ''')
    conn.commit()
    conn.close()

@lru_cache(maxsize=1000)
def get_user_language(user_id):
    conn = sqlite3.connect('translator_settings.db')
    c = conn.cursor()
    c.execute('SELECT preferred_language FROM user_settings WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'en'

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
        self.supported_languages = GoogleTranslator().get_supported_languages(as_dict=True)
        self.translators = {}
        init_db()

    def open_settings_modal(self, trigger_id, user_id):
        current_language = get_user_language(user_id)
        
        common_languages = {
            'en': 'English',
            'ja': 'Japanese',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'id': 'Indonesian',
            'ms': 'Malay'
        }
        
        options = [
            {
                "text": {
                    "type": "plain_text",
                    "text": f"{name}"
                },
                "value": code
            }
            for code, name in common_languages.items()
        ]
        
        initial_option = next(
            (opt for opt in options if opt["value"] == current_language),
            options[0]
        )

        modal_payload = {
            "type": "modal",
            "callback_id": "language_settings",
            "private_metadata": user_id,
            "title": {
                "type": "plain_text",
                "text": "Translation Settings",
                "emoji": True
            },
            "submit": {
                "type": "plain_text",
                "text": "Save",
                "emoji": True
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel",
                "emoji": True
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Choose your preferred language for translations:"
                    }
                },
                {
                    "type": "input",
                    "block_id": "preferred_language",
                    "element": {
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a language",
                            "emoji": True
                        },
                        "options": options,
                        "initial_option": initial_option,
                        "action_id": "language_select"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Preferred Language",
                        "emoji": True
                    }
                }
            ]
        }

        try:
            self.client.views_open(
                trigger_id=trigger_id,
                view=modal_payload
            )
        except SlackApiError as e:
            print(f"Error opening modal: {e.response['error']}")
            raise e

    def get_translator(self, target_lang):
        if target_lang not in self.translators:
            self.translators[target_lang] = GoogleTranslator(source='auto', target=target_lang)
        return self.translators[target_lang]

    def translate_for_user(self, text, source_lang, target_lang):
        """Synchronous translation function"""
        if source_lang == target_lang:
            return None
        try:
            translator = self.get_translator(target_lang)
            translated = translator.translate(text)
            print(f"Translated to {target_lang}: {translated}")
            return translated
        except Exception as e:
            print(f"Translation error for {target_lang}: {e}")
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

                try:
                    response = self.client.conversations_members(channel=channel_id)
                    members = response['members']
                    print(f"Channel members: {members}")
                except SlackApiError as e:
                    print(f"Error getting channel members: {e}")
                    return

                translations = {}
                # Process translations for each member
                for member_id in members:
                    if member_id == self.BOT_ID:
                        continue
                        
                    target_lang = get_user_language(member_id)
                    print(f"Processing member {member_id}, target language: {target_lang}")
                    
                    if source_lang != target_lang and target_lang not in translations:
                        translated = self.translate_for_user(text, source_lang, target_lang)
                        if translated:
                            translations[target_lang] = translated
                            print(f"Added translation for {target_lang}: {translated}")

                if not translations:
                    print("No translations generated")
                    return

                translation_text = f"{text}\n\n"
                for lang, translated in translations.items():
                    translation_text += f"🌐 {lang.upper()}:\n```{translated}```\n"

                print(f"Final translation text: {translation_text}")

                try:
                    response = self.client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=message_ts,
                        text=translation_text
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

@app.route('/api/slack/commands', methods=['POST'])
def handle_command():
    """Handle slash commands from Slack"""
    try:
        if request.form.get('command') == '/translate-settings':
            trigger_id = request.form.get('trigger_id')
            user_id = request.form.get('user_id')
            
            if not trigger_id or not user_id:
                return Response("Missing required data", status=400)
            
            bot.open_settings_modal(trigger_id, user_id)
            return Response("Opening translation settings...", status=200)
            
        return Response("Unknown command", status=400)
        
    except Exception as e:
        print(f"Error handling command: {e}")
        return Response(f"Error: {str(e)}", status=500)
    
@app.route('/api/slack/interactions', methods=['POST'])
def handle_interaction():
    """Handle interactions from modals and other interactive components"""
    try:
        payload = json.loads(request.form.get('payload', '{}'))
        print("Received interaction payload:", json.dumps(payload, indent=2))

        if payload.get('type') == 'view_submission' and \
           payload.get('view', {}).get('callback_id') == 'language_settings':
            selected_language = payload['view']['state']['values']['preferred_language']['language_select']['selected_option']['value']
            user_id = payload['view']['private_metadata']
            print("selected_language: ", selected_language)
            print("User: ", user_id)

            conn = sqlite3.connect('translator_settings.db')
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO user_settings (user_id, preferred_language)
                VALUES (?, ?)
            ''', (user_id, selected_language))
            conn.commit()
            conn.close()

            get_user_language.cache_clear()

            return Response(status=200)

    except Exception as e:
        print(f"Error handling interaction: {e}")
        return Response(str(e), status=500)

    return Response("", status=200)
