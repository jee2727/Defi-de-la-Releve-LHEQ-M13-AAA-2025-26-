#!/usr/bin/env python3
"""
Tournament Statistics Compiler
Compiles game data and generates tournament statistics
"""

import json
import os
from collections import defaultdict
from pathlib import Path

class TournamentCompiler:
    """Compiles tournament statistics from game files"""
    
    def __init__(self, games_dir='web/data/games', output_dir='web/data'):
        self.games_dir = games_dir
        self.output_dir = output_dir
        self.games = []
        self.teams = {}
        self.players = {}
        
    def load_games(self):
        """Load all game JSON files"""
        print("\n[1/4] Loading game files...")
        
        games_path = Path(self.games_dir)
        game_files = sorted(games_path.glob('game_*.json'))
        
        for game_file in game_files:
            try:
                with open(game_file, 'r', encoding='utf-8') as f:
                    game = json.load(f)
                    self.games.append(game)
            except Exception as e:
                print(f"  ✗ Error loading {game_file.name}: {e}")
        
        print(f"  ✓ Loaded {len(self.games)} games")
        return len(self.games)
    
    def compile_standings(self):
        """Calculate team standings from games"""
        print("\n[2/4] Compiling team standings...")
        
        # Initialize all teams
        team_names = set()
        for game in self.games:
            team_names.add(game['home_team'])
            team_names.add(game['away_team'])
        
        for team_name in sorted(team_names):
            self.teams[team_name] = {
                'name': team_name,
                'games_played': 0,
                'wins': 0,
                'losses': 0,
                'ties': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goal_differential': 0,
                'points': 0
            }
        
        # Process each game
        for game in self.games:
            home_team = game['home_team']
            away_team = game['away_team']
            home_score = game['home_score']
            away_score = game['away_score']
            
            # Update games played and goals
            self.teams[home_team]['games_played'] += 1
            self.teams[home_team]['goals_for'] += home_score
            self.teams[home_team]['goals_against'] += away_score
            
            self.teams[away_team]['games_played'] += 1
            self.teams[away_team]['goals_for'] += away_score
            self.teams[away_team]['goals_against'] += home_score
            
            # Calculate wins/losses/ties
            if home_score > away_score:
                self.teams[home_team]['wins'] += 1
                self.teams[away_team]['losses'] += 1
                self.teams[home_team]['points'] += 2
            elif away_score > home_score:
                self.teams[away_team]['wins'] += 1
                self.teams[home_team]['losses'] += 1
                self.teams[away_team]['points'] += 2
            else:
                self.teams[home_team]['ties'] += 1
                self.teams[away_team]['ties'] += 1
                self.teams[home_team]['points'] += 1
                self.teams[away_team]['points'] += 1
            
            # Calculate goal differential
            self.teams[home_team]['goal_differential'] = self.teams[home_team]['goals_for'] - self.teams[home_team]['goals_against']
            self.teams[away_team]['goal_differential'] = self.teams[away_team]['goals_for'] - self.teams[away_team]['goals_against']
        
        # Sort by points (descending)
        sorted_teams = sorted(self.teams.values(), key=lambda x: (-x['points'], -x['goal_differential']))
        
        print(f"  ✓ Calculated standings for {len(sorted_teams)} teams")
        return sorted_teams
    
    def compile_players(self):
        """Compile player statistics from games"""
        print("\n[3/4] Compiling player statistics...")
        
        players = []
        
        for game in self.games:
            boxscore = game.get('boxscore', {})
            goals = boxscore.get('goals', [])
            
            for goal in goals:
                try:
                    player_info = goal.get('participant', {})
                    player_name = player_info.get('fullName', 'Unknown')
                    player_number = player_info.get('number', 0)
                    team_id = goal.get('teamId', '')
                    
                    # Find team name from teams dict
                    team_name = None
                    for team_id_key, team_name_val in zip(['sagueneens_m13', 'drakkar_m13', 'armada_m13', 'remparts_m13', 
                                                            'olympiques_m13', 'tigres_m13', 'huskies_m13', 'oceanic_m13',
                                                            'foreurs_m13', 'cataractes_m13', 'phoenix_m13', 'voltigeurs_m13'],
                                                          ['Sagueneens DR M13', 'Drakkar DR M13', 'Armada DR M13', 'Remparts DR M13',
                                                           'Olympiques DR M13', 'Tigres DR M13', 'Huskies DR M13', 'Oceanic DR M13',
                                                           'Foreurs DR M13', 'Cataractes DR M13', 'Phoenix DR M13', 'Voltigeurs DR M13']):
                        if team_id == team_id_key:
                            team_name = team_name_val
                            break
                    
                    # Count assists
                    assists = len(goal.get('assists', []))
                    
                    # Find or create player record
                    player_found = False
                    for p in players:
                        if p['name'] == player_name and p['team_name'] == team_name:
                            p['goals'] += 1
                            p['assists'] += assists
                            p['points'] = p['goals'] + p['assists']
                            player_found = True
                            break
                    
                    if not player_found and team_name:
                        players.append({
                            'name': player_name,
                            'number': player_number,
                            'team_name': team_name,
                            'position': 'F',  # Default to Forward
                            'games_played': 1,
                            'goals': 1,
                            'assists': assists,
                            'points': 1 + assists,
                            'penalty_minutes': 0
                        })
                except Exception as e:
                    continue
        
        print(f"  ✓ Compiled statistics for {len(players)} players")
        return players
    
    def save_standings(self, standings):
        """Save standings to JSON file"""
        standings_path = os.path.join(self.output_dir, 'teams.json')
        with open(standings_path, 'w', encoding='utf-8') as f:
            json.dump(standings, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved standings to {standings_path}")
    
    def save_players(self, players):
        """Save player stats to JSON file"""
        players_path = os.path.join(self.output_dir, 'players.json')
        
        # If no players yet, create placeholder
        if not players:
            players = [{
                'name': 'Player data pending',
                'number': 0,
                'team_name': 'TBD',
                'position': 'F',
                'games_played': 0,
                'goals': 0,
                'assists': 0,
                'points': 0,
                'penalty_minutes': 0
            }]
        
        with open(players_path, 'w', encoding='utf-8') as f:
            json.dump(players, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved players to {players_path}")
    
    def compile_all(self):
        """Run complete compilation"""
        print("="*70)
        print("TOURNAMENT STATISTICS COMPILER")
        print("Défi de la Relève M13 AAA 2025-26")
        print("="*70)
        
        # Load games
        game_count = self.load_games()
        
        if game_count == 0:
            print("\n✗ No games found. Please add game files to web/data/games/")
            return False
        
        # Compile standings
        standings = self.compile_standings()
        
        # Compile players
        players = self.compile_players()
        
        # Save files
        print("\n[4/4] Saving compiled data...")
        self.save_standings(standings)
        self.save_players(players)
        
        # Display standings
        print("\n" + "="*70)
        print("TOURNAMENT STANDINGS")
        print("="*70)
        print(f"{'Rank':<5} {'Team':<25} {'GP':<3} {'W':<3} {'L':<3} {'T':<3} {'GF':<3} {'GA':<3} {'Pts':<3}")
        print("-"*70)
        
        for idx, team in enumerate(standings, 1):
            print(f"{idx:<5} {team['name']:<25} {team['games_played']:<3} {team['wins']:<3} {team['losses']:<3} {team['ties']:<3} {team['goals_for']:<3} {team['goals_against']:<3} {team['points']:<3}")
        
        print("\n" + "="*70)
        print("✓ COMPILATION COMPLETE")
        print("="*70)
        
        return True


def main():
    try:
        compiler = TournamentCompiler()
        compiler.compile_all()
        return 0
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
