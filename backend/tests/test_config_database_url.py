from app.config import Settings


def test_plain_postgresql_url_is_rewritten_for_psycopg():
    settings = Settings(database_url="postgresql://user:pass@db.example.com:5432/bep")
    assert settings.database_url == "postgresql+psycopg://user:pass@db.example.com:5432/bep"


def test_postgres_scheme_is_rewritten_for_psycopg():
    settings = Settings(database_url="postgres://user:pass@db.example.com/bep")
    assert settings.database_url == "postgresql+psycopg://user:pass@db.example.com/bep"


def test_psycopg_url_is_left_unchanged():
    url = "postgresql+psycopg://bep:bep@localhost:5432/bep"
    assert Settings(database_url=url).database_url == url
