from app.database import postgres

def create_order() -> None:
    postgres.save()
