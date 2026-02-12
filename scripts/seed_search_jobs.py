#!/usr/bin/env python3
"""Seed default search jobs for AI in higher education policy research."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine, Base
from app.models.search_job import SearchJob

SEEDS = [
    {
        "name": "AI Academic Integrity",
        "query": "AI artificial intelligence academic integrity plagiarism detection higher education policy 2024 2025",
    },
    {
        "name": "AI in Teaching & Learning",
        "query": "generative AI teaching learning pedagogy higher education faculty guidelines",
    },
    {
        "name": "AI Institutional Policy",
        "query": "university college AI policy governance framework responsible use guidelines",
    },
    {
        "name": "AI & Student Assessment",
        "query": "AI assessment evaluation student work grading higher education policy",
    },
    {
        "name": "AI Ethics in Education",
        "query": "AI ethics bias fairness equity higher education research",
    },
    {
        "name": "AI Literacy & Workforce",
        "query": "AI literacy skills workforce preparation higher education curriculum",
    },
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    created = 0
    for seed in SEEDS:
        existing = db.query(SearchJob).filter(SearchJob.name == seed["name"]).first()
        if not existing:
            db.add(SearchJob(**seed))
            created += 1
    db.commit()
    print(f"Seeded {created} search jobs ({len(SEEDS) - created} already existed).")
    db.close()


if __name__ == "__main__":
    main()
