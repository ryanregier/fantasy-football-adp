import pandas as pd
import requests
import plotly
import json

def fetch_espn_players(limit=50, start_offset=0, cookies=None):
    espn_url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2025/segments/0/leaguedefaults/3?view=kona_player_info"
    print("Fetching ESPN ADPs")
    all_players = []
    offset = start_offset

    while True:
        print(offset)
        fantasy_filter = {
            "players": {
            "filterStatsForExternalIds": {"value": [2024, 2025]},
            "filterSlotIds": {"value": [0,1,2,3,4,5,6,7,8,9,10,
                                        11,12,13,14,15,16,17,18,19,23,24]},
            "filterStatsForSourceIds": {"value": [0, 1]},
            "sortAppliedStatTotal": {"sortAsc": False, "sortPriority": 3, "value": "102025"},
            "sortDraftRanks": {"sortPriority": 2, "sortAsc": True, "value": "PPR"},
            "sortPercOwned": {"sortAsc": False, "sortPriority": 4},
            "limit": limit,
            "offset": offset,
            "filterRanksForScoringPeriodIds": {"value": [1]},
            "filterRanksForRankTypes": {"value": ["PPR"]},
            "filterRanksForSlotIds": {"value": [0,2,4,6,17,16,8,9,10,12,13,24,11,14,15]},
            "filterStatsForTopScoringPeriodIds": {
                "value": 2,
                "additionalValue": ["002025","102025","002024","022025"]
            }
        }
    }
        headers = {
            "accept": "application/json",
            "referer": "https://fantasy.espn.com/",
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "x-fantasy-filter": json.dumps(fantasy_filter),
            "x-fantasy-platform": "kona-PROD-1eb11d9ef8e2d38718627f7aae409e9065630000",
            "x-fantasy-source": "kona"
        }

        response = requests.get(espn_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        players = data.get("players", [])
        if not players:
            break

        all_players.extend(players)
        offset += limit
        # print(f"Fetched {len(players)} players; offset now {offset}")

        if len(players) < limit:
            # Likely reached the end
            break
        time.sleep(0.1)
    print("Fetched ESPN data")
    return all_players

def fetch_yahoo_players(count=50):
    yahoo_url = (
        "https://pub-api-ro.fantasysports.yahoo.com/fantasy/v2/"
        "league/461.l.public;out=settings/"
        "players;position=ALL;start={start};count={count};"
        "sort=average_pick;search=;out=auction_values,ranks;"
        "ranks=season;ranks_by_position=season;out=expert_ranks;"
        "expert_ranks.rank_type=projected_season_remaining/"
        "draft_analysis;cut_types=diamond;slices=last7days"
        "?format=json_f"
    )
    all_players = []
    start = 0
    
    while True:
        url = yahoo_url.format(start=start, count=count)
        print(f"Fetching {count} players starting at {start}...")
        
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        players = data['fantasy_content']['league']['players']
        
        all_players.extend(players)
        # Stop when fewer than 'count' players are returned
        if len(players) < count:  # minus the "count" key
            break
        
        start += count
    
    return all_players


def generate_dataframe():
    sleeper_url = "https://api.sleeper.com/projections/nfl/2025?season_type=regular&position[]=DEF&position[]=K&position[]=QB&position[]=RB&position[]=TE&position[]=WR&order_by=adp_std"
    res = requests.get(sleeper_url)
    df_sleeper = pd.DataFrame(res.json())
    df_sleeper['Player'] = df_sleeper['player'].apply(lambda x: f"{x.get('first_name')} {x.get('last_name')}")
    df_sleeper['Position'] = df_sleeper['player'].apply(lambda x: x.get('fantasy_positions')[0] if len(x.get('fantasy_positions')) == 1 else ", ".join(map(str, x.get('fantasy_positions'))))
    df_sleeper["SLEEPER_ADP_PPR"] = df_sleeper['stats'].apply(lambda x: x.get('adp_ppr'))
    df_sleeper['injury_status'] = df_sleeper['player'].apply(lambda x: x.get('injury_status'))
    df_sleeper['yoe'] = df_sleeper['player'].apply(lambda x: x.get('years_exp'))
    df_sleeper = df_sleeper[['Player', 'Position', 'team', 'injury_status', 'yoe', 'SLEEPER_ADP_PPR']]
    df_sleeper["SLEEPER_ADP_PPR"] = pd.to_numeric(df_sleeper["SLEEPER_ADP_PPR"], errors="coerce")
    df_sleeper = df_sleeper.dropna(subset=["SLEEPER_ADP_PPR"])
    print("Generated sleeper")
    
    data = fetch_players()
    df_espn = pd.DataFrame(data)
    df_espn['ESPN_PPR_ADP'] = df_espn['player'].apply(lambda x: unpack_espn_adp(x))
    df_espn['Player'] = df_espn['player'].apply(lambda x: f"{x.get('firstName')} {x.get('lastName')}")
    df_espn = df_espn[['Player', 'ESPN_PPR_ADP']]
    df_espn["ESPN_PPR_ADP"] = pd.to_numeric(df_espn["ESPN_PPR_ADP"], errors="coerce")
    df_espn = df_espn.dropna(subset=["ESPN_PPR_ADP"])
    print("Generated ESPN")
    
    players = fetch_yahoo_players(100)
    df_yahoo = pd.DataFrame(players)
    df_yahoo['Player'] = df_yahoo['player'].apply(lambda x: f"{x['name']['first']} {x['name']['last']}")
    df_yahoo['YAHOO_Standard_ADP'] = df_yahoo['player'].apply(lambda x: x['draft_analysis']['average_pick'])
    df_yahoo = df_yahoo[['Player', 'YAHOO_Standard_ADP']]
    df_yahoo["YAHOO_Standard_ADP"] = pd.to_numeric(df_yahoo["YAHOO_Standard_ADP"], errors="coerce")
    df_yahoo = df_yahoo.dropna(subset=["YAHOO_Standard_ADP"])
    print("Generated Yahoo")
    
    df_merged = (
        df_sleeper
        .merge(df_espn, on="Player", how="outer")
        .merge(df_yahoo, on="Player", how="outer")
    )
    df_merged = df_merged.sort_values(by=['SLEEPER_ADP_PPR'], ascending=True)
    df_merged['Custom_ADP'] = round(df_merged['SLEEPER_ADP_PPR']*0.75 + df_merged['ESPN_PPR_ADP']*0.15 + df_merged['YAHOO_Standard_ADP']*0.1, 3)
    return df_merged

import dash
from dash import Dash, dash_table, html
import pandas as pd



# Generate data
df = generate_dataframe()

# Initialize app
app = Dash(__name__)

# Layout
app.layout = html.Div([
    html.H2("Fantasy Football ADP Comparison"),
    
    dash_table.DataTable(
        id="table",
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        filter_action="native",   # enables filtering
        sort_action="native",     # enables sorting
        sort_mode="multi",        # allows sorting by multiple columns
        page_action="native",     # enables pagination
        page_size=30,              # number of rows per page
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Arial"
        },
        style_header={
            "backgroundColor": "lightgrey",
            "fontWeight": "bold"
        }
    )
])

if __name__ == "__main__":
    app.run_server(debug=True)
	