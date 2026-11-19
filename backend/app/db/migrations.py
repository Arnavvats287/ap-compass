"""Small additive SQLite migration. No populated table is recreated or rewritten."""
from sqlalchemy import text
from .models import ReviewAction

VERSION = '002-human-po-review'


def migrate(engine):
    with engine.begin() as connection:
        # CREATE IF NOT EXISTS is safe on old installations and repeated startup.
        connection.execute(text('CREATE TABLE IF NOT EXISTS schema_migration (version TEXT PRIMARY KEY)'))
        ReviewAction.__table__.create(connection,checkfirst=True)
        connection.execute(text("""CREATE TRIGGER IF NOT EXISTS review_action_no_update
            BEFORE UPDATE ON review_action BEGIN SELECT RAISE(ABORT, 'Review actions are append-only'); END"""))
        connection.execute(text("""CREATE TRIGGER IF NOT EXISTS review_action_no_delete
            BEFORE DELETE ON review_action BEGIN SELECT RAISE(ABORT, 'Review actions are append-only'); END"""))
        connection.execute(text("""CREATE TRIGGER IF NOT EXISTS review_action_no_replace
            BEFORE INSERT ON review_action
            WHEN EXISTS (SELECT 1 FROM review_action WHERE id=NEW.id OR run_id=NEW.run_id)
            BEGIN SELECT RAISE(ABORT, 'Review actions are append-only'); END"""))
        connection.execute(text('INSERT OR IGNORE INTO schema_migration(version) VALUES (:version)'),{'version':VERSION})
