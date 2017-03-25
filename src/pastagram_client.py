import random

from twisted.internet import protocol
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver
from hockey.controller import Controller
from hockey.action import Action
from hockey.board_printer import BoardPrinter

from copy import deepcopy


class HockeyClient(LineReceiver, object):
    def __init__(self, name, debug):
        self.name = name
        self.debug = debug
        self.controller = Controller()

    def connectionMade(self):
        self.sendLine(self.name)


    def sendLine(self, line):
        super(HockeyClient, self).sendLine(line.encode('UTF-8'))


    def lineReceived(self, line):
        line = line.decode('UTF-8')
        playerNumber = 0
        if (line.startswith("Welcome,")):
            playerNumber = int(line[-2])
            if playerNumber == 0:
                self.controller.register(name)
                self.controller.register("other")
            else:
                self.controller.register("other")
                self.controller.register(name)
        if "did go" in line:
            boardPrinter = BoardPrinter()
            arrayMove = line[line.index('did go') + 7:].split(" ")
            oppenentMove = arrayMove[0]
            if arrayMove[1] != "-":
                oppenentMove += " " + arrayMove[1]
            print(oppenentMove)
            print(self.controller.ball)
            self.controller.move(oppenentMove)
            print("THE BALL")

            # boardPrinter.print_game(self.controller)
        if self.debug:
            print('Server said:', line)
        if '{} is active player'.format(self.name) in line or 'invalid move' in line:
            self.play_game()

    def play_game(self):
        ballX, ballY = self.controller.ball
        # print(self.controller.get_possible_actions(ballX, ballY))
        to_number = self.controller.get_possible_actions(ballX, ballY)[0]
        self.controller.move(to_number)
        print(to_number)
        self.sendLine(to_number)

    def alphabeta(self, controller, depth, alpha, beta, maximizing_player):
        ballX, ballY = controller.ball

        if depth == 0 or not controller.get_possible_actions(ballX, ballY):
            return random.randint(0, 100)

        if maximizing_player:
            value = float("-inf")
            for move in controller.get_possible_actions(ballX, ballY):
                # Copy board
                c = deepcopy(controller)
                # Apply move to copied board
                c.move(move)
                value = max(value, self.alphabeta(c, depth - 1, alpha, beta, False))
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return value
        else:
            value = float("+inf")
            for move in controller.get_possible_actions(ballX, ballY):
                # Apply move
                c = deepcopy(controller)
                # Apply move to copied board
                c.move(move)
                value = min(value, self.alphabeta(c, depth - 1, alpha, beta, True))
                beta = min(beta, value)
                # Apply move
                if beta <= alpha:
                    break
            return value


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