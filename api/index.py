import os
from api.routes import create_app

app = create_app()

if __name__ == "__main__":
    if os.environ.get("VERCEL_ENV") != "production":
        app.run(debug=True)