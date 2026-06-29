#!/usr/bin/env python3

import json
import os
from collections import defaultdict
from lheq_scraper import LHEQGameScraper

class LHEQStatsCompiler:
    def __init__(self):
        self.scraper = LHEQGameScraper()
        self.games_dir = "web/data/games"

    def load_all_game_files(self):
        """Load all game JSON files from the games directory"""
        print(f"📂 Loading all game files from {self.games_dir}...")
        
        all_games = []
        
        if not os.path.exists(self.games_dir):
            print(f"❌ Games directory not found: {self.games_dir}")
            return all_games

        game_files = sorted([f for f in os.listdir(self.games_dir) if f.startswith('game_') and f.endswith('.json')])
        print(f"📋 Found {len(game_files)} game files")

        for game_file in game_files:
            try:
                filepath = os.path.join(self.games_dir, game_file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
                    all_games.append(game_data)
                    print(f"   ✅ Loaded: {game_file}")
            except Exception as e:
                print(f"   ⚠️ Error loading {game_file}: {e}")
                continue

        return all_games

    def extract_players_from_game(self, game):
        """Extract all players from a single game's boxscore"""
        players = {}

        try:
            # Check if game is FINAL
            if game.get('status', '').upper() != 'FINAL':
                return players

            game_id = game.get('id')
            home_team = game.get('homeTeam', 'Unknown')
            away_team = game.get('awayTeam', 'Unknown')

            # Fetch boxscore for this game
            boxscore = self.scraper.fetch_boxscore(game_id)
            if not boxscore:
                return players

            # Extract home team players
            if isinstance(boxscore, dict) and 'homeTeam' in boxscore:
                home_players = boxscore.get('homeTeam', [])
                if isinstance(home_players, list):
                    for player_data in home_players:
                        try:
                            name = player_data.get('playerName', '').strip()
                            number = player_data.get('playerNumber', 0)
                            position = player_data.get('position', '').strip().upper()
                            goals = player_data.get('goals', 0) or 0
                            assists = player_data.get('assists', 0) or 0

                            if name and position in ['F', 'D', 'G', 'C']:
                                player_key = f"{name}_{number}_{home_team}"
                                
                                if player_key not in players:
                                    players[player_key] = {
                                        'name': name,
                                        'number': number,
                                        'team_name': home_team,
                                        'position': 'F' if position in ['F', 'C'] else position,
                                        'games_played': 0,
                                        'goals': 0,
                                        'assists': 0,
                                        'penalty_minutes': 0
                                    }

                                players[player_key]['games_played'] += 1
                                players[player_key]['goals'] += goals
                                players[player_key]['assists'] += assists
                        except Exception as e:
                            continue

            # Extract away team players
            if isinstance(boxscore, dict) and 'awayTeam' in boxscore:
                away_players = boxscore.get('awayTeam', [])
                if isinstance(away_players, list):
                    for player_data in away_players:
                        try:
                            name = player_data.get('playerName', '').strip()
                            number = player_data.get('playerNumber', 0)
                            position = player_data.get('position', '').strip().upper()
                            goals = player_data.get('goals', 0) or 0
                            assists = player_data.get('assists', 0) or 0

                            if name and position in ['F', 'D', 'G', 'C']:
                                player_key = f"{name}_{number}_{away_team}"
                                
                                if player_key not in players:
                                    players[player_key] = {
                                        'name': name,
                                        'number': number,
                                        'team_name': away_team,
                                        'position': 'F' if position in ['F', 'C'] else position,
                                        'games_played': 0,
                                        'goals': 0,
                                        'assists': 0,
                                        'penalty_minutes': 0
                                    }

                                players[player_key]['games_played'] += 1
                                players[player_key]['goals'] += goals
                                players[player_key]['assists'] += assists
                        except Exception as e:
                            continue

        except Exception as e:
            print(f"⚠️ Error extracting players from game {game.get('id')}: {e}")

        return players

    def compile_all_players(self, games):
        """Compile all unique players from all games"""
        print(f"\n🔍 Compiling player statistics from {len(games)} games...")

        all_players = defaultdict(lambda: {
            'name': '',
            'number': 0,
            'team_name': '',
            'position': '',
            'games_played': 0,
            'goals': 0,
            'assists': 0,
            'penalty_minutes': 0
        })

        processed_games = 0

        for i, game in enumerate(games, 1):
            try:
                if game.get('status', '').upper() != 'FINAL':
                    continue

                game_id = game.get('id')
                home_team = game.get('home_team', game.get('homeTeam', 'Unknown'))
                away_team = game.get('away_team', game.get('awayTeam', 'Unknown'))

                print(f"\n📊 [{i}/{len(games)}] Processing: {away_team} vs {home_team} (Game {game_id})")

                # Extract players from this game
                game_players = self.extract_players_from_game(game)

                # Merge into all_players
                for player_key, player_data in game_players.items():
                    if player_key not in all_players:
                        all_players[player_key] = player_data
                    else:
                        # Update existing player stats
                        all_players[player_key]['games_played'] += player_data['games_played']
                        all_players[player_key]['goals'] += player_data['goals']
                        all_players[player_key]['assists'] += player_data['assists']
                        all_players[player_key]['penalty_minutes'] += player_data.get('penalty_minutes', 0)

                print(f"   ✅ Extracted {len(game_players)} unique players")
                processed_games += 1

            except Exception as e:
                print(f"⚠️ Error processing game {game.get('id')}: {e}")
                continue

        # Convert to list
        players_list = list(all_players.values())

        # Add points field
        for player in players_list:
            player['points'] = player['goals'] + player['assists']

        # Sort by points (descending), then by goals (descending)
        players_list.sort(key=lambda x: (-x['points'], -x['goals']))

        print(f"\n✅ Compiled {len(players_list)} unique players from {processed_games} completed games")

        return players_list

    def save_players_json(self, players):
        """Save compiled player statistics to JSON"""
        filename = "data/players.json"

        try:
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Player statistics saved to: {filename}")
            print(f"📊 Total players: {len(players)}")
            
            if players:
                print(f"\n🏆 TOP 10 SCORERS:")
                for i, player in enumerate(players[:10], 1):
                    print(f"   {i}. {player['name']} ({player['team_name']}) - {player['points']} pts ({player['goals']}G, {player['assists']}A)")
            
            return filename
        except Exception as e:
            print(f"❌ Error saving players file: {e}")
            return None

    def run_full_compilation(self):
        """Run complete compilation workflow"""
        print(f"\n🏒 LHEQ STATS COMPILER")
        print("=" * 70)

        try:
            # Load all game files
            games = self.load_all_game_files()

            if not games:
                print("❌ No games found")
                return []

            print(f"\n✅ Loaded {len(games)} game files")

            # Compile player statistics
            players = self.compile_all_players(games)

            # Save to JSON
            self.save_players_json(players)

            print(f"\n🏆 COMPILATION COMPLETE!")
            return players

        except Exception as e:
            print(f"❌ Compilation error: {e}")
            return []

    def run_scrape_and_compile(self, start_date, end_date):
        """Run scraper then compile statistics"""
        print(f"\n🏒 LHEQ FULL WORKFLOW")
        print("=" * 70)

        try:
            # Step 1: Scrape games from API
            print(f"\n📥 STEP 1: Scraping games from LHEQ API")
            print(f"   Date range: {start_date} to {end_date}")
            players_from_scrape = self.scraper.run(start_date, end_date)

            # Step 2: Load and compile from game files
            print(f"\n📂 STEP 2: Compiling statistics from game files")
            games = self.load_all_game_files()
            players = self.compile_all_players(games)

            # Save final results
            self.save_players_json(players)

            print(f"\n🏆 FULL WORKFLOW COMPLETE!")
            return players

        except Exception as e:
            print(f"❌ Workflow error: {e}")
            return []


if __name__ == "__main__":
    import sys

    compiler = LHEQStatsCompiler()

    if len(sys.argv) >= 3:
        # Scrape and compile mode
        start_date = sys.argv[1]
        end_date = sys.argv[2]
        print(f"🗓️ Using custom date range: {start_date} to {end_date}")
        compiler.run_scrape_and_compile(start_date, end_date)
    elif len(sys.argv) == 2 and sys.argv[1] == "--compile-only":
        # Compile only (from existing game files)
        print("📂 Compiling from existing game files only")
        compiler.run_full_compilation()
    else:
        # Default: scrape May 2026 and compile
        print("🗓️ Using default date range: May 2026")
        compiler.run_scrape_and_compile("2026-05-01", "2026-05-31")
