import random
from typing import Dict, List

from aiwolf import (AbstractPlayer, Agent, Content, GameInfo, GameSetting,
                    Judge, Role, Species, Status, Talk, Topic, Vote, Operator, VoteContentBuilder)
from aiwolf.constant import AGENT_NONE

from const import CONTENT_SKIP
    
class HyunjiVillager(AbstractPlayer):
    me: Agent # Myself.
    vote_candidate: Agent # Candidate for voting.
    game_info: GameInfo # Information about current game.
    game_setting: GameSetting # Settings of current game.
    comingout_map: Dict[Agent, Role] # Mapping between an agent and the role it claims that it is.
    divination_reports: List[Judge] # Time series of divination reports.
    identification_reports: List[Judge] # Time series of identification reports.
    vote_talk: List[Vote] # Talk containing VOTE.
    voted_reports: List[Vote] # Time series of voting reports.
    request_vote_talk: List[Vote] # Talk containing REQUEST VOTE.
    talk_list_head: int # Index of the talk to be analysed next.

    def __init__(self) -> None:
        self.me = AGENT_NONE
        self.vote_candidate = AGENT_NONE
        self.game_info = None  # type: ignore
        self.comingout_map = {}
        self.divination_reports = []
        self.identification_reports = []
        self.vote_talk = []
        self.voted_reports = []
        self.request_vote_talk = []
        self.talk_list_head = 0

    def is_alive(self, agent: Agent) -> bool:
        """Bool value of whether the agent is alive."""
        return self.game_info.status_map[agent] == Status.ALIVE

    def get_others(self, agent_list: List[Agent]) -> List[Agent]:
        """Return a list of agents excluding myself from the given list of agents."""
        return [a for a in agent_list if a != self.me]

    def get_alive(self, agent_list: List[Agent]) -> List[Agent]:
        """Return a list of alive agents contained in the given list of agents."""
        return [a for a in agent_list if self.is_alive(a)]

    def get_alive_others(self, agent_list: List[Agent]) -> List[Agent]:
        """Return a list of alive agents that is contained in the given list of agents
        and is not equal to myself."""
        return self.get_alive(self.get_others(agent_list))

    def random_select(self, agent_list: List[Agent]) -> Agent:
        """Return one agent randomly chosen from the given list of agents."""
        return random.choice(agent_list) if agent_list else AGENT_NONE

    def initialize(self, game_info: GameInfo, game_setting: GameSetting) -> None:
        self.game_info = game_info
        self.game_setting = game_setting
        self.me = game_info.me
        self.comingout_map.clear()
        self.divination_reports.clear()
        self.identification_reports.clear()
        self.vote_talk.clear()
        self.voted_reports.clear()
        self.request_vote_talk.clear()

    def day_start(self) -> None:
        self.talk_list_head = 0
        self.vote_candidate = AGENT_NONE

    def update(self, game_info: GameInfo) -> None:
        self.game_info = game_info  # Update game information.
        for i in range(self.talk_list_head, len(game_info.talk_list)):  # Analyze talks that have not been analyzed yet.
            tk: Talk = game_info.talk_list[i]  # The talk to be analyzed.
            talker: Agent = tk.agent
            if talker == self.me:  # Skip my talk.
                continue
            content: Content = Content.compile(tk.text)
            if content.topic == Topic.COMINGOUT:
                self.comingout_map[talker] = content.role
            elif content.topic == Topic.DIVINED:
                self.divination_reports.append(Judge(talker, game_info.day, content.target, content.result))
            elif content.topic == Topic.IDENTIFIED:
                self.identification_reports.append(Judge(talker, game_info.day, content.target, content.result))
            elif content.topic == Topic.VOTE:
                self.vote_talk.append(Vote(talker, game_info.day, content.target))
            elif content.topic == Topic.VOTED: 
                self.voted_reports.append(Vote(talker, game_info.day, content.target))
            elif content.topic == Topic.OPERATOR and content.operator == Operator.REQUEST:
                for contents in content.content_list:
                    if contents.topic == Topic.VOTE:
                        self.request_vote_talk.append(Vote(talker, game_info.day, contents.target))
        self.talk_list_head = len(game_info.talk_list)  # All done.

    def talk(self) -> Content:
        # Choose an agent to be voted for while talking.
        
        # The list of agents that voted for me in the last turn.
        voted_for_me: List[Agent] = [j.agent for j in self.voted_reports if j.target == self.me]
        # The list of agents that said they would vote for me.
        vote_talk_for_me: List[Agent] = [j.agent for j in self.vote_talk if j.target == self.me]
        # The list of agents that requested to vote for me.
        request_vote_for_me: List[Agent] = [j.agent for j in self.request_vote_talk if j.target == self.me]
        # The list of fake seers that reported me as a werewolf.
        fake_seers: List[Agent] = [j.agent for j in self.divination_reports
                                if j.target == self.me and j.result == Species.WEREWOLF]
        reported_wolves: List[Agent] = [j.target for j in self.divination_reports
                                        if j.agent not in fake_seers and j.result == Species.WEREWOLF]
        
        # Vote for one of the alive agents that were judged as werewolves by non-fake seers.
        candidates: List[Agent] = self.get_alive_others(reported_wolves)
        # Vote for one of the alive agents that can vote for me this turn.
        if not candidates:
            candidates = self.get_alive_others(vote_talk_for_me)
        # Vote for one of the alive agents that requested to vote for me this turn.
        if not candidates:
            candidates = self.get_alive_others(request_vote_for_me)
        # Vote for one of the alive agents that voted for me in the last turn.
        if not candidates:
            candidates = self.get_alive(voted_for_me)
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

    def vote(self) -> Agent:
        return self.vote_candidate if self.vote_candidate != AGENT_NONE else self.me

    def attack(self) -> Agent:
        raise NotImplementedError()

    def divine(self) -> Agent:
        raise NotImplementedError()

    def guard(self) -> Agent:
        raise NotImplementedError()

    def whisper(self) -> Content:
        raise NotImplementedError()

    def finish(self) -> None:
        pass