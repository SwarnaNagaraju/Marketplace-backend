"""Run seed manually: python -m scripts.seed_data (from backend dir with PYTHONPATH=.)"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import connect_db, close_db
from app.utils.seed import run_seed


async def main():
    await connect_db()
    await run_seed()
    print("Seed completed.")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
