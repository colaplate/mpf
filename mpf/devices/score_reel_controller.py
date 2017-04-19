"""Score reel controller."""
from mpf.core.mpf_controller import MpfController


class ScoreReelController(MpfController):

    """The overall controller that is in charge of and manages the score reels in a pinball machine.

    The main thing this controller does is keep track of how many
    ScoreReelGroups there are in the machine and how many players there are,
    as well as maps the current player to the proper score reel.

    This controller is also responsible for working around broken
    ScoreReelGroups and "stacking" and switching out players when there are
    multiple players per ScoreReelGroup.

    Known limitations of this module:
        * Assumes all score reels include a zero value.
        * Assumes all score reels count up or down by one.
        * Assumes all score reels map their displayed value to their stored
          value in a 1:1 way. (i.e. value[0] displays 0, value[5] displays 5,
          etc.
        * Currently this module only supports "incrementing" reels (i.e.
          counting up). Decrementing support will be added in the future.
    """

    def __init__(self, machine):
        """Initialise score reel controller."""
        super().__init__(machine)

        self.active_scorereelgroup = None
        """Pointer to the active ScoreReelGroup for the current player.
        """
        self.player_to_scorereel_map = []
        """This is a list of ScoreReelGroup objects which corresponds to player
        indexes. The first element [0] in this list is the first player (which
        is player index [0], the next one is the next player, etc.
        """
        self.reset_queue = []
        """List of score reel groups that still need to be reset"""
        self.queue = None
        """Holds any active queue event queue objects"""

        # register for events

        # switch the active score reel group and reset it (if needed)
        self.machine.events.add_handler('player_turn_started',
                                        self.rotate_player)

        # receive notification of score changes
        self.machine.events.add_handler('player_score', self.score_change)

        # receives notifications of game starts to reset the reels
        self.machine.events.add_handler('game_starting', self.game_starting)

    def rotate_player(self, **kwargs):
        """Called when a new player's turn starts.

        The main purpose of this method is to map the current player to their
        ScoreReelGroup in the backbox. It will do this by comparing length of
        the list which holds those mappings (`player_to_scorereel_map`) to
        the length of the list of players. If the player list is longer that
        means we don't have a ScoreReelGroup for that player.

        In that case it will check the tags of the ScoreReelGroups to see if
        one of them is tagged with playerX which corresponds to this player.
        If not then it will pick the next free one. If there are none free,
        then it will "double up" that player on an existing one which means
        the same Score Reels will be used for both players, and they will
        reset themselves automatically between players.
        """
        del kwargs

        # if our player to reel map is less than the number of players, we need
        # to create a new mapping
        if (len(self.player_to_scorereel_map) <
                len(self.machine.game.player_list)):
            self.map_new_score_reel_group()

        self.active_scorereelgroup = self.player_to_scorereel_map[
            self.machine.game.player.index]

        self.debug_log("Mapping Player %s to ScoreReelGroup '%s'",
                       self.machine.game.player.number,
                       self.active_scorereelgroup.name)

        # Make sure this score reel group is showing the right score
        self.debug_log("Current player's score: %s",
                       self.machine.game.player.score)
        self.debug_log("Score displayed on reels: %s",
                       self.active_scorereelgroup.assumed_value_int)
        if (self.active_scorereelgroup.assumed_value_int !=
                self.machine.game.player.score):
            self.active_scorereelgroup.set_value(self.machine.game.player.score)

        # light up this group
        for group in self.machine.score_reel_groups:
            group.unlight()

        self.active_scorereelgroup.light()

    def map_new_score_reel_group(self):
        """Create a mapping of a player to a score reel group."""
        # do we have a reel group tagged for this player?
        for reel_group in self.machine.score_reel_groups.items_tagged(
                "player" + str(self.machine.game.player.number)):
            self.player_to_scorereel_map.append(reel_group)
            self.debug_log("Found a mapping to add: %s", reel_group.name)
            return

        # if we didn't find one, then we'll just use the first player's group
        # for all the additional ones.

        # todo maybe we should get fancy with looping through? Meh... we'll
        # cross that bridge when we get to it.

        self.player_to_scorereel_map.append(self.player_to_scorereel_map[0])

    def score_change(self, value, change, **kwargs):
        """Called whenever the score changes and adds the score increase to the current active ScoreReelGroup.

        This method is the handler for the score change event, so it's called
        automatically.

        Args:
            score: Integer value of the new score. This parameter is ignored,
                and included only because the score change event passes it.
            change: Interget value of the change to the score.
        """
        del kwargs
        if self.active_scorereelgroup and change:
            self.active_scorereelgroup.add_value(value=change, target=value)

    def game_starting(self, queue, game, **kwargs):
        """Reset the score reels when a new game starts.

        This is a queue event so it doesn't allow the game start to continue
        until it's done.

        Args:
            queue: A reference to the queue object for the game starting event.
            game: A reference to the main game object. This is ignored and only
                included because the game_starting event passes it.
        """
        del game
        del kwargs
        self.queue = queue
        # tell the game_starting event queue that we have stuff to do
        self.queue.wait()

        # populate the reset queue
        self.reset_queue = []

        for dummy_player, score_reel_group in self.machine.score_reel_groups.items():
            self.reset_queue.append(score_reel_group)
        self.reset_queue.sort(key=lambda x: x.name)
        # todo right now this sorts by ScoreGroupName. Need to change to tags
        self._reset_next_group()  # kick off the reset process

    def _reset_next_group(self, value=0, **kwargs):
        del kwargs
        # param `value` since that's what validate passes. Dunno if we need it.
        if self.reset_queue:  # there's still more to reset
            next_group = self.reset_queue.pop(0)
            self.debug_log("Resetting ScoreReelGroup %s", next_group.name)
            # add the handler to know when this group is reset
            self.machine.events.add_handler('scorereelgroup_' +
                                            next_group.name +
                                            '_valid', self._reset_next_group)
            next_group.set_value(value)

        else:  # no more to reset
            # clear the event queue
            self.queue.clear()
            self.queue = None
            # remove all these handlers watching for 0
            self.machine.events.remove_handler(self._reset_next_group)
