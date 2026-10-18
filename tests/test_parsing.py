from bot.parsing import parse_fields


def test_parse_fields():
    text = """
    логін: sasha@gmail.com
    пароль:qwe:rty
    https://diia.gov.ua/login
    сайт: https://example.com
    зустріч о 10:30
    просто нотатка
    """
    assert parse_fields(text) == [
        {"key": "логін", "value": "sasha@gmail.com"},
        {"key": "пароль", "value": "qwe:rty"},
        {"key": "посилання", "value": "https://diia.gov.ua/login"},
        {"key": "сайт", "value": "https://example.com"},
        {"key": "нотатка", "value": "зустріч о 10:30"},
        {"key": "нотатка", "value": "просто нотатка"},
    ]


def test_parse_empty():
    assert parse_fields("\n  \n") == []
