"""
Quick smoke-test for DataService (Football-Data.org v4).

Run from project root:
    python app/test_data_service.py
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

from app.services.DataService import DataService, WC_CODE, COMPETITION_CODES


async def main() -> None:
    svc = DataService()
    await svc.initialize()

    try:
        # 1. Health check
        print("\n── Health Check ──")
        healthy = await svc.health_check()
        print(f"Healthy: {healthy}")

        # 2. World Cup competition info
        print("\n── WC 2026 Competition ──")
        comp = await svc.get_competition(WC_CODE)
        print(f"Name   : {comp.get('name')}")
        print(f"Area   : {comp.get('area', {}).get('name')}")
        print(f"Season : {comp.get('currentSeason', {}).get('startDate')} → {comp.get('currentSeason', {}).get('endDate')}")

        # 3. WC 2026 teams
        print("\n── WC 2026 Teams ──")
        teams = await svc.get_world_cup_teams()
        print(f"Total teams: {len(teams)}")
        for t in teams[:5]:
            print(f"  {t.get('name')} ({t.get('tla')})")
        if len(teams) > 5:
            print(f"  … and {len(teams) - 5} more")

        # 4. WC 2026 group stage matches
        print("\n── WC 2026 Group Stage Matches ──")
        group_matches = await svc.get_world_cup_matches(stage="GROUP_STAGE")
        print(f"Total group stage matches: {len(group_matches)}")
        for m in group_matches[:3]:
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            date = m["utcDate"][:10]
            status = m["status"]
            score = m.get("score", {}).get("fullTime", {})
            print(f"  {home} vs {away}  |  {date}  |  {status}  |  {score}")

        # 5. WC 2026 standings
        print("\n── WC 2026 Standings ──")
        standings = await svc.get_world_cup_standings()
        tables = standings.get("standings", [])
        print(f"Standing tables returned: {len(tables)}")
        if tables:
            first_table = tables[0]
            print(f"Type : {first_table.get('type')} | Stage: {first_table.get('stage')}")
            for row in first_table.get("table", [])[:3]:
                team = row["team"]["name"]
                pts = row["points"]
                print(f"  {row['position']}. {team} — {pts} pts")

        # 6. WC 2026 top scorers
        print("\n── WC 2026 Top Scorers ──")
        scorers = await svc.get_world_cup_top_scorers(limit=5)
        if scorers:
            for s in scorers:
                name = s["player"]["name"]
                goals = s.get("goals", 0)
                team = s["team"]["name"]
                print(f"  {name} ({team}) — {goals} goals")
        else:
            print("  No scorer data yet.")

        # 7. Today's matches across all competitions
        print("\n── Today's Matches (all competitions) ──")
        today = await svc.list_matches()
        print(f"Matches today: {len(today)}")
        for m in today[:3]:
            home = m["homeTeam"]["shortName"]
            away = m["awayTeam"]["shortName"]
            comp_name = m.get("competition", {}).get("name", "?")
            print(f"  {home} vs {away}  [{comp_name}]")

        # 8. Competition code reference
        print("\n── Competition Code Reference ──")
        for code, id_ in list(COMPETITION_CODES.items())[:5]:
            print(f"  {code} → {id_}")

    finally:
        await svc.close()
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
