from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    app.run()    