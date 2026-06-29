#!/usr/bin/env python3
"""
Hockey Quebec Tournament Data Scraper
Scrapes the Défi de la Relève M13 AAA 2025-26 tournament data from LHEQ

Tournament URL: https://masculin.lheq.ca/fr/ligue-de-hockey-d-excellence-du-quebec-masculin/schedule-stats-standings/3fb187df-fced-4d32-8e48-1b9a87fd69da?seasonId=2025-26
"""

import json
import os
import requests
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import re
import time

class TournamentScraper:
    """Scrapes tournament data from LHEQ Spordle API"""

    def __init__(self, output_dir='web/data/games'):
        self.output_dir = output_dir
        self.tournament_id = "3fb187df-fced-4d32-8e48-1b9a87fd69da"
        self.season_id = "2025-26"
        self.games = []
        self.teams = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, '..', 'gamesheets'), exist_ok=True)

    def fetch_from_spordle_api(self):
        """
        Fetch tournament data from Spordle API
        """
        print("\n[1/3] Attempting to fetch from Spordle API...")
        
        try:
            url = "https://www.public.spordle.com/api/v2/schedule"
            params = {
                'tournament_id': self.tournament_id,
                'season': self.season_id
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            games = data.get('data', {}).get('games', [])
            
            if games:
                print(f"  ✓ Retrieved {len(games)} games from Spordle API")
                return games
            else:
                print("  ✗ No games found in API response")
                return []
            
        except Exception as e:
            print(f"  ✗ Error fetching from API: {e}")
            return []

    def fetch_from_web(self):
        """
        Scrape tournament data directly from LHEQ website
        """
        print("\n[2/3] Attempting to scrape LHEQ website...")
        
        try:
            url = "https://masculin.lheq.ca/fr/ligue-de-hockey-d-excellence-du-quebec-masculin/schedule-stats-standings/3fb187df-fced-4d32-8e48-1b9a87fd69da?seasonId=2025-26"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            print(f"  Fetching: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            games_data = []
            
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'schedule' in script.string.lower():
                    try:
                        match = re.search(r'{.*?"games".*?}', script.string, re.DOTALL)
                        if match:
                            data = json.loads(match.group())
                            if 'games' in data:
                                games_data = data['games']
                                break
                    except:
                        continue
            
            if not games_data:
                game_rows = soup.find_all('tr', class_=re.compile('game|match|schedule', re.I))
                for row in game_rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            game_info = {
                                'date': cells[0].get_text(strip=True),
                                'time': cells[1].get_text(strip=True) if len(cells) > 1 else 'TBD',
                                'home_team': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                                'away_team': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                                'score': cells[4].get_text(strip=True) if len(cells) > 4 else 'TBD',
                            }
                            if game_info['home_team'] and game_info['away_team']:
                                games_data.append(game_info)
                    except:
                        continue
            
            if games_data:
                print(f"  ✓ Found {len(games_data)} games on website")
                return games_data
            else:
                print("  ✗ Could not find game data on website")
                return []
            
        except Exception as e:
            print(f"  ✗ Error scraping website: {e}")
            return []

    def create_sample_structure(self):
        """
        Create sample game JSON structure for manual data entry
        """
        print("\n[3/3] Creating sample game structure...")
        
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
                    {
                        "id": "team_1",
                        "name": "Team A",
                        "logoUrl": None
                    },
                    {
                        "id": "team_2",
                        "name": "Team B",
                        "logoUrl": None
                    }
                ],
                "goals": [
                    {
                        "teamId": "team_1",
                        "period": 1,
                        "minute": 5,
                        "participant": {
                            "participantId": "player_1",
                            "fullName": "Player Name",
                            "number": 10
                        },
                        "assists": [
                            {
                                "participantId": "player_2",
                                "fullName": "Assister Name",
                                "number": 15
                            }
                        ],
                        "isPowerplay": False,
                        "isShorthanded": False
                    }
                ],
                "penalties": [],
                "roster": []
            },
            "home_team_roster": [],
            "away_team_roster": []
        }
        
        sample_path = os.path.join(self.output_dir, '_SAMPLE_GAME_STRUCTURE.json')
        with open(sample_path, 'w', encoding='utf-8') as f:
            json.dump(sample_game, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Created sample structure at: {sample_path}")

    def save_games(self, games):
        """
        Save game data to JSON files
        """
        if not games:
            return 0
        
        print(f"\n  Saving {len(games)} games...")
        
        saved_count = 0
        for idx, game in enumerate(games, 1):
            try:
                game_id = game.get('id', f"game_{idx:03d}")
                filename = f"{game_id}.json"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(game, f, indent=2, ensure_ascii=False)
                
                print(f"    ✓ Saved {filename}")
                saved_count += 1
            except Exception as e:
                print(f"    ✗ Error saving game {idx}: {e}")
        
        return saved_count

    def scrape_all(self):
        """
        Run the complete scraping process
        """
        print("="*70)
        print("DÉFI DE LA RELÈVE M13 AAA 2025-26 TOURNAMENT DATA SCRAPER")
        print("="*70)
        print(f"Tournament ID: {self.tournament_id}")
        print(f"Season: {self.season_id}")
        
        games = self.fetch_from_spordle_api()
        
        if not games:
            games = self.fetch_from_web()
        
        self.create_sample_structure()
        
        if games:
            saved = self.save_games(games)
            print(f"\n✓ Successfully saved {saved} games")
        else:
            print("\n⚠ Could not automatically fetch tournament data")
            print("\nManual Data Entry Instructions:")
            print("-" * 70)
            print("To populate tournament data manually:")
            print("\n1. Visit the tournament page:")
            print("   https://masculin.lheq.ca/fr/ligue-de-hockey-d-excellence-du-quebec-masculin/")
            print("   schedule-stats-standings/3fb187df-fced-4d32-8e48-1b9a87fd69da?seasonId=2025-26")
            print("\n2. For each game, create a JSON file in web/data/games/ named:")
            print("   game_001.json, game_002.json, etc.")
            print("\n3. Use _SAMPLE_GAME_STRUCTURE.json as a template")
            print("\n4. Include all game details:")
            print("   - Game ID, date, time, teams, scores")
            print("   - Players, goals, assists, penalties")
            print("   - Team rosters (optional)")
            print("\n5. Once games are added, run: python tournament_stats.py")
        
        print("\n" + "="*70)
        print("✓ SCRAPING COMPLETE")
        print("="*70)


def main():
    """Main function"""
    try:
        scraper = TournamentScraper()
        scraper.scrape_all()
        return 0
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
