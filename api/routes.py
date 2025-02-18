from flask import Flask
from slackeventsapi import SlackEventAdapter
from api.config import SLACK_SIGNING_SECRET

def create_app():
    app = Flask(__name__)
    
    slack_events_adapter = SlackEventAdapter(
        SLACK_SIGNING_SECRET,
        '/api/slack/events',
        app
    )
    
    @slack_events_adapter.on("message")
    def handle_message(event_data):
        """Event handler for messages"""
    
    @app.route("/", methods=['GET'])
    def home():
        return "Translation Bot server-side is running!"
    
    return app