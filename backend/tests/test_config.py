from app.config import Settings


def test_cors_origin_list_parses_comma_separated_values():
    s = Settings(cors_origins="http://a.test, http://b.test ,")
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]


def test_defaults_target_local_postgres():
    assert Settings().database_url.startswith("postgresql+psycopg://")
