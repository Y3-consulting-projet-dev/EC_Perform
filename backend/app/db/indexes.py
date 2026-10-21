from pymongo import ASCENDING, DESCENDING

from app.db.session import db


def create_indexes():
    """Index des collections de la Phase 4/5. Idempotent : appelé au démarrage de l'API et par
    le script create_indexes.py. Les index uniques garantissent qu'un cycle n'a qu'un seul
    document de révision et qu'une étape n'a qu'un seul papier de travail, même en cas de
    création concurrente."""
    db.cycle_revisions.create_index([("missionId", ASCENDING), ("code", ASCENDING)], unique=True)
    db.review_points.create_index([("missionId", ASCENDING), ("cycleCode", ASCENDING), ("statut", ASCENDING)])
    db.working_papers.create_index(
        [("missionId", ASCENDING), ("cycleCode", ASCENDING), ("etape", ASCENDING)], unique=True
    )
    db.working_paper_versions.create_index([("paperId", ASCENDING), ("version", DESCENDING)])
