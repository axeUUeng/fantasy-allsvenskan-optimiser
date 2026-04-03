import fantasy_optimizer.db.models  # noqa: F401 — registers all ORM models with Base
from fantasy_optimizer.db.database import Base, engine

Base.metadata.create_all(engine)
print("Tables created successfully")
