import os
from pathlib import Path

import uvicorn

DB_PATH = Path(__file__).with_name("seafarer.db")
os.environ["SEAFARER_DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"

from app.main import create_app
from app.models import Base


def ensure_fresh_demo_database():
    from app.database import create_engine_from_url

    engine = create_engine_from_url(os.environ["SEAFARER_DATABASE_URL"])
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


ensure_fresh_demo_database()
app = create_app(
    database_url=os.environ["SEAFARER_DATABASE_URL"],
    create_tables=False,
    seed_demo=True,
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)
