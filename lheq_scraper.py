#!/usr/bin/env python3

import json
import os
import requests
import urllib.parse
from datetime import datetime
from collections import defaultdict

class LHEQGameScraper:
    def __init__(self):
        self.api_base_url = "https://pub-api.play.spordle.com/api/sp/games"
        self.api_key = "f08ed9064e3cdc382e6abb305ff543d0150fb52f"
        self.headers = {
            "Authorization": f"API-Key {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json"
        }

        # Create directories for outputs
        os.makedirs("web/data/gamesheets", exist_ok=True)
        os.makedirs("web/data/games", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

    def build_api_url(self, start_date, end_date, skip=0):
        """Build the API URL with proper filters for Défi de la Relève"""
        filter_obj = {
            "order": "startTime ASC",
            "skip": skip,
            "where": {
                "and": [
                    {
                        "date": {
                            "between": [start_date, end_date]
                        }
                    },
                    {
                        "categoryId": "ba267b3e-9734-478c-a9e2-4890895cfc47"
                    },
                    {
                        "scheduleId": {
                            "inq": [182366, 183835]
                        }
                    },
                    {
                        "officeId": 9175
                    }
                ]
            },
            "include": [
                "teamStats",
                "surface",
                "office",
                "awayTeam",
                "homeTeam",
                "externalProviders"
            ]
        }

        filter_json = json.dumps(filter_obj, separators=(',', ':'))
        filter_encoded = urllib.parse.quote(filter_json)
        return f"{self.api_base_url}?filter={filter_encoded}"

    def fetch_games_for_period(self, start_date, end_date):
        """Fetch all games for a specific date range"""
        print(f"📅 Fetching games from {start_date} to {end_date}...")

        all_games = []
        skip = 0
        batch_size = 100

        while True:
            api_url = self.build_api_url(start_date, end_date, skip)

            try:
                response = requests.get(api_url, headers=self.headers, timeout=30)
                response.raise_for_status()

                data = response.json()
                games_batch = data if isinstance(data, list) else data.get('data', [])

                if not games_batch:
                    break

                all_games.extend(games_batch)
                print(f"📋 Found {len(games_batch)} games in this batch (total: {len(all_games)})")

                if len(games_batch) < batch_size:
                    break

                skip += len(games_batch)

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching games: {e}")
                break

        return all_games

    def fetch_boxscore(self, game_id):
        """Fetch detailed boxscore data for a game"""
        boxscore_url = f"{self.api_base_url}/{game_id}/boxScore"

        try:
            response = requests.get(boxscore_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching boxscore for game {game_id}: {e}")
            return None

    def fetch_game_details_with_players(self, game_id):
        """Fetch detailed game information including player lists"""
        filter_str = '{"include":["teamStats","surface","schedule",{"awayTeam":["category"]},{"homeTeam":["category"]},"category","externalProviders"]}'
        filter_encoded = urllib.parse.quote(filter_str)
        details_url = f"{self.api_base_url}/{game_id}?filter={filter_encoded}"

        try:
            response = requests.get(details_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching game details for game {game_id}: {e}")
            return None

    def fetch_team_members(self, team_id):
        """Fetch complete team roster"""
        team_filter = {
            "where": {
                "positions": {
                    "inq": ["F", "C", "D", "G"]
                },
                "teamId": int(team_id)
            }
        }

        filter_json = json.dumps(team_filter, separators=(',', ':'))
        filter_encoded = urllib.parse.quote(filter_json)
        members_url = f"https://pub-api.play.spordle.com/api/sp/members?filter={filter_encoded}"

        try:
            response = requests.get(members_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching team members for team {team_id}: {e}")
            return None

    def is_game_completed(self, game):
        """Check if a game is completed"""
        team_stats = game.get('teamStats', [])
        if not team_stats:
            return False
        for stat in team_stats:
            if stat.get('goalFor') is not None:
                return True
        return False

    def extract_scores(self, game):
        """Extract home and away scores"""
        team_stats = game.get('teamStats', [])
        home_team_id = game.get('homeTeamId')
        away_team_id = game.get('awayTeamId')

        home_score = None
        away_score = None

        for stat in team_stats:
            team_id = stat.get('teamId')
            goals = stat.get('goalFor')

            if team_id == home_team_id:
                home_score = goals
            elif team_id == away_team_id:
                away_score = goals

        return home_score, away_score

    def extract_players_from_boxscore(self, boxscore, team_name, position_filter=None):
        """Extract all players from boxscore data"""
        players = {}

        if not boxscore:
            return players

        # Handle both dict and list formats
        if isinstance(boxscore, dict):
            boxscore = boxscore.get('data', []) if 'data' in boxscore else boxscore

        if not isinstance(boxscore, list):
            return players

        for player_data in boxscore:
            try:
                player_name = player_data.get('playerName', '').strip()
                player_number = player_data.get('playerNumber', 0)
                position = player_data.get('position', '').strip().upper()
                goals = player_data.get('goals', 0) or 0
                assists = player_data.get('assists', 0) or 0

                if not player_name or position not in ['F', 'D', 'G', 'C']:
                    continue

                if position_filter and position != position_filter:
                    continue

                player_key = f"{player_name}_{player_number}_{team_name}"

                if player_key not in players:
                    players[player_key] = {
                        'name': player_name,
                        'number': player_number,
                        'team_name': team_name,
                        'position': position,
                        'games': 1,
                        'goals': goals,
                        'assists': assists
                    }
                else:
                    players[player_key]['goals'] += goals
                    players[player_key]['assists'] += assists
                    players[player_key]['games'] += 1

            except Exception as e:
                print(f"⚠️ Error processing player data: {e}")
                continue

        return players

    def save_individual_game_file(self, game_data):
        """Save individual game data to JSON file"""
        game_id = game_data.get('id')
        filename = f"web/data/games/game_{game_id}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, indent=2, ensure_ascii=False)
            print(f"   💾 Game data saved: {filename}")
            return filename
        except Exception as e:
            print(f"   ⚠️ Error saving game file: {e}")
            return None

    def compile_player_statistics(self, all_games):
        """Compile all player statistics from games"""
        print(f"\n🔍 Compiling player statistics from {len(all_games)} games...")

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

        game_count = 0

        for game in all_games:
            try:
                if not self.is_game_completed(game):
                    continue

                game_id = game.get('id')
                home_team = game.get('homeTeam', {}).get('name', 'Unknown')
                away_team = game.get('awayTeam', {}).get('name', 'Unknown')

                print(f"\n📊 Processing game {game_count + 1}: {away_team} vs {home_team}")

                # Fetch boxscore for this game
                boxscore = self.fetch_boxscore(game_id)
                if not boxscore:
                    print(f"   ⚠️ No boxscore data available")
                    continue

                # Extract home team players
                if isinstance(boxscore, dict) and 'homeTeam' in boxscore:
                    home_players = boxscore.get('homeTeam', [])
                    for player_data in home_players:
                        try:
                            name = player_data.get('playerName', '').strip()
                            number = player_data.get('playerNumber', 0)
                            position = player_data.get('position', '').strip().upper()
                            goals = player_data.get('goals', 0) or 0
                            assists = player_data.get('assists', 0) or 0

                            if name and position in ['F', 'D', 'G', 'C']:
                                player_key = f"{name}_{number}_{home_team}"
                                if player_key not in all_players:
                                    all_players[player_key] = {
                                        'name': name,
                                        'number': number,
                                        'team_name': home_team,
                                        'position': 'F' if position in ['F', 'C'] else position,
                                        'games_played': 0,
                                        'goals': 0,
                                        'assists': 0,
                                        'penalty_minutes': 0
                                    }

                                all_players[player_key]['games_played'] += 1
                                all_players[player_key]['goals'] += goals
                                all_players[player_key]['assists'] += assists
                        except Exception as e:
                            continue

                # Extract away team players
                if isinstance(boxscore, dict) and 'awayTeam' in boxscore:
                    away_players = boxscore.get('awayTeam', [])
                    for player_data in away_players:
                        try:
                            name = player_data.get('playerName', '').strip()
                            number = player_data.get('playerNumber', 0)
                            position = player_data.get('position', '').strip().upper()
                            goals = player_data.get('goals', 0) or 0
                            assists = player_data.get('assists', 0) or 0

                            if name and position in ['F', 'D', 'G', 'C']:
                                player_key = f"{name}_{number}_{away_team}"
                                if player_key not in all_players:
                                    all_players[player_key] = {
                                        'name': name,
                                        'number': number,
                                        'team_name': away_team,
                                        'position': 'F' if position in ['F', 'C'] else position,
                                        'games_played': 0,
                                        'goals': 0,
                                        'assists': 0,
                                        'penalty_minutes': 0
                                    }

                                all_players[player_key]['games_played'] += 1
                                all_players[player_key]['goals'] += goals
                                all_players[player_key]['assists'] += assists
                        except Exception as e:
                            continue

                game_count += 1

            except Exception as e:
                print(f"⚠️ Error processing game: {e}")
                continue

        # Convert to list and sort by points (goals + assists), then by goals
        players_list = list(all_players.values())
        players_list.sort(key=lambda x: (-x['goals'] - x['assists'], -x['goals']))

        # Add points field
        for player in players_list:
            player['points'] = player['goals'] + player['assists']

        print(f"\n✅ Compiled {len(players_list)} unique players from {game_count} completed games")

        return players_list

    def save_players_json(self, players):
        """Save compiled player statistics to JSON"""
        filename = "data/players.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
            print(f"💾 Player statistics saved to: {filename}")
            print(f"📊 Total players: {len(players)}")
            if players:
                print(f"🏆 Top scorer: {players[0]['name']} ({players[0]['points']} pts)")
            return filename
        except Exception as e:
            print(f"❌ Error saving players file: {e}")
            return None

    def run(self, start_date, end_date):
        """Main execution flow"""
        print(f"\n🏒 LHEQ GAME DATA SCRAPER")
        print(f"📅 Date Range: {start_date} to {end_date}")
        print("=" * 70)

        try:
            # Fetch all games
            api_games = self.fetch_games_for_period(start_date, end_date)

            if not api_games:
                print("❌ No games found")
                return

            print(f"\n✅ Found {len(api_games)} total games")

            # Process each game and save
            completed_games = []
            for i, game in enumerate(api_games, 1):
                try:
                    game_id = game.get('id')
                    home_team = game.get('homeTeam', {}).get('name', 'Unknown')
                    away_team = game.get('awayTeam', {}).get('name', 'Unknown')

                    if not self.is_game_completed(game):
                        print(f"⏭️ [{i}/{len(api_games)}] Game {game_id} is SCHEDULED - skipping")
                        continue

                    print(f"\n🎮 [{i}/{len(api_games)}] Processing: {away_team} vs {home_team}")

                    # Fetch boxscore
                    boxscore = self.fetch_boxscore(game_id)
                    if boxscore:
                        game['boxscore'] = boxscore
                        print(f"   ✅ Boxscore fetched")

                    completed_games.append(game)

                except Exception as e:
                    print(f"⚠️ Error processing game {game_id}: {e}")
                    continue

            print(f"\n✅ Total completed games: {len(completed_games)}")

            # Compile player statistics
            players = self.compile_player_statistics(completed_games)

            # Save to JSON
            self.save_players_json(players)

            print(f"\n🏆 SCRAPING COMPLETE!")
            return players

        except Exception as e:
            print(f"❌ Scraper error: {e}")
            return []


if __name__ == "__main__":
    import sys

    scraper = LHEQGameScraper()

    # Parse command line arguments
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
        print(f"Using custom date range: {start_date} to {end_date}")
        scraper.run(start_date, end_date)
    else:
        # Default to May 2026 (tournament dates)
        print("Using default date range: May 2026")
        scraper.run("2026-05-01", "2026-05-31")
