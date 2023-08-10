from collections import deque
from typing import Deque, List, Optional

from aiwolf import (Agent, ComingoutContentBuilder, Content, GameInfo,
                    GameSetting, IdentContentBuilder, Judge, Role, Species,
                    Vote, VoteContentBuilder)
from aiwolf.constant import AGENT_NONE

from const import CONTENT_SKIP
from villager import HyunjiVillager


class HyunjiMedium(HyunjiVillager):
    co_date: int # Scheduled comingout date.
    found_wolf: bool # Whether a werewolf is found or not.
    has_co: bool # Bool value of whether or not comingout has done.
    my_judge_queue: Deque[Judge] # Queue of medium results.
    vote_talk: List[Vote] # Talk containing VOTE.
    voted_reports: List[Vote] # Time series of voting reports.
    request_vote_talk: List[Vote] #Talk containing REQUEST VOTE.

    def __init__(self) -> None:
        super().__init__()
        self.co_date = 0
        self.found_wolf = False
        self.has_co = False
        self.my_judge_queue = deque()
        self.vote_talk = []
        self.voted_reports = []
        self.request_vote_talk = []

    def initialize(self, game_info: GameInfo, game_setting: GameSetting) -> None:
        super().initialize(game_info, game_setting)
        self.co_date = 3
        self.found_wolf = False
        self.has_co = False
        self.my_judge_queue.clear()
        self.vote_talk.clear()
        self.voted_reports.clear()
        self.request_vote_talk.clear()

    def day_start(self) -> None:
        super().day_start()
        judge: Optional[Judge] = self.game_info.medium_result
        if judge is not None:
            self.my_judge_queue.append(judge)
            if judge.result == Species.WEREWOLF:
                self.found_wolf = True

    def talk(self) -> Content:
        # Do comingout if it's on scheduled day or a werewolf is found.
        if not self.has_co and (self.game_info.day == self.co_date or self.found_wolf):
            self.has_co = True
            return Content(ComingoutContentBuilder(self.me, Role.MEDIUM))
        # Report the medium result after doing comingout.
        if self.has_co and self.my_judge_queue:
            judge: Judge = self.my_judge_queue.popleft()
            return Content(IdentContentBuilder(judge.target, judge.result))
        # The list of agents that voted for me in the last turn.
        voted_for_me: List[Agent] = [j.agent for j in self.voted_reports if j.target == self.me]
        # The list of agents that said they would vote for me.
        vote_talk_for_me: List[Agent] = [j.agent for j in self.vote_talk if j.target == self.me]
        # The list of agents that requested to vote for me.
        request_vote_for_me: List[Agent] = [j.agent for j in self.request_vote_talk if j.target == self.me]
        # The list of fake seers that reported me as a werewolf.
        # Fake seers.
        fake_seers: List[Agent] = [j.agent for j in self.divination_reports
                                   if j.target == self.me and j.result == Species.WEREWOLF]
        # Vote for one of the alive fake mediums.
        candidates: List[Agent] = [a for a in self.comingout_map
                                   if self.is_alive(a) and self.comingout_map[a] == Role.MEDIUM]
    
        # Vote for one of the alive agents that voted for me in the last turn.
        if not candidates:
            candidates = self.get_alive(voted_for_me)
        # Vote for one of the alive agents that can vote for me this turn.
        if not candidates:
            candidates = self.get_alive_others(vote_talk_for_me)
        # Vote for one of the alive agents that requested to vote for me this turn.
        if not candidates:
            candidates = self.get_alive_others(request_vote_for_me)
        # Vote for one of the alive agents that were judged as werewolves by non-fake seers
        if not candidates:
            reported_wolves: List[Agent] = [j.target for j in self.divination_reports
                                            if j.agent not in fake_seers and j.result == Species.WEREWOLF]
            candidates = self.get_alive_others(reported_wolves)
        # Vote for one of the alive fake seers if there are no candidates.
        if not candidates:
            candidates = self.get_alive(fake_seers)
        # Vote for one of the alive agents if there are no candidates.
        if not candidates:
            candidates = self.get_alive_others(self.game_info.agent_list)
        # Declare which to vote for if not declare yet or the candidate is changed.
        if self.vote_candidate == AGENT_NONE or self.vote_candidate not in candidates:
            self.vote_candidate = self.random_select(candidates)
            if self.vote_candidate != AGENT_NONE:
                return Content(VoteContentBuilder(self.vote_candidate))
        return CONTENT_SKIP
