"""
    This module implements the Stockfish class.
    :copyright: (c) 2016-2021 by Ilya Zhelyabuzhsky.
    :license: MIT, see LICENSE for more details.
"""

# The above note refers to the LICENSE file of the project that models.py
# is originally from. The contents of that license file can be found in 
# LICENSE-models.

# This file was obtained from the python stockfish project on github. 
# I will be adding and/or modifying some code as needed for the application,
# and the changes I'll make can be found in the commit history.

import subprocess
from typing import Any, List, Optional
import copy

class Stockfish:
    """Integrates the Stockfish chess engine with Python."""

    def __init__(
        self, path: str = "stockfish", depth: int = 28, parameters: dict = None
    ) -> None:
        self.default_stockfish_params = {
            "Write Debug Log": "false",
            "Contempt": 0,
            "Min Split Depth": 0,
            "Threads": 1,
            "Ponder": "false",
            "Hash": 16,
            "MultiPV": 1,
            "Skill Level": 20,
            "Move Overhead": 30,
            "Minimum Thinking Time": 20,
            "Slow Mover": 80,
            "UCI_Chess960": "false",
            "UCI_LimitStrength": "false",
            "UCI_Elo": 1350, # As long as UCI_LimitStrength is false, this value shouldn't matter.
        }
        self.stockfish = subprocess.Popen(
            path, universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )

        self._stockfish_major_version: int = int(self._read_line().split(" ")[1])

        self._put("uci")

        self.depth = str(depth)
        self.info: str = ""

        if parameters is None:
            parameters = {}
        self._parameters = copy.deepcopy(self.default_stockfish_params)
        self._parameters.update(parameters)
        for name, value in list(self._parameters.items()):
            self._set_option(name, value)

        self._start_new_game()            

    def get_parameters(self) -> dict:
        """Returns current board position.
        Returns:
            Dictionary of current Stockfish engine's parameters.
        """
        return self._parameters

    def reset_parameters(self) -> None:
        """Resets the stockfish parameters.
        Returns:
            None
        """
        self._parameters = copy.deepcopy(self.default_stockfish_params)
        for name, value in list(self._parameters.items()):
            self._set_option(name, value)

    def _start_new_game(self) -> None:
        self._put("ucinewgame")
        self._is_ready()
        self.info = ""

    def _put(self, command: str) -> None:
        if not self.stockfish.stdin:
            raise BrokenPipeError()
        self.stockfish.stdin.write(f"{command}\n")
        self.stockfish.stdin.flush()

    def _read_line(self) -> str:
        if not self.stockfish.stdout:
            raise BrokenPipeError()
        return self.stockfish.stdout.readline().strip()

    def _set_option(self, name: str, value: Any) -> None:
        self._put(f"setoption name {name} value {value}")
        self._is_ready()

    def _is_ready(self) -> None:
        self._put("isready")
        while True:
            if self._read_line() == "readyok":
                return

    def _go(self) -> None:
        self._put(f"go depth {self.depth}")

    def _go_time(self, time: int) -> None:
        self._put(f"go movetime {time}")

    @staticmethod
    def _convert_move_list_to_str(moves: List[str]) -> str:
        result = ""
        for move in moves:
            result += f"{move} "
        return result.strip()

    def set_position(self, moves: List[str] = None) -> None:
        """Sets current board position.
        Args:
            moves:
              A list of moves to set this position on the board.
              Must be in full algebraic notation.
              example: ['e2e4', 'e7e5']
        """
        self._start_new_game()
        if moves is None:
            moves = []
        self._put(f"position startpos moves {self._convert_move_list_to_str(moves)}")

    def get_board_visual(self) -> str:
        """Returns a visual representation of the current board position.
        Returns:
            String of visual representation of the chessboard with its pieces in current position.
        """
        self._put("d")
        board_rep = ""
        count_lines = 0
        while count_lines < 17:
            board_str = self._read_line()
            if "+" in board_str or "|" in board_str:
                count_lines += 1
                board_rep += f"{board_str}\n"
        return board_rep

    def get_fen_position(self) -> str:
        """Returns current board position in Forsyth–Edwards notation (FEN).
        Returns:
            String with current position in Forsyth–Edwards notation (FEN)
        """
        self._put("d")
        while True:
            text = self._read_line()
            splitted_text = text.split(" ")
            if splitted_text[0] == "Fen:":
                return " ".join(splitted_text[1:])

    def set_skill_level(self, skill_level: int = 20) -> None:
        """Sets current skill level of stockfish engine.
        Args:
            skill_level:
              Skill Level option between 0 (weakest level) and 20 (full strength)
        Returns:
            None
        """
        self._set_option("UCI_LimitStrength", "false")
        self._set_option("Skill Level", skill_level)
        self._parameters.update({"Skill Level": skill_level})

    def set_elo_rating(self, elo_rating: int = 1350) -> None:
        """Sets current elo rating of stockfish engine, ignoring skill level.
        Args:
            elo_rating: Aim for an engine strength of the given Elo
        Returns:
            None
        """
        self._set_option("UCI_LimitStrength", "true")
        self._set_option("UCI_Elo", elo_rating)
        self._parameters.update({"UCI_Elo": elo_rating})

    def set_fen_position(self, fen_position: str) -> None:
        """Sets current board position in Forsyth–Edwards notation (FEN).
        Args:
            fen_position:
              FEN string of board position.
        Returns:
            None
        """
        self._start_new_game()
        self._put(f"position fen {fen_position}")
        
    def get_top_moves(self, num_top_moves: int) -> dict:
        """ Returns the top num_top_moves moves in the current position.
        Will return a dictionary of string-string pairs representing the best moves.
        The key is the PV number (as a string), and the value is the first move.        
        
        If there is an error, then an exception will be raised.
        If it's a mate now, then None is returned.        
        """
        
        if num_top_moves > self._parameters["MultiPV"] or num_top_moves <= 0:
            raise ValueError('bad value for num_top_moves')
        self._go()
        lines = []
        while True:
            text = self._read_line()
            splitted_text = text.split(" ")
            lines.append(splitted_text)
            if splitted_text[0] == "bestmove":
                break # since the line outputting the bestmove is the last line.
        first_moves_of_PVs = {
            # This is a ditionary. The key is the multiPV number of this line, and
            # the value will be another dictionary containing info for the PV 
            # (i.e., the first move of the PV, and other info about it).
        }
        multiplier = 1 if ("w" in self.get_fen_position()) else -1
        # Traversing in reverse order is important since the finalized info
        # is outputted at the end. To see this, in the terminal do "./stockfish", then
        # something like "setoption name multiPV value 3", and finally do 
        # "go depth 24".
        for current_line in reversed(lines):
            if current_line[0] == "bestmove":
                if current_line[1] == "(none)":
                    # Means the game is over.
                    return None
            elif (("multipv" in current_line) and ("depth" in current_line) and 
                  current_line[current_line.index("depth") + 1] == self.depth):
                multiPV_number = current_line[current_line.index("multipv") + 1]
                if int(multiPV_number) <= num_top_moves:
                    has_centipawn_value = ("cp" in current_line)
                    has_mate_value = ("mate" in current_line)
                    if has_centipawn_value == has_mate_value:
                        raise RuntimeError("Having a centipawn value and mate value should be mutually exclusive.")
                    first_moves_of_PVs[multiPV_number] = {
                        "Move": current_line[current_line.index("pv") + 1],
                        "Centipawn": int(current_line[current_line.index("cp") + 1]) * multiplier if has_centipawn_value else None,
                        "Mate": int(current_line[current_line.index("mate") + 1]) * multiplier if has_mate_value else None,
                        "Depth": int(current_line[current_line.index("depth") + 1]),
                        "Seldepth": int(current_line[current_line.index("seldepth") + 1])
                    }
            else:
                return first_moves_of_PVs
        raise RuntimeError("Reached the end of get_top_moves without returning anything.")

    def get_best_move(self) -> Optional[str]:
        """Returns best move with current position on the board.
        Returns:
            A string of move in algebraic notation or None, if it's a mate now.
        """
        self._go()
        last_text: str = ""
        while True:
            text = self._read_line()
            splitted_text = text.split(" ")
            if splitted_text[0] == "bestmove":
                if splitted_text[1] == "(none)":
                    return None
                self.info = last_text
                return splitted_text[1]
            last_text = text

    def get_best_move_time(self, time: int = 1000) -> Optional[str]:
        """Returns best move with current position on the board after a determined time
        Args:
            time:
              Time for stockfish to determine best move in milliseconds (int)
        Returns:
            A string of move in algebraic notation or None, if it's a mate now.
        """
        self._go_time(time)
        last_text: str = ""
        while True:
            text = self._read_line()
            splitted_text = text.split(" ")
            if splitted_text[0] == "bestmove":
                if splitted_text[1] == "(none)":
                    return None
                self.info = last_text
                return splitted_text[1]
            last_text = text

    def is_move_correct(self, move_value: str) -> bool:
        """Checks new move.
        Args:
            move_value:
              New move value in algebraic notation.
        Returns:
            True, if new move is correct, else False.
        """
        self._put(f"go depth 1 searchmoves {move_value}")
        while True:
            text = self._read_line()
            splitted_text = text.split(" ")
            if splitted_text[0] == "bestmove":
                if splitted_text[1] == "(none)":
                    return False
                else:
                    return True

    def get_evaluation(self) -> dict:
        """Evaluates current position
        Returns:
            A dictionary of the current advantage with "type" as "cp" (centipawns) or "mate" (checkmate in)
        """
        
        # CONTINUE HERE - Examine this function to see how it gets the evaluation. Figure out if
        # it's the method you're using to get the evaluation yourself, and if the methods differ
        # then figure out which is better to do.

        evaluation = dict()
        fen_position = self.get_fen_position() # this line and the ._put line below should be redundant.
        if "w" in fen_position:  # w can only be in FEN if it is whites move
            compare = 1
        else:  # stockfish shows advantage relative to current player, convention is to do white positive
            compare = -1
        self._put(f"position {fen_position}")
        self._go()
        while True:
            text = self._read_line()
            splitted_text = text.split(" ")
            if splitted_text[0] == "info":
                for n in range(len(splitted_text)):
                    if splitted_text[n] == "score":
                        evaluation = {
                            "type": splitted_text[n + 1],
                            "value": int(splitted_text[n + 2]) * compare,
                        }
            elif splitted_text[0] == "bestmove":
                return evaluation

    def set_depth(self, depth_value: int = 2) -> None:
        """Sets current depth of stockfish engine.
        Args:
            depth_value: Depth option higher than 1
        """
        self.depth = str(depth_value)

    def get_stockfish_major_version(self):
        """Returns Stockfish engine major version.
        Returns:
            Current stockfish major version
        """

        return self._stockfish_major_version

    def __del__(self) -> None:
        self._put("quit")
        self.stockfish.kill()