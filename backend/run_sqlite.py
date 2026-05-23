import os
import uvicorn

os.environ["SEAFARER_DATABASE_URL"] = "sqlite:///./seafarer.db"

from app.main import create_app

app = create_app(database_url=os.environ["SEAFARER_DATABASE_URL"], create_tables=True, seed_demo=True)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)
