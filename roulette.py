import random
from exceptions import InvalidBet
import pprint
import abc

class Outcome:
    def __init__(self, name, odds):
        '''Represents an Outcome, for handling bets
        
        Parameters:
            name: str
            odds: number
        
        '''
        self.name = name
        self.odds = odds
    
    def __eq__(self, other):
        '''Return True if both Outcomes have the same name'''
        return self.name == other.name
    
    def __ne__(self, other):
        '''Return True if both Outcomes do not have the same name'''
        return ~(self.name == other.name)
    
    def __hash__(self):
        '''Returns hash value of name property (string)'''
        return hash(self.name)
    
    def __str__(self):
        return "{} (odds:{})".format(self.name, self.odds)
    
    def __repr__(self):
        return "Outcome({}, {})".format(self.name, self.odds)
    
class PrisonOutcome(Outcome):
    '''Special prison rule for Euro Roulette.
    
    When Outcome is a PrisonOutcome, the 0 bin becomes a special case where 
    half the money is returned to the player for losing bets.
    '''
    def __repr__(self):
        return "PrisonOutcome({}, {})".format(self.name, self.odds)
    
class Bin(frozenset): 
    '''Represents the 38 bins of the roulette wheel.
    
    Contains a collection of winning Outcomes for the corresponding bin.
    '''
    def get_outcome_iterator(self):
        return iter(self)

class Wheel:
    '''Manages and randomly selects a bin to simulate a roulette wheel.
    
    Properties:
        bins: Contains bin instances.
        rng: Random number generator used to select bins.
        all_outcomes: Set of all possible outcomes.
    '''
    
    def __init__(self, seed=None, rules="american"):
        self.bins = [Bin([]) for _ in range(38)]
    
        self.rng = random.Random()
        self.all_outcomes = set()
        if seed:
            self.rng.seed(seed)
            
        if rules == "american":
            bb = BinBuilder()
        elif rules == "european":
            bb = EuroBinBuilder()
        else:
            bb = None
                
        if bb:
            bb.build_bins(self)
        
    def add_outcome(self, bin, outcome):
        if outcome not in self.all_outcomes:
            self.all_outcomes.add(outcome)
        self.bins[bin] = Bin(self.bins[bin] | Bin([outcome]))
        
    def get_outcome(self, name):
        outcome = [oc for oc in self.all_outcomes if oc.name == name]
        if outcome:
            return outcome[0]
        
        return None
    
    def add_bin(self, idx, bin):
        self.bins[idx] = bin
    
    def next(self):
        return self.bins[self.rng.randint(0,37)]
    
    def get(self, idx):
        return self.bins[idx]
    
    def get_all_bins(self):
        return iter(self.bins)
    
    def get_all_outcomes(self):
        return self.all_outcomes
    
class BinBuilder:
    '''Adds winning Outcomes to each bin on the wheel'''
    def add_straight_bets(self, wheel):
        '''Adds straight bets to their bins with odds 35:1.
        
        Each bin (0-36) should have its own straight bet.
        00 should have a similar straight bet at index 37 of the wheel.
        '''
        ODDS = 35
        for n in range(37):
            wheel.add_outcome(n, Outcome("{}".format(n), ODDS))
        wheel.add_outcome(37, Outcome("00", ODDS))
    
    def add_split_bets(self, wheel):
        '''Adds split bets to their corresponding bins with odds 17:1.
        
        A pair consists of two adjacent bins, left/right or top/down.
        Left/right pairs can be found by iterating over the first 2 columns,
        and finding the corresponding bin to the right (n, n+1).
        Top/down pairs can be found by iterating over every element not in the
        last row and finding the corresponding bin below it (n, n+3).
        '''
        def add_left_right_pair(outcome, idx, wheel):
            wheel.add_outcome(idx, outcome)
            wheel.add_outcome(idx+1, outcome)
            
        def add_top_down_pair(outcome, idx, wheel):
            wheel.add_outcome(idx, outcome)
            wheel.add_outcome(idx+3, outcome)
        
        ODDS = 17
        for r in range(12):
            for i in range(1,3):
                n = 3*r + i
                pair_outcome = Outcome("{}-{}".format(n, n+1), ODDS)
                add_left_right_pair(pair_outcome, n, wheel)
                
        for n in range(1,34):
            pair_outcome = Outcome("{}-{}".format(n, n+3), ODDS)
            add_top_down_pair(pair_outcome, n, wheel)
    
    def add_street_bets(self, wheel):
        '''Add street bets to their corresponding bins with odds 11:1.
        
        A street bet consists of a row of 3 bins.
        Street bets can be found by iterating over each element in the first
        column and finding its neighbors, (n, n+1, n+2).
        '''
        ODDS = 11
        for r in range(12):
            n = 3*r+1
            street_outcome = Outcome("{}-{}-{}".format(n,n+1,n+2), ODDS)
            for i in range(3):
                wheel.add_outcome(n+i, street_outcome)
    
    def add_corner_bets(self, wheel):
        '''Add corner bets to their corresponding bins with odds 8:1.
        
        Corners consist of bins sharing a corner on the board. Between 1-4
        bins can share a corner, but it can be observed that for any corner with
        under 4 bins, a better bet can be made with 4 bins including the original
        bins, so corner bets will only be added for 4 bin sets.
        
        Corners can be found by iterating over the first 2 columns up to the 
        last row and indexing (n, n+1, n+3, n+4). This creates a corner block
        from a bin, its neighbor to the right, its neighbor below it, and its
        neighbor to its bottom right.
        '''
        def add_corner_block(idx, wheel):
            ODDS = 8
            outcome = Outcome("{}-{}-{}-{}".format(*(idx + i for i in [0,1,3,4])), ODDS)
            for i in [0,1,3,4]:
                wheel.add_outcome(idx+i, outcome)
        
        for r in range(11):
            left_n = 3*r + 1
            add_corner_block(left_n, wheel)
            
            right_n = 3*r + 2
            add_corner_block(right_n, wheel)

    def add_line_bets(self, wheel):
        '''Add line bets to their corresponding bins with odds 5:1.
        
        Line blocks consist of 6 bins each. Each line is the line between
        rows on the roulette board. As there are 12 rows, there are 11 lines,
        and relevant bins can be found iterating over consecutive 6 bin blocks
        from the first up to the last row.
        '''
        ODDS = 5
        for r in range(11):
            n = 3*r + 1
            idxs = [n + i for i in range(6)]
            line_outcome = Outcome("{}-{}-{}-{}-{}-{}".format(*idxs), ODDS)
            for idx in idxs:
                wheel.add_outcome(idx, line_outcome)
            
    
    def add_dozen_bets(self, wheel):
        '''Add dozen bets to their corresponding bins with odds 2:1.
        
        Dozen blocks consist of 12 bin intervals: 1-12, 13-24, 25-36.
        '''
        ODDS = 2
        for d in range(3):
            dozen_outcome = Outcome("dozen({})".format(d+1), ODDS)
            for m in range(12):
                idx = 12*d + m + 1
                wheel.add_outcome(idx, dozen_outcome)
    
    def add_column_bets(self, wheel):
        '''Add column bets to their corresponding bins with odds 2:1.
        
        Column blocks consist of the 12 bins in a single column.
        '''
        ODDS = 2
        for c in range(3):
            col_outcome = Outcome("column({})".format(c+1), ODDS)
            for r in range(12):
                idx = 3*r + c + 1
                wheel.add_outcome(idx, col_outcome)
    
    def add_even_money_bets(self, wheel):
        '''Add even money bets to their corresponding bins with odds 1:1.
        
        Even money bets consist of 6 types:
            1. Red
                Red bins on the boards.
            2. Black
                Black bins on the board.
            3. Even
                Even bins on the board.
            4. Odd
                Odd bins on the board.
            5. High
                Bins < 19.
            6. Low
                Bins >= 19.
        '''
        ODDS = 1
        red = Outcome("red", ODDS)
        black = Outcome("black", ODDS)
        even = Outcome("even", ODDS)
        odd = Outcome("odd", ODDS)
        high = Outcome("high", ODDS)
        low = Outcome("low", ODDS)
        
        red_bins = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        
        for n in range(1, 37):
            if n >= 1 and n < 19:
                wheel.add_outcome(n, low)
            else:
                wheel.add_outcome(n, high)
                
            if n % 2 == 0:
                wheel.add_outcome(n, even)
            else:
                wheel.add_outcome(n, odd)
                
            if n in red_bins:
                wheel.add_outcome(n, red)
            else:
                wheel.add_outcome(n, black)
                
    def add_five_bets(self, wheel):
        '''Add five-bet (00-0-1-2-3) to bins 0,1,2,3, and 00 with odds 6:1.'''
        five_bet = Outcome("00-0-1-2-3", 6)
        for i in range(4):
            wheel.add_outcome(i, five_bet)
        wheel.add_outcome(37, five_bet)
        
    def build_bins(self, wheel):
        self.add_straight_bets(wheel)
        self.add_split_bets(wheel)
        self.add_street_bets(wheel)
        self.add_corner_bets(wheel)
        self.add_line_bets(wheel)
        self.add_dozen_bets(wheel)
        self.add_column_bets(wheel)
        self.add_even_money_bets(wheel)
        self.add_five_bets(wheel)
        
class EuroBinBuilder(BinBuilder):
    '''Modifies the rules for European Roulette.
    
    European roulette has a few differences from American roulette:
        1. The 0 bin should return a PrisonOutcome instead of an Outcome.
        2. There are no 5-bets (00-0-1-2-3), instead these are replaced with 4 bets (0-1-2-3).
    '''
    def add_straight_bets(self, wheel):
        '''Adds straight bets to their bins with odds 35:1.
        
        Each bin (0-36) should have its own straight bet.
        00 should have a similar straight bet at index 37 of the wheel.
        '''
        ODDS = 35
        for n in range(1,37):
            wheel.add_outcome(n, Outcome("{}".format(n), ODDS))
        wheel.add_outcome(37, Outcome("00", ODDS))
        wheel.add_outcome(0, PrisonOutcome("0", ODDS))
        
    def add_five_bets(self, wheel):
        '''This bet doesn't exist in European Roulette, so do nothing'''
        pass
    
    def add_four_bets(self, wheel):
        '''Add four-bet to bin 0 with odds 6:1'''
        four_bet = Outcome("0-1-2-3", 6)
        for i in range(4):
            wheel.add_outcome(i, four_bet)
        
    def build_bins(self, wheel):
        '''Build bins as before, but add additional four bets'''
        super().build_bins(wheel)
        self.add_four_bets(wheel)
    
    
class Bet:
    '''Manages the amount of money wagered on Outcomes.
    
    Properties:
        amount: The amount bet
        outcome: The outcome that was bet on
    '''
    def __init__(self, amount, outcome):
        self.amount = amount
        self.outcome = outcome
        
    def win_amount(self):
        '''Calculates the total win amount.
        
        Returns:
            number : amount * odds
        '''
        return self.amount*self.outcome.odds
    
    def lose_amount(self):
        '''Lose amount is same as win amount, but used differently.
        
        Returns:
            number : amount * odds
        '''
        return self.win_amount()
    
    def __str__(self):
        '''Returns string represenation of the bet with form "amount on outcome'''
        return "{} on {}".format(self.amount, self.outcome)
    
    def __repr__(self):
        '''Returns string representation with the form Bet(amount, outcome)'''
        return "Bet({}, {})".format(self.amount, self.outcome)
        
class Table:
    ''' Manages all the bets currently active.
    
    Properties:
        limit: The table limit. Sum of all bets must not exceed this.
        minimum: The minimum bet allowed.
        bets: List of active bets.
    '''
    def __init__(self, limit, wheel):
        self.limit = limit
        self.bets = []
        self.wheel = wheel
        
    def place_bet(self, bet):
        self.bets.append(bet)
        if not self.is_valid():
            raise InvalidBet
    
    def __iter__(self):
        return iter(self.bets)
    
    def __str__(self):
        return pprint.saferepr(self.bets)
    
    def __repr__(self):
        return "Table({})".format("".join((str(x) for x in self.bets)))
    
    def is_valid(self):
        if sum(x.amount for x in self.bets) > self.limit:
            return False
        return True
    
    def clear_bets(self):
        self.bets = []
    
class Game:
    '''Manages game state.
    
    Properties:
        wheel: Wheel instance that selects random bins.
        table: Table instance which holds ongoing bets.
    '''
    def __init__(self, table):
        self.table = table
        
    def cycle(self, player):
        '''Executes a single cycle of play with a given Player:
            1. Calls on Player to place bets.
            2. Retrieves winning Bin from Wheel
            3. Iterates over Table's Bets and call corresponding win/lose function
            
        Returns:
            1. Sum of win/loss amount for testing purposes.
            2. Number of bets for testing purposes.
        '''
        if player.playing():
            player.place_bets()
        winning_outcomes = self.table.wheel.next()
        player.winners(winning_outcomes)
        outcomes = []
        for b in self.table.bets:
            if b.outcome in winning_outcomes:
                outcomes.append(player.win(b))
            else:
                outcomes.append(player.lose(b))         
        
        self.table.clear_bets()
        return sum(outcomes), len(outcomes)
    
class Player(abc.ABC):
    '''Abstract Player class.
    
    Properties:
        table: Table used to place bets.
        stake: Current stake.
        rounds: Number of rounds left to play.
    '''
    def __init__(self, table):
        self.table = table
        self.stake = None
        self.rounds = None
    
    def playing(self):
        if self.rounds is None or self.stake is None:
            return False
        if self.rounds > 0 and self.stake > 0:
            return True   
        return False
    
    @abc.abstractmethod
    def place_bets(self):
        raise NotImplementedError
    
    def win(self, bet):
        return bet.win_amount()
        
    def lose(self, bet):
        if isinstance(bet.outcome, PrisonOutcome):
            return bet.lose_amount * 0.5
        return 0
        
    def set_stake(self, stake):
        self.stake = stake
        
    def set_rounds(self, rounds):
        self.rounds = rounds
        
    def winners(self, winners):        
        '''Called every round to report winners
        
        Marks round end, so decrement remaining round counter.
        Some Players do not have rounds (like passenger57), so only update rounds
        if applicable.
        '''
        if self.rounds:
            self.rounds -= 1
        
class Passenger57(Player):
    '''A test Player to check Game functionality.
    
    Passenger57 always bets on black.
    Win/Lose returns True/False for testing in unittest.
    '''
    def __init__(self, table):
        super().__init__(table)
        self.black = self.table.wheel.get_outcome("black")
        
    def place_bets(self):
        self.table.place_bet(Bet(10, self.black))
    
    def playing(self):
        return True
    
class Martingale(Player):
    '''Player that bets in Roulette.
    
    Strategy: Doubles bet on black every loss and resets bet to a base amount 
        on each win.
    '''
    def __init__(self, table):
        super().__init__(table)
        self.multiplier = 0
        self.black = table.wheel.get_outcome("black")
        
    def place_bets(self):
        amount = 2**self.multiplier
        if amount > self.table.limit:
            amount = self.table.limit
            
        if amount > self.stake:
            amount = self.stake
        
        self.stake -= amount
        self.table.place_bet(Bet(amount, self.black))
    
    def win(self, bet):
        self.multiplier = 0
        self.stake += bet.amount
        return super().win(bet)
    
    def lose(self, bet):
        self.multiplier += 1
        return super().lose(bet)
    
#    def winners(self, winners):
#        super().__winners__(winners)
    
class SevenReds(Martingale):
    '''Player that bets in Roulette.
    
    Strategy: Wait for 7 consecutive reds, then bets on black.
    
    Functions:
        place_bets: bets with the same strategy as martingale after 7 consecutive
            reds.
    '''
    def __init__(self, table):
        super().__init__(table)
        self.red_count = 0
        self.red = self.table.wheel.get_outcome("red")
        self.black = self.table.wheel.get_outcome("black")
    
    def place_bets(self):
        multiplier = self.red_count - 7
        if multiplier >= 0:
            super().place_bets()
    
    def winners(self, winners):     
        super().winners(winners)
        if self.red in winners:
            self.red_count += 1
        else:
            self.red_count = 0
            
                        
class PlayerRandom(Player):
    '''Player that bets randomly.
    
    Strategy: Bets on random Outcome.
    
    Functions:
        place_bets: get all possible Outcomes and bet on 1 randomly.
    '''
    def __init__(self, table, seed=None):
        super().__init__(table)
        if seed:
            self.rng = random.Random(seed)
        else:
            self.rng = random.Random()
            
    def place_bets(self):
        all_outcomes = self.table.wheel.get_all_outcomes()
        outcome = self.rng.sample(all_outcomes, 1)[0]
        bet = Bet(self.stake, outcome)
        
        self.table.place_bet(bet)
        return bet
        
    
class Simulator:
    '''Simulator for gathering performance statistics on Player's strategy.
    
    Parameters:
        init_duration: max number of rounds to have Player play.
        init_stake: starting stakes for Player.
        samples: number of games to simulate.
        durations: list of how long Player was able to play in each simulation.
        maxima: list of Player's max stake in each simulation
        player: Player strategy to use.
        game: Game to simulate.
    
    Methods:
        session: initializes Player with initial settings and executes game
            cycles until Player stops playing. Saves duration played as well as
            max stake. Returns stake history for testing.
        gather: executes session the number of times specified in samples.
    '''
    def __init__(self, game, player):
        self.init_duration = 250
        self.init_stake = 100
        self.samples = 50
        self.durations = IntegerStatistics()
        self.maxima = IntegerStatistics()
        self.player = player
        self.game = game
    
    def session(self):
        self.player.__init__(self.player.table)
        self.player.set_rounds(self.init_duration)
        self.player.set_stake(self.init_stake)
        
        stakes = [self.player.stake]
        duration = 0
        while self.player.playing():
            self.game.cycle(self.player)
            stakes.append(self.player.stake)
            duration += 1
        self.durations.append(duration)
        self.maxima.append(max(stakes))
        
        return stakes
    
    def gather(self, debug=False):
        for _ in range(self.samples):    
            if debug:
                print(self.session())
            else:
                self.session()
                
class IntegerStatistics(list):
    '''Extension of List class to calculate statistical summaries.

    functions:
        mean: sum of values / number of values
        stddev: sqrt(sum((values - mean)^2)/(number of values -1))
    '''
    def mean(self):
        return sum(self)/len(self)

    def stdev(self):
        return (sum((x - self.mean())**2 for x in self)/(len(self) -1 ))**.5
            
class SimulationBuilder():
    '''Wrapper to build simulators
    
    Simulators consist of:
        1. Wheel
        2. Table
        3. Player
        4. Game    
    
    SimulationBuilder builds everything up the Player, which may change.
    
    Functions:
        get_simulator: takes a Player mode as input and returns the simulator
            with the desired betting strategy.
    '''
    def __init__(self, table_limit, seed=None):
        self.seed = seed
        if self.seed:
            wheel = Wheel(seed)
        else:
            wheel = Wheel()
            
        table = Table(table_limit, wheel)
        
        self.game = Game(table)
        self.pb = PlayerBuilder(table)
        
    def get_simulator(self, mode):
        simulator = Simulator(self.game, self.pb.get_player(mode, self.seed))
        return simulator
    
class PlayerBuilder():
    '''Wrapper to build Players from Table'''
    def __init__(self, table):
        self.table = table
    def get_player(self, mode, seed):
        if mode == "martingale":
            return Martingale(self.table)
        elif mode == "sevenreds":
            return SevenReds(self.table)
        elif mode == "passenger57":
            return Passenger57(self.table)
        elif mode == "random":
            return PlayerRandom(self.table, seed)
        else:
            raise ValueError

    
            
if __name__ == "__main__":
    sb = SimulationBuilder(table_limit=1000)
    simulator = sb.get_simulator("sevenreds")
    simulator.gather(debug=False)
    print(simulator.durations)
    print(simulator.maxima)