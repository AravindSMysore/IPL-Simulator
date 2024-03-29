import pandas as pd
import pickle
from tqdm import tqdm
from Utils.helper import Innings, display_batting_table
import itertools
import random
from IPython.display import display
from Utils.sample_squads import (
    CSK_Squad, CSK_Pitch, RCB_Squad,
    RCB_Pitch, RR_Squad, RR_Pitch,
    MI_Squad, MI_Pitch, SRH_Squad,
    SRH_Pitch, DC_Squad, DC_Pitch,
    KXIP_Squad, KXIP_Pitch, KKR_Squad,
    KKR_Pitch)


with open('Data/BF_Cols.pkl', 'rb') as fp:
    BF_Cols = pickle.load(fp)
with open('Data/BS_Cols.pkl', 'rb') as fp:
    BS_Cols = pickle.load(fp)


class EvaluationMetrics():
    def __init__(self, model_inn1, model_inn2, load_path=None, step=5):
        self.bowler_stat = {}
        self.batsmen_stat = {}
        self.step = step
        self.models = [model_inn1, model_inn2]
        self.progression_stat = {
            "runs": [[] for _ in range(int(20/self.step))],
            "wickets": [[] for _ in range(int(20/self.step))],
        }
        self.total_stat = []
        self.innings_obj_list = []

        self.teams = [[CSK_Squad, CSK_Pitch],
                      [RCB_Squad, RCB_Pitch],
                      [RR_Squad, RR_Pitch],
                      [MI_Squad, MI_Pitch],
                      [SRH_Squad, SRH_Pitch],
                      [DC_Squad, DC_Pitch],
                      [KXIP_Squad, KXIP_Pitch],
                      [KKR_Squad, KKR_Pitch],
                      ]
        table_keys = ["Played", "Wins", "Losses", "Points",
                      "ByRuns", "ByBalls", "AgRuns", "AgBalls"]
        self.season_table = {
            'Chennai Super Kings': {i: 0 for i in table_keys},
            'Royal Challengers Bangalore': {i: 0 for i in table_keys},
            'Rajasthan Royals': {i: 0 for i in table_keys},
            'Mumbai Indians': {i: 0 for i in table_keys},
            'Sunrisers Hyderabad': {i: 0 for i in table_keys},
            'Delhi Capitals': {i: 0 for i in table_keys},
            'Kings XI Punjab': {i: 0 for i in table_keys},
            'Kolkata Knight Riders': {i: 0 for i in table_keys},
        }
        self.old_season_tables = []
        self.match_count = 0
        self.form_matches()

        if load_path is not None:
            self.load_object(load_path)

    def load_object(self, load_path):
        with open(load_path, "rb") as fp:
            saved_evaluator = pickle.load(fp)
        self.bowler_stat = saved_evaluator["bowler_stat"]
        self.batsmen_stat = saved_evaluator["batsmen_stat"]
        self.progression_stat = saved_evaluator["progression_stat"]
        self.total_stat = saved_evaluator["total_stat"]
        self.innings_obj_list = saved_evaluator["innings_obj_list"]
        self.teams = saved_evaluator["teams"]
        self.season_table = saved_evaluator["season_table"]
        if "old_season_tables" in saved_evaluator:
            self.old_season_tables = saved_evaluator["old_season_tables"]
        self.matches = saved_evaluator["matches"]
        self.match_count = saved_evaluator["match_count"]

    def save_object(self, save_path):
        save_evaluator = {}
        save_evaluator["bowler_stat"] = self.bowler_stat
        save_evaluator["batsmen_stat"] = self.batsmen_stat
        save_evaluator["progression_stat"] = self.progression_stat
        save_evaluator["total_stat"] = self.total_stat
        save_evaluator["innings_obj_list"] = self.innings_obj_list
        save_evaluator["teams"] = self.teams
        save_evaluator["season_table"] = self.season_table
        save_evaluator["old_season_tables"] = self.old_season_tables
        save_evaluator["matches"] = self.matches
        save_evaluator["match_count"] = self.match_count
        with open(save_path, "wb") as fp:
            pickle.dump(save_evaluator, fp)

    def simulate_innings(self, batting_lineup, bowling_lineup,
                         toss_team, venue, innings=1, target=0, verbose=0):
        if innings == 1:
            inn_df = pd.DataFrame(columns=BF_Cols)
        elif innings == 2:
            inn_df = pd.DataFrame(columns=BS_Cols)
        else:
            assert False, "innings should be '1' or '2'"
        inn = Innings(batting_lineup, bowling_lineup, toss_team,
                      venue, innings, inn_df, target)
        simulation_ret = inn.simulate_inning(self.models[innings - 1])
        btl = inn.Batting_lineup
        bwl = inn.Bowling_lineup

        for i in btl:
            if (i.Entered_Match):
                batsman_dict = {
                    "Runs": i.Runs,
                    "Fours": i.Fours_Hit,
                    "Sixes": i.Sixes_Hit,
                    "Balls Faced": i.Balls,
                    "Dismissal Type": (i.Dismissal
                                       if i.Dismissal else 'Not Out'),
                    "Dismissed By": i.Dismissal_By if i.Dismissal_By else "-"
                }
                if i.Name in self.batsmen_stat:
                    self.batsmen_stat[i.Name].append(batsman_dict)
                else:
                    self.batsmen_stat[i.Name] = [batsman_dict]
        for i in set(bwl):
            bowling_dict = {"Runs Conceded": i.Runs_Conceded,
                            "Wickets Taken": len(i.Wickets_Taken),
                            "Balls": 6*(i.Overs_Bowled)+(i.Balls_Bowled)
                            }
            if i.Name in self.bowler_stat:
                self.bowler_stat[i.Name].append(bowling_dict)
            else:
                self.bowler_stat[i.Name] = [bowling_dict]

        progression_score_lis = [0 for _ in range(int(20/self.step))]
        progression_wicket_lis = [0 for _ in range(int(20/self.step))]
        count = 0
        for i in inn.Overs_Summary:
            ind = count//self.step
            progression_score_lis[ind] += i[0]
            progression_wicket_lis[ind] += i[1]
            if (count + 1)//self.step != ind:
                self.progression_stat["runs"][ind].append(
                    progression_score_lis[ind])
                self.progression_stat["wickets"][ind].append(
                    progression_wicket_lis[ind])
            count += 1
        if innings == 1:
            self.total_stat.append(inn.Runs)
            self.innings_obj_list.append([inn])
        elif innings == 2:
            self.innings_obj_list[-1].append(inn)
        if verbose:
            display_batting_table(inn, display_level=verbose-1)
        return (inn.Runs, self.get_balls(inn), simulation_ret
                if innings == 2 else None)

    def form_matches(self):
        self.match_count = 0
        combinations = list(itertools.combinations(
            [i for i in range(len(self.teams))], 2))
        self.matches = []
        for comb in combinations:
            self.matches.append(
                [[self.teams[comb[0]][0], self.teams[comb[1]][0]],
                    self.teams[comb[0]][1]]
            )
            self.matches.append(
                [[self.teams[comb[0]][0], self.teams[comb[1]][0]],
                    self.teams[comb[1]][1]],
            )
        random.shuffle(self.matches)
        for match in self.matches:
            random.shuffle(match[0])

    def display_table(self):
        display_dic = {}
        table_cols = ["Played", "Wins", "Losses", "Points"]
        for team in self.season_table:
            team_dic = self.season_table[team]
            display_dic[team] = {col: team_dic[col] for col in table_cols}
            byrr = (team_dic["ByRuns"] / team_dic["ByBalls"] * 6
                    if team_dic["ByBalls"] != 0 else 0)
            agrr = (team_dic["AgRuns"] / team_dic["AgBalls"] * 6
                    if team_dic["AgBalls"] != 0 else 0)
            display_dic[team]["NRR"] = byrr - agrr
        points_table_df = pd.DataFrame.from_dict(
            display_dic, orient='index').sort_values(by=["Points", "NRR"],
                                                     ascending=False)
        display(points_table_df)

    def reinitialize_tournament(self):
        self.old_season_tables.append(self.season_table)
        table_keys = ["Played", "Wins", "Losses", "Points",
                      "ByRuns", "ByBalls", "AgRuns", "AgBalls"]
        self.season_table = {
            'Chennai Super Kings': {i: 0 for i in table_keys},
            'Royal Challengers Bangalore': {i: 0 for i in table_keys},
            'Rajasthan Royals': {i: 0 for i in table_keys},
            'Mumbai Indians': {i: 0 for i in table_keys},
            'Sunrisers Hyderabad': {i: 0 for i in table_keys},
            'Delhi Capitals': {i: 0 for i in table_keys},
            'Kings XI Punjab': {i: 0 for i in table_keys},
            'Kolkata Knight Riders': {i: 0 for i in table_keys},
        }
        self.form_matches()

    def simulate_match(self, verbose=0):
        if self.match_count >= len(self.matches):
            print("All Matches in the series are over")
            return
        match = self.matches[self.match_count]
        self.match_count += 1
        toss = random.choice([0, 1])
        inn1_score, inn1_balls, _ = self.simulate_innings(
            match[0][0][0], match[0][1][1],
            match[0][toss][0][0], match[1], 1, verbose=verbose)

        (inn2_score, inn2_balls,
            (ret_str, inn2_ret)) = self.simulate_innings(
            match[0][1][0], match[0][0][1],
            match[0][toss][0][0], match[1], 2,
            inn1_score+1, verbose=verbose)
        self.season_table[match[0][0][0][0]]["ByRuns"] += inn1_score
        self.season_table[match[0][0][0][0]]["ByBalls"] += inn1_balls
        self.season_table[match[0][1][0][0]]["AgRuns"] += inn1_score
        self.season_table[match[0][1][0][0]]["AgBalls"] += inn1_balls
        self.season_table[match[0][1][0][0]]["ByRuns"] += inn2_score
        self.season_table[match[0][1][0][0]]["ByBalls"] += inn2_balls
        self.season_table[match[0][0][0][0]]["AgRuns"] += inn2_score
        self.season_table[match[0][0][0][0]]["AgBalls"] += inn2_balls
        self.season_table[match[0][0][0][0]]["Played"] += 1
        self.season_table[match[0][1][0][0]]["Played"] += 1
        if inn2_ret == 1:
            self.season_table[match[0][1][0][0]]["Points"] += 2
            self.season_table[match[0][1][0][0]]["Wins"] += 1
            self.season_table[match[0][0][0][0]]["Losses"] += 1
        elif inn2_ret == 0:
            self.season_table[match[0][0][0][0]]["Points"] += 2
            self.season_table[match[0][0][0][0]]["Wins"] += 1
            self.season_table[match[0][1][0][0]]["Losses"] += 1
        elif inn2_ret == -1:
            self.season_table[match[0][0][0][0]]["Points"] += 1
            self.season_table[match[0][1][0][0]]["Points"] += 1
        if verbose:
            print(ret_str)

    def evaluate(self):
        pass

    def get_balls(self, inn):
        o = inn.Overs - 1
        b = inn.Balls
        if (inn.Balls == 6):
            b = 0
            o += 1
        else:
            b -= 1
        return o*6 + b


class ActualStats():
    def __init__(self, load_path=None, step=5, intervals=None):
        self.BF_df = pd.read_csv("Data/Batting_First.csv")
        self.BS_df = pd.read_csv("Data/Chasing.csv")
        self.bowler_stat = {}
        self.batsmen_stat = {}
        self.step = step
        self.progression_stat = {
            "runs": [[] for _ in range(int(20/self.step))],
            "wickets": [[] for _ in range(int(20/self.step))],
        }
        if intervals is not None:
            self.intervals = intervals
        else:
            self.intervals = ((1, 6), (7, 10), (11, 15), (16, 20))
        self.new_progression_stat = {"runs": {i: [] for i in self.intervals},
                                     "wickets": {
                                         i: [] for i in self.intervals}, }
        self.over_to_interval = {}
        for interval in self.intervals:
            for i in range(interval[0], interval[1]+1):
                self.over_to_interval[i] = interval
        self.total_stat = []
        self.chasing_stat = []

        self.curr_score = None
        self.wickets = 0
        self.batsman_dict = {}
        self.bowler_dict = {}
        self.progression_subdict = None
        self.new_progression_subdict = None

        if load_path is not None:
            self.load_object(load_path)

    def load_object(self, load_path):
        with open(load_path, "rb") as fp:
            saved_evaluator = pickle.load(fp)
        self.bowler_stat = saved_evaluator["bowler_stat"]
        self.batsmen_stat = saved_evaluator["batsmen_stat"]
        self.progression_stat = saved_evaluator["progression_stat"]
        self.new_progression_stat = saved_evaluator["new_progression_stat"]
        self.total_stat = saved_evaluator["total_stat"]
        self.chasing_stat = saved_evaluator["chasing_stat"]

    def save_object(self, save_path):
        save_evaluator = {}
        save_evaluator["bowler_stat"] = self.bowler_stat
        save_evaluator["batsmen_stat"] = self.batsmen_stat
        save_evaluator["progression_stat"] = self.progression_stat
        save_evaluator["new_progression_stat"] = self.new_progression_stat
        save_evaluator["total_stat"] = self.total_stat
        save_evaluator["chasing_stat"] = self.chasing_stat
        with open(save_path, "wb") as fp:
            pickle.dump(save_evaluator, fp)

    def new_match(self, innings):
        if innings == 1 and self.curr_score is not None:
            self.total_stat.append(self.curr_score)
        for batsman_name in self.batsman_dict:
            if batsman_name not in self.batsmen_stat:
                self.batsmen_stat[batsman_name] = [
                    self.batsman_dict[batsman_name]]
            else:
                self.batsmen_stat[batsman_name].append(
                    self.batsman_dict[batsman_name])
        for bowler_name in self.bowler_dict:
            if bowler_name not in self.bowler_stat:
                self.bowler_stat[bowler_name] = [self.bowler_dict[bowler_name]]
            else:
                self.bowler_stat[bowler_name].append(
                    self.bowler_dict[bowler_name])
        if self.progression_subdict is not None:
            for key in self.progression_subdict:
                for ind, value in enumerate(self.progression_subdict[key]):
                    self.progression_stat[key][ind].append(value)
        if self.new_progression_subdict is not None:
            for key in self.new_progression_subdict:
                for interval in self.intervals:
                    if self.last_over_inn < interval[1]:
                        continue
                    self.new_progression_stat[key][interval].append(
                        self.new_progression_subdict[key][interval])

        self.curr_score = 0
        self.wickets = 0
        self.batsman_dict = {}
        self.bowler_dict = {}
        self.progression_subdict = {
            "runs": [0 for i in range(int(20/self.step))],
            "wickets": [0 for i in range(int(20/self.step))],
        }
        self.new_progression_subdict = {
            "runs": {i: 0 for i in self.intervals},
            "wickets": {i: 0 for i in self.intervals}}

    def update_dic(self, row, update_other_stats=True):
        res = row["Result"]
        if update_other_stats:
            bowler = row["Bowler"]
            batsman = row["Striker"]
            non_striker = row["Non_Striker"]
        wickets_thisball = 0
        runs_thisball = 0
        if res == 0:
            wickets_thisball = 1
            if update_other_stats:
                self.bowler_dict[bowler]["Runs Conceded"] += 0
                self.bowler_dict[bowler]["Balls"] += 1
                self.batsman_dict[batsman]["Dismissal Type"] = "Retired Hurt"

        elif 1 <= res <= 7:
            runs_thisball = res-1
            if update_other_stats:
                self.batsman_dict[batsman]["Runs"] += res-1
                self.batsman_dict[batsman]["Balls Faced"] += 1
                self.bowler_dict[bowler]["Runs Conceded"] += res-1
                self.bowler_dict[bowler]["Balls"] += 1
                if res-1 == 4:
                    self.batsman_dict[batsman]["Fours"] += 1
                elif res-1 == 6:
                    self.batsman_dict[batsman]["Sixes"] += 1

        elif 8 <= res <= 13:
            wickets_thisball = 1
            if update_other_stats:
                self.batsman_dict[batsman]["Balls Faced"] += 1
                self.bowler_dict[bowler]["Balls"] += 1
                if res != 13:
                    self.batsman_dict[batsman]["Dismissed By"] = bowler
                    self.bowler_dict[bowler]["Wickets Taken"] += 1
                if res == 8:
                    self.batsman_dict[batsman]["Dismissal Type"] = "Bowled"
                if res == 9:
                    self.batsman_dict[batsman]["Dismissal Type"] = "Caught"
                if res == 10:
                    self.batsman_dict[batsman]["Dismissal Type"] = "LBW"
                if res == 11:
                    self.batsman_dict[batsman]["Dismissal Type"] = "Stumped"
                if res == 12:
                    self.batsman_dict[batsman]["Dismissal Type"] = "Hit Wicket"
                if res == 13:
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Obstructing the Field"

        elif 50 <= res <= 54:
            runs_thisball = res-49
            if update_other_stats:
                self.bowler_dict[bowler]["Runs Conceded"] += res-49

        # No ball runs scored by byes/leg byes
        elif 46 <= res <= 49:
            runs_thisball = res-44
            if update_other_stats:
                self.bowler_dict[bowler]["Runs Conceded"] += res-44
                self.batsman_dict[batsman]["Balls Faced"] += 1

        # No ball but runs scored
        elif (40 <= res <= 45):
            runs_thisball = res-39
            if update_other_stats:
                self.batsman_dict[batsman]["Runs"] += res-40
                self.batsman_dict[batsman]["Fours"] += 1
                self.batsman_dict[batsman]["Sixes"] += 1
                self.batsman_dict[batsman]["Balls Faced"] += 1
                self.bowler_dict[bowler]["Runs Conceded"] += res-39

        # Leg byes/byes
        elif (36 <= res <= 39):
            runs_thisball = res-35
            if update_other_stats:
                self.batsman_dict[batsman]["Balls Faced"] += 1
                self.bowler_dict[bowler]["Balls"] += 1

        # Normal Runouts
        elif (14 <= res <= 21):
            wickets_thisball = 1
            # 0 runs non striker out
            if res == 14:
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

            # 0 runs striker out
            elif res == 15:
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

            # 1 run non striker out
            elif res == 16:
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman]["Runs"] += 1
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1
                    self.bowler_dict[bowler]["Runs Conceded"] += 1

            # 1 run striker out
            elif res == 17:
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman]["Runs"] += 1
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1
                    self.bowler_dict[bowler]["Runs Conceded"] += 1

            # 2 run non striker out
            elif res == 18:
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman]["Runs"] += 2
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1
                    self.bowler_dict[bowler]["Runs Conceded"] += 2

            # 2 run striker out
            elif res == 19:
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman]["Runs"] += 2
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1
                    self.bowler_dict[bowler]["Runs Conceded"] += 2

            # 3 run non striker out
            elif res == 20:
                runs_thisball = 3
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman]["Runs"] += 3
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1
                    self.bowler_dict[bowler]["Runs Conceded"] += 3

            # 3 run striker out
            elif res == 21:
                runs_thisball = 3
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman]["Runs"] += 3
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1
                    self.bowler_dict[bowler]["Runs Conceded"] += 3

        elif (34 <= res <= 35):
            runs_thisball = 1
            wickets_thisball = 1
            if update_other_stats:
                # stumped wide
                if (res == 34):
                    self.batsman_dict[batsman]["Dismissal Type"] = "Stumped"
                    self.batsman_dict[batsman]["Dismissed By"] = bowler
                    self.bowler_dict[bowler]["Runs Conceded"] += 1
                    self.bowler_dict[bowler]["Wickets Taken"] += 1

                # stumped no ball
                if (res == 35):
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Stumped"
                    self.batsman_dict[batsman]["Dismissed By"] = bowler
                    self.bowler_dict[bowler]["Runs Conceded"] += 1
                    self.bowler_dict[bowler]["Wickets Taken"] += 1

        # Leg bye/bye runnout
        elif (24 <= res <= 29):
            wickets_thisball = 1
            # Leg bye non striker runnout 1
            if (res == 24):
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

            # Leg bye striker runnout 1
            elif (res == 25):
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

            # Leg bye non striker runnout 2
            elif (res == 26):
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

            # Leg bye striker runnout 2
            elif (res == 27):
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

            # Leg bye non striker runnout 3
            elif (res == 28):
                runs_thisball = 3
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

            # Leg bye striker runnout 3
            elif (res == 29):
                runs_thisball = 3
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Balls"] += 1

        elif (30 <= res <= 33):
            wickets_thisball = 1
            # Wide, 0 actual runs runout non striker
            if (res == 30):
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 1

            elif res == 31:
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 1

            # Wide, 1 run non striker out
            elif (res == 32):
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 2

            # Wide, 1 run striker out
            elif (res == 33):
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 2

        # Noball runout
        elif (22 <= res <= 23 or 55 <= res <= 56):
            wickets_thisball = 1
            # No ball, 0 actual runs runout non striker
            if (res == 55):
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 1

            # No ball, 0 run striker out
            elif (res == 56):
                runs_thisball = 1
                if update_other_stats:
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 1

            # Noball, 1 run non striker out
            elif (res == 22):
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[batsman]["Runs"] += 1
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[non_striker][
                        "Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 2

            # Noball, 1 run striker out
            elif (res == 23):
                runs_thisball = 2
                if update_other_stats:
                    self.batsman_dict[batsman]["Runs"] += 1
                    self.batsman_dict[batsman]["Balls Faced"] += 1
                    self.batsman_dict[batsman]["Dismissal Type"] = "Run Out"
                    self.bowler_dict[bowler]["Runs Conceded"] += 2
        if update_other_stats:
            self.curr_score += runs_thisball
            self.wickets += wickets_thisball
            ind = (row["Overs"] - 1)//self.step
            self.progression_subdict["runs"][ind] += runs_thisball
            self.progression_subdict["wickets"][ind] += wickets_thisball
            self.last_over_inn = row["Overs"]
            self.new_progression_subdict[
                "runs"][self.over_to_interval[row["Overs"]]] += runs_thisball
            self.new_progression_subdict[
                "wickets"][
                    self.over_to_interval[row["Overs"]]] += wickets_thisball
        if not update_other_stats:
            return runs_thisball, wickets_thisball

    def fill_chasing_stat(self, row):
        if row is None:
            return
        ret = {}
        runs_thisball, wickets_thisball = self.update_dic(
            row, update_other_stats=False)
        final_score = row["Current_Score"] + runs_thisball
        first_innings_score = row["Target"] - 1
        ret["Final_Score"] = [final_score, row["Wickets"] + wickets_thisball]
        ret["First_Innings_Score"] = first_innings_score
        ret["Overs"] = [row["Overs"] - 1, row["Balls"]]
        ret["Chasing_Team"] = row["Batting_Team"]
        ret["Defending_Team"] = row["Bowling_Team"]
        if final_score > first_innings_score:
            outcome = 1
        elif final_score == first_innings_score:
            outcome = 0
        elif final_score < first_innings_score:
            outcome = -1
        else:
            assert False, "Wrong if conditions"
        ret["Outcome"] = outcome
        self.chasing_stat.append(ret)

    def run_df(self, innings, verbose=False):
        if innings == 1:
            df = self.BF_df
        elif innings == 2:
            df = self.BS_df
        prev_row = (None, None, None, None)
        prev_row_dic = None
        for ind, row in tqdm(df.iterrows(), ncols=80,
                             total=df.shape[0], disable=not verbose):
            curr_row = (row["Toss"], row["Venue"],
                        row["Batting_Team"], row["Bowling_Team"])
            if prev_row != curr_row:
                if innings == 2:
                    self.fill_chasing_stat(prev_row_dic)
                self.new_match(innings)
            prev_row_dic = row
            prev_row = curr_row
            if (row["Striker"] not in self.batsman_dict):
                self.batsman_dict[row["Striker"]] = {
                    "Runs": 0,
                    "Fours": 0,
                    "Sixes": 0,
                    "Balls Faced": 0,
                    "Dismissal Type": "-",
                    "Dismissed By": "-"
                }
            if (row["Non_Striker"] not in self.batsman_dict):
                self.batsman_dict[row["Non_Striker"]] = {
                    "Runs": 0,
                    "Fours": 0,
                    "Sixes": 0,
                    "Balls Faced": 0,
                    "Dismissal Type": "-",
                    "Dismissed By": "-"
                }
            if (row["Bowler"] not in self.bowler_dict):
                self.bowler_dict[row["Bowler"]] = {
                    "Runs Conceded": 0,
                    "Wickets Taken": 0,
                    "Balls": 0,
                }
            self.update_dic(row)
        if innings == 2:
            self.fill_chasing_stat(prev_row_dic)
