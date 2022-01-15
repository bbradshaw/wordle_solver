from collections import defaultdict, Counter
from ctypes.wintypes import WORD
from enum import IntEnum
from random import choice
from rich import console, text
import sys

console = console.Console()
GUESSES = 20

with open("/Users/ben/Documents/personal/scrabble_dictionary.txt") as sd:
    WORDS = tuple(w.strip() for w in sd)

class LetterResult(IntEnum):
    NOT_USED = 1
    IS_USED = 2
    CORRECT = 3


class Guesser:
    def __init__(self, word_length):
        self.words = {w: Counter(w) for w in WORDS if len(w) == word_length}
        self.solved = [None]*word_length
        self.wrong = [set() for _ in range(word_length)]
        self.max_letter = dict()
        self.min_letter = defaultdict(int)
        self.word_length = word_length
    
    def _position_contraints(self, word):
        for i in range(self.word_length):
            if self.solved[i] is not None and self.solved[i] != word[i]:
                return False
            if word[i] in self.wrong[i]:
                return False
        return True 

    def _letter_constraints(self, counted):
        for (letter, count) in counted.items():
            if letter in self.max_letter and count > self.max_letter[letter]:
                return False
        for (letter, count) in self.min_letter.items():
            if counted[letter] < count:
                return False
        return True

    def _updated_words(self):
        new_words = dict()
        for word, counted in self.words.items():
            if self._position_contraints(word) and self._letter_constraints(counted):
                new_words[word] = counted
        return new_words

    def update_guesses(self, guess, oracle):
        res = oracle(guess)
        for letter in set(guess):
            spots = [res[i] for i in range(self.word_length) if guess[i] == letter]
            min_usages = sum(1 for s in spots if s in (LetterResult.IS_USED, LetterResult.CORRECT))
            is_maxed = any(s for s in spots if s == LetterResult.NOT_USED)
            self.min_letter[letter] = min_usages
            if is_maxed:
                self.max_letter[letter] = min_usages
        for p in range(self.word_length):
            if res[p] == LetterResult.CORRECT:
                self.solved[p] = guess[p]
            elif res[p] == LetterResult.IS_USED:
                self.wrong[p].add(guess[p])
        self.words = self._updated_words()

    def guess_next_word(self):
        try:
            return choice(tuple(self.words))
        except IndexError:
            raise KeyError("Ran out of words to guess! :(")

    def answer(self):
        if all(self.solved[i] is not None for i in range(self.word_length)):
            return "".join(self.solved)
        return None

def make_oracle_for_word(word):
    def oracle(guess):
        remaining = Counter(word)
        res = []
        for p in range(len(word)):
            if word[p] == guess[p]:
                res.append(LetterResult.CORRECT)
                remaining[guess[p]] -= 1
            else:
                res.append(0)
        for p in range(len(word)):
            if res[p] != 0:
                continue
            if remaining[guess[p]] > 0:
                res[p] = LetterResult.IS_USED
                remaining[guess[p]] -= 1
            else:
                res[p] = LetterResult.NOT_USED
        return res
    return oracle


def make_human_oracle_for_guess(word_length, guess):
    from rich.prompt import PromptBase
    class InputPrompt(PromptBase):
        def check_choice(self, choice):
            return len(choice) == word_length and all(c in ('1','2','3') for c in choice)
    result = InputPrompt.ask(
        f"I guess [bold]{guess}[/]. Enter result: ", console=console, choices=["1", "2", "3"])
    result = [int(r) for r in result]
    def oracle(_guess):
        return result
    return oracle


def guess_display(word_length, oracle, guess):
    display = []
    res = oracle(guess)
    for p in range(word_length):
        if res[p] == LetterResult.NOT_USED:
            color = "frame bright_black"
        elif res[p] == LetterResult.IS_USED:
            color = "frame yellow"
        else:
            color = "frame green3"
        display.append(("{} ".format(guess[p]), color))
    return text.Text.assemble(*display)


def automain(word):
    oracle = make_oracle_for_word(word)
    word_length = len(word)
    guesser = Guesser(word_length)
    for gn in range(GUESSES):
        guess = guesser.guess_next_word()
        console.print(guess_display(word_length, oracle, guess))
        guesser.update_guesses(guess, oracle)
        answer = guesser.answer()
        if answer:
            console.print(f"the answer is: {answer}")
            break


def humanmain(word_length):
    console.print(
        ("[frame bright_black]1[/] for not used, "
         "[frame yellow]2[/] for used in wrong place, "
         "and [frame green3]3[/] for correct guess."))
    guesser = Guesser(word_length)
    from rich.prompt import Confirm, PromptBase
    human_guess = None
    if Confirm.ask("Take first guess?"):
        class FirstGuessPrompt(PromptBase):
            def check_choice(self, value: str) -> bool:
                len(value) == word_length
        human_guess = FirstGuessPrompt.ask("Your guess?")
    for gn in range(GUESSES):
        if human_guess:
            guess = human_guess
            human_guess = None
        else:
            guess = guesser.guess_next_word()
        console.print(f"guess is '{guess}'")
        oracle = make_human_oracle_for_guess(word_length, guess)
        guesser.update_guesses(guess, oracle)
        console.print(guess_display(word_length, oracle, guess))
        answer = guesser.answer()
        if answer:
            console.print(f"the answer is: {answer}")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            word_length = int(sys.argv[1])
            humanmain(word_length)
        except ValueError:
            automain(sys.argv[1])
    else:
        humanmain(6)