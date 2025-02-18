from flask import Flask
from slackeventsapi import SlackEventAdapter
from api.config import SLACK_SIGNING_SECRET
from api.bot import SlackTranslateBot

def create_app():
    app = Flask(__name__)
    
    bot = SlackTranslateBot()
    
    slack_events_adapter = SlackEventAdapter(
        SLACK_SIGNING_SECRET,
        '/api/slack/events',
        app
    )
    
    @slack_events_adapter.on("message")
    def handle_message(event_data):
        """Event handler for messages"""
        bot.handle_message(event_data["event"])
    
    @app.route("/", methods=['GET'])
    def home():
        return "Translation Bot server-side is running!"
    
    return app