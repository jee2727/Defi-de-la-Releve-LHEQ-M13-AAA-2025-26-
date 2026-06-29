#!/usr/bin/env python3
"""
Hockey Quebec Tournament Data Scraper
Scrapes tournament game data from LHEQ Spordle platform

Tournament URL: https://masculin.lheq.ca/fr/ligue-de-hockey-d-excellence-du-quebec-masculin/schedule-stats-standings/3fb187df-fced-4d32-8e48-1b9a87fd69da?seasonId=2025-26
"""

import json
import os
import requests
import sys
from datetime import datetime
from bs4 import BeautifulSoup

class TournamentScraper:
    """Scrapes tournament data from LHEQ Spordle API"""

    def __init__(self, output_dir='web/data/games'):
        self.output_dir = output_dir
        self.base_url = "https://www.public.spordle.com/api"
        self.tournament_id = "3fb187df-fced-4d32-8e48-1b9a87fd69da"
        self.season_id = "2025-26"
        self.games = []
        self.teams = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, '..', 'gamesheets'), exist_ok=True)

    def fetch_tournament_schedule(self):
        """
        Fetch tournament schedule from LHEQ Spordle API
        """
        print("\nFetching tournament schedule...")
        
        try:
            # Try to fetch from Spordle API
            url = f"{self.base_url}/schedule"
            params = {
                'season_id': self.season_id,
                'tournament_id': self.tournament_id
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            print(f"  ✓ Retrieved {len(data.get('games', []))} games from API")
            return data.get('games', [])
            
        except Exception as e:
            print(f"  ✗ Error fetching from API: {e}")
            return []

    def create_sample_game_structure(self):
        """
        Create a sample game structure for reference
        """
        print("\nCreating sample game structure...")
        
        sample_game = {
            "id": "game_001",
            "date": "2026-01-15",
            "time": "14:00",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 3,
            "away_score": 2,
            "status": "FINAL",
            "tournament_day": 1,
            "boxscore": {
                "teams": [
                    {"id": "team_1", "name": "Team A", "logoUrl": None},
                    {"id": "team_2", "name": "Team B", "logoUrl": None}
                ],
                "goals": [],
                "penalties": []
            },
            "home_team_roster": [],
            "away_team_roster": []
        }
        
        sample_path = os.path.join(self.output_dir, '_SAMPLE_GAME_STRUCTURE.json')
        with open(sample_path, 'w', encoding='utf-8') as f:
            json.dump(sample_game, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Created sample structure at {sample_path}")

    def scrape_all(self):
        """
        Run the complete scraping process
        """
        print("="*70)
        print("HOCKEY QUEBEC TOURNAMENT DATA SCRAPER")
        print("="*70)
        
        games_from_api = self.fetch_tournament_schedule()
        
        if not games_from_api:
            print("\n⚠ Could not automatically fetch tournament data")
            self.create_sample_game_structure()
            print("\nInstructions:")
            print("-" * 70)
            print("To populate tournament data:")
            print("1. Visit: https://masculin.lheq.ca/")
            print("2. Get the 12 teams and their game results")
            print("3. Create game JSON files in web/data/games/")
            print("4. Use _SAMPLE_GAME_STRUCTURE.json as template")
            print("5. Run: python tournament_stats.py")
        else:
            print(f"\n✓ Successfully found {len(games_from_api)} games")


def main():
    try:
        scraper = TournamentScraper()
        scraper.scrape_all()
        return 0
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
