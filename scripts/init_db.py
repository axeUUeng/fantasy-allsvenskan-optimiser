from fantasy_optimizer.db.database import Base, engine

Base.metadata.create_all(engine)
print("Tables created successfully")
