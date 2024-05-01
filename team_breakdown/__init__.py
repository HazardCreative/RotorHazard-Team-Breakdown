''' Class ranking method: Team Breakdown '''

import logging
import RHUtils
import copy
from eventmanager import Evt
from RHRace import StartBehavior
from Results import RaceClassRankMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

def team_breakdown(rhapi, race_class, args):
    method = args.get('method')

    results = rhapi.db.raceclass_results(race_class)
    leaderboard = copy.deepcopy(results['by_race_time'])

    stat = args.get('stat') + '_raw'

    teams = []
    num_teams = int(args.get('teams', 2))
    for _ in range(num_teams):
        teams.append({
            'time': 0,
            'lb_lines': []
        })

    if method == 'all':

        stat_total = 0
        for line in leaderboard:
            stat_total += line[stat]

        pilotsets = []
        for pilotset in range(2 ** len(leaderboard)):
            pilots_selected = []
            for x in range(len(leaderboard)):
                if pilotset & (2 ** x) != 0:
                    pilots_selected.append(x)

            time = 0
            for x in pilots_selected:
                time += leaderboard[x][stat]

            pilotsets.append({
                'set': pilots_selected,
                'time': time
            })


        if num_teams == 2:
            pilotsets = sorted(pilotsets, key=lambda x: abs(x['time'] - (stat_total / num_teams)))

            for idx, line in enumerate(leaderboard):
                if idx in pilotsets[0]['set']:
                    teams[0]['time'] += line[stat]
                    teams[0]['lb_lines'].append(line)
                else:
                    teams[1]['time'] += line[stat]
                    teams[1]['lb_lines'].append(line)
        else:
            # can't use this method with >2 pilots
            return False, {}

    elif method == 'bin':
        # binning
        for line in reversed(leaderboard):
            selected_team = teams[0]

            selected_team['time'] += line[stat]
            selected_team['lb_lines'].append(line)

            teams = sorted(teams, key = lambda x: (x['time']))

    else:
        return False, {}

    display_lb = []
    for idx, team in enumerate(teams):
        for line in team['lb_lines']:
            line['position'] = rhapi.__("Team") + " {}".format(idx)
            line['time'] = line[args.get('stat')]
            display_lb.append(line)

    display_lb.append({
        'position': '-',
        'callsign': '-',
        'time': '-',
    })

    timeFormat = rhapi.config.get_item('UI', 'timeFormat')

    for idx, team in enumerate(teams):
        line = {}
        line['position'] = rhapi.__("Team") + " {}".format(idx)
        line['callsign'] = RHUtils.time_format(team['time'], timeFormat)
        line['time'] = RHUtils.time_format(team['time'] - teams[0]['time'], timeFormat)
        display_lb.append(line)

    meta = {
        'method_label': F"Breakdown by {args.get('stat')}",
        'rank_fields': [{
            'name': 'time',
            'label': "Time"
        }]
    }

    return display_lb, meta

def register_handlers(args):
    args['register_fn'](
        RaceClassRankMethod(
            "Team Breakdown",
            team_breakdown,
            {
                'method': 'bin',
                'teams': 2,
                'stat': 'fastest_lap',
            },
            [
                UIField('method', "Method", UIFieldType.SELECT, options=[
                        UIFieldSelectOption('bin', "Fast / O(n)"),
                        UIFieldSelectOption('all', "Most Accurate / O(2^n)"),
                    ], value='bin'),
                UIField('teams', "Number of teams", UIFieldType.BASIC_INT, placeholder="2"),
                UIField('stat', "Stat", UIFieldType.SELECT, options=[
                    UIFieldSelectOption('fastest_lap', "Fastest Lap"),
                    UIFieldSelectOption('average_lap', "Average Lap"),
                    UIFieldSelectOption('consecutives', "Consecutives"),
                    UIFieldSelectOption('total_time_laps', "Total Time"),
                ], value='fastest_lap'),

                # UIField('max_pilots', "Maximum pilots per team", UIFieldType.BASIC_INT, placeholder="Auto"),
            ]
        )
    )

def initialize(rhapi):
    rhapi.events.on(Evt.CLASS_RANK_INITIALIZE, register_handlers)

