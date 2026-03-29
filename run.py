import os
from dotenv import load_dotenv
load_dotenv()   # must be before create_app so env vars are available

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV", "production") == "development"
    app.run(debug=debug, host="127.0.0.1", port=5001)
