""".env loader — parsing, precedence, and resilience."""
from ricdapp.env import load_env_file


def _load(tmp_path, text, env=None):
    f = tmp_path / '.env'
    f.write_text(text, encoding='utf-8')
    environ = env if env is not None else {}
    n = load_env_file(f, environ)
    return n, environ


def test_parses_values_comments_and_quotes(tmp_path):
    n, env = _load(tmp_path, """
# database section
DB_ENGINE=postgresql
DB_HOST=db.internal
DB_PASSWORD="p@ss=word"
DJANGO_DEBUG='False'

not a kv line
""")
    assert n == 4
    assert env['DB_ENGINE'] == 'postgresql'
    assert env['DB_HOST'] == 'db.internal'
    assert env['DB_PASSWORD'] == 'p@ss=word'   # quotes stripped, inner = kept
    assert env['DJANGO_DEBUG'] == 'False'


def test_existing_environment_wins(tmp_path):
    n, env = _load(tmp_path, "DB_ENGINE=postgresql\n", env={'DB_ENGINE': 'sqlite3'})
    assert n == 0
    assert env['DB_ENGINE'] == 'sqlite3'  # real env var not overwritten


def test_missing_file_is_noop(tmp_path):
    env = {}
    assert load_env_file(tmp_path / 'nope.env', env) == 0
    assert env == {}
