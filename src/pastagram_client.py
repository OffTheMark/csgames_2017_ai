import random

from twisted.internet import protocol
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver
from hockey2.our_controller_polarity import ControllerPolarity
from hockey.action import Action

from copy import copy, deepcopy
import time


class HockeyClient(LineReceiver, object):
    def __init__(self, name, debug):
        self.name = name
        self.debug = debug
        self.controller = ControllerPolarity(15, 15)
        self.indexPlayer = 0
        self.enemyPlayerIndex = 0
        self.time_threshold = 1.75
        self.initial_time = 0.0
        self.elapsed = 0.0
        self.last_depth = 0

    def connectionMade(self):
        self.sendLine(self.name)

    def sendLine(self, line):
        super(HockeyClient, self).sendLine(line.encode('UTF-8'))

    def lineReceived(self, line):
        line = line.decode('UTF-8')
        if line.startswith("Welcome,"):
            self.indexPlayer = int(line[-2])
            if self.indexPlayer == 0:
                self.enemyPlayerIndex = 1
                self.controller.register(name)
                self.controller.register("other")
            else:
                self.enemyPlayerIndex = 0
                goal = "north"
                self.controller.register("other")
                self.controller.register(name)
        if "power up is at" in line:
            power_up_string = line[line.index('(') + 1:].split(" - ")[0][:-1]
            power_up_array = [int(x) for x in power_up_string.split(", ")]
            self.controller.power_up_position = (power_up_array[0], power_up_array[1])
        if "did go" in line and self.name not in line:
            array_action = line[line.index('did go') + 7:].split(" ")
            opponent_action = array_action[0]
            if array_action[1] != "-":
                opponent_action += " " + array_action[1]
            self.controller.move(opponent_action)
            print("Opponent moved {}".format(opponent_action))
            print("The ball is at {}".format(self.controller.ball))
        if "polarity of the goal" in line:
            self.controller.inverse_polarity()
            print("Our goal is at {}".format(self.controller.goal_by_player[self.indexPlayer]))

        if self.debug:
            print('Server said:', line)
        if '{} is active player'.format(self.name) in line or 'invalid move' in line:
            self.play_game()

    def play_game(self):
        ballX, ballY = self.controller.ball
        self.initial_time = time.time()
        possible_actions = self.controller.get_possible_actions(ballX, ballY)

        if len(possible_actions) > 0:
            very_best_action = None
            very_best_value = float("-inf")
            # Optimistic, I admit
            for depth in range(2, 2000):
                if self.elapsed >= self.time_threshold:
                    break
                self.last_depth = depth
                best_value = float("-inf")
                best_action = None

                for action in possible_actions:
                    self.elapsed = time.time() - self.initial_time
                    if self.elapsed >= self.time_threshold:
                        break
                    # Copy board
                    c = deepcopy(self.controller)
                    # Apply move to copied board
                    c.move(action)
                    new_ball_x, new_ball_y = c.ball
                    # If there is a bounce, we play again
                    maximizing_param = False if not c.dots[new_ball_x][new_ball_y]['bounce'] else True
                    value = self.alphabeta(c, depth, float("-inf"), float("+inf"), maximizing_param)
                    if value > best_value:
                        best_value = value
                        best_action = action
                if best_value > very_best_value:
                    very_best_value = best_value
                    very_best_action = best_action

            action = very_best_action if very_best_action else possible_actions[
                random.randint(0, len(possible_actions) - 1)]
        else:
            # In case things go south, do whatever
            action = Action.from_number(random.randint(0, 7))

        self.controller.move(action)
        self.sendLine(action)
        print("Last depth : {}".format(self.last_depth + 1))

    def alphabeta(self, cont, depth, alpha, beta, maximizing_player):
        ballX, ballY = cont.ball
        self.elapsed = time.time() - self.initial_time

        if depth == 0 or not cont.get_possible_actions(ballX, ballY) or self.elapsed >= self.time_threshold:
            return self.calculateBoard(cont)

        if maximizing_player:
            value = float("-inf")
            possible_actions = cont.get_possible_actions(ballX, ballY)
            for action in possible_actions:
                # Copy board
                c = deepcopy(cont)
                # Apply move to copied board
                c.move(action)
                new_ball_x, new_ball_y = c.ball
                # If there's a bounce, the same player plays
                maximizing_param = False if not c.dots[new_ball_x][new_ball_y]['bounce'] else maximizing_player
                value = max(value, self.alphabeta(c, depth - 1, alpha, beta, maximizing_param))
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return value
        else:
            value = float("+inf")
            possible_actions = cont.get_possible_actions(ballX, ballY)
            for action in possible_actions:
                # Apply move
                c = deepcopy(cont)
                # Apply move to copied board
                c.move(action)
                new_ball_x, new_ball_y = c.ball
                # If there's a bounce, the same player plays
                maximizing_param = True if not c.dots[new_ball_x][new_ball_y]['bounce'] else maximizing_player
                value = min(value, self.alphabeta(c, depth - 1, alpha, beta, maximizing_param))
                beta = min(beta, value)
                # Apply move
                if beta <= alpha:
                    break
            return value

    def calculateBoard(self, controller):
        x, y = controller.ball
        winScore = float("inf")
        ourTurn = 0
        if controller.active_player_name() == name:
            ourTurn = 1
        else:
            ourTurn = -1
        if len(controller.get_possible_actions(x, y)) == 0:
            return winScore * -ourTurn

        if y == controller.goal_by_player[self.indexPlayer]:
            return winScore
        if y == controller.goal_by_player[self.enemyPlayerIndex]:
            return winScore * -1
        return controller.size_y - abs(controller.goal_by_player[self.indexPlayer] - y)


class ClientFactory(protocol.ClientFactory):
    def __init__(self, name, debug):
        self.name = name
        self.debug = debug

    def buildProtocol(self, addr):
        return HockeyClient(self.name, self.debug)

    def clientConnectionFailed(self, connector, reason):
        if self.debug:
            print("Connection failed - goodbye!")
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        if self.debug:
            print("Connection lost - goodbye!")
        reactor.stop()


name = "Pastagram"

f = ClientFactory(name, debug=True)
reactor.connectTCP("localhost", 8023, f)
reactor.run()
