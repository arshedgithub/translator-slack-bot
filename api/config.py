import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('.') / '.env'
load_dotenv(env_path)

SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')

if not SLACK_TOKEN:
    raise ValueError("SLACK_TOKEN environment variable is not set")
if not SLACK_SIGNING_SECRET:
    raise ValueError("SLACK_SIGNING_SECRET environment variable is not set")