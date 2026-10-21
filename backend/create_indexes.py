from app.db.indexes import create_indexes
from app.db.session import db

create_indexes()
print(f"Index créés sur la base '{db.name}' (cycle_revisions, review_points, working_papers, working_paper_versions)")
