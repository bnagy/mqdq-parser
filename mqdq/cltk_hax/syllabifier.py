"""Latin language syllabifier.
Parses a latin word or a space separated list of words into a list of syllables.
Consonantal I is transformed into a J at the start of a word as necessary.
Tuned for poetry and verse, this class is tolerant of isolated single character consonants that
may appear due to elision."""

import copy
import re
import logging
from typing import List

from mqdq.cltk_hax.scansion_constants import ScansionConstants
import mqdq.cltk_hax.string_utils as string_utils

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

__author__ = ['Todd Cook <todd.g.cook@gmail.com>']
__license__ = 'MIT License'


class Syllabifier:
    """Scansion constants can be modified and passed into the constructor if desired."""

    def __init__(self, constants=ScansionConstants()):
        self.constants = constants
        self.consonant_matcher = re.compile("[{}]".format(constants.CONSONANTS))
        self.vowel_matcher = re.compile(
            "[{}]".format(constants.VOWELS + constants.ACCENTED_VOWELS))
        self.consonantal_i_matcher = re.compile(
            r"\b[iIīĪ][{}]".format(constants.VOWELS + constants.ACCENTED_VOWELS))
        self.remove_punct_map = string_utils.remove_punctuation_dict()
        self.kw_matcher = re.compile("[kK][w]")
        self.ACCEPTABLE_CHARS = constants.ACCENTED_VOWELS + constants.VOWELS + ' ' \
                                + constants.CONSONANTS
        self.diphthongs = [d for d in constants.DIPTHONGS if d not in ["ui", "Ui", "uī"]]

    def syllabify(self, words: str) -> List[str]:
        """
        Parse a Latin word into a list of syllable strings.

        :param words: a string containing one latin word or many words separated by spaces.
        :return: list of string, each representing a syllable.

        >>> syllabifier = Syllabifier()
        >>> print(syllabifier.syllabify("fuit"))
        ['fu', 'it']
        >>> print(syllabifier.syllabify("libri"))
        ['li', 'bri']
        >>> print(syllabifier.syllabify("contra"))
        ['con', 'tra']
        >>> print(syllabifier.syllabify("iaculum"))
        ['ja', 'cu', 'lum']
        >>> print(syllabifier.syllabify("amo"))
        ['a', 'mo']
        >>> print(syllabifier.syllabify("bracchia"))
        ['brac', 'chi', 'a']
        >>> print(syllabifier.syllabify("deinde"))
        ['dein', 'de']
        >>> print(syllabifier.syllabify("certabant"))
        ['cer', 'ta', 'bant']
        >>> print(syllabifier.syllabify("aere"))
        ['ae', 're']
        >>> print(syllabifier.syllabify("adiungere"))
        ['ad', 'jun', 'ge', 're']
        >>> print(syllabifier.syllabify("mōns"))
        ['mōns']
        >>> print(syllabifier.syllabify("domus"))
        ['do', 'mus']
        >>> print(syllabifier.syllabify("lixa"))
        ['li', 'xa']
        >>> print(syllabifier.syllabify("asper"))
        ['as', 'per']
        >>> #  handle doubles
        >>> print(syllabifier.syllabify("siccus"))
        ['sic', 'cus']
        >>> # handle liquid + liquid
        >>> print(syllabifier.syllabify("almus"))
        ['al', 'mus']
        >>> # handle liquid + mute
        >>> print(syllabifier.syllabify("ambo"))
        ['am', 'bo']
        >>> print(syllabifier.syllabify("anguis"))
        ['an', 'guis']
        >>> print(syllabifier.syllabify("arbor"))
        ['ar', 'bor']
        >>> print(syllabifier.syllabify("pulcher"))
        ['pul', 'cher']
        >>> print(syllabifier.syllabify("ruptus"))
        ['ru', 'ptus']
        >>> print(syllabifier.syllabify("Bīthÿnus"))
        ['Bī', 'thÿ', 'nus']
        >>> print(syllabifier.syllabify("sanguen"))
        ['san', 'guen']
        >>> print(syllabifier.syllabify("unguentum"))
        ['un', 'guen', 'tum']
        >>> print(syllabifier.syllabify("lingua"))
        ['lin', 'gua']
        >>> print(syllabifier.syllabify("linguā"))
        ['lin', 'guā']
        >>> print(syllabifier.syllabify("languidus"))
        ['lan', 'gui', 'dus']
        >>> print(syllabifier.syllabify("suis"))
        ['su', 'is']
        >>> print(syllabifier.syllabify("habui"))
        ['ha', 'bu', 'i']
        >>> print(syllabifier.syllabify("habuit"))
        ['ha', 'bu', 'it']
        >>> print(syllabifier.syllabify("qui"))
        ['qui']
        >>> print(syllabifier.syllabify("quibus"))
        ['qui', 'bus']
        >>> print(syllabifier.syllabify("hui"))
        ['hui']
        >>> print(syllabifier.syllabify("cui"))
        ['cui']
        >>> print(syllabifier.syllabify("seu"))
        ['seu']
        >>> print(syllabifier.syllabify("huic"))
        ['huic']
        # Handle a 'false prefix' which would otherwise
        # give an incorrect syllabification.
        >>> print(syllabifier.syllabify("servit"))
        ['ser', 'vit']
        >>> print(syllabifier.syllabify("proelia"))
        ['proe', 'li', 'a']
        >>> print(syllabifier.syllabify("roseis"))
        ['ro', 'se', 'is']
        >>> print(syllabifier.syllabify("eius"))
        ['ei', 'us']
        """
        cleaned = words.translate(self.remove_punct_map)
        cleaned = cleaned.replace("qu", "kw")
        cleaned = cleaned.replace("Qu", "Kw")
        cleaned = cleaned.replace("QU", "KW")
        items = cleaned.strip().split(" ")

        for char in cleaned:
            if not char in self.ACCEPTABLE_CHARS:
                LOG.error("Unsupported character found in %s " % cleaned)
                return items
        syllables: list = []
        for item in items:
            syllables += self._setup(item)
        for idx, syl in enumerate(syllables):
            if "kw" in syl:
                syl = syl.replace("kw", "qu")
                syllables[idx] = syl
            if "Kw" in syl:
                syl = syl.replace("Kw", "Qu")
                syllables[idx] = syl
            if "KW" in syl:
                syl = syl.replace("KW", "QU")
                syllables[idx] = syl
            if "gw" in syl:
                syl = syl.replace("gw", "gu")
                syllables[idx] = syl
            if "Gw" in syl:
                syl = syl.replace("Gw", "Gu")
                syllables[idx] = syl

        return string_utils.remove_blank_spaces(syllables)

    def _prefix_split(self, word) -> List[str]:
        
        if word in self.constants.EXCEPTIONS.keys():
            # do this first so that seu gets matched as an exception
            # and doesn't trigger the 'se' prefix
            return self.constants.EXCEPTIONS[word]

        for prefix in self.constants.PREFIXES:
            if word.startswith(prefix):
                (first, rest) = string_utils.split_on(word, prefix)
                # There are some prefixes which get in the way of real words.
                # as a bandaid, make sure that we don't consider something to
                # be a prefix if it leaves a 'rest' that is phonotactically
                # impossible.
                if not self._legal_onset(rest):
                    return [word]
                if self._contains_vowels(rest):
                    return([first] + self._prefix_split(rest))
                # a word like pror can happen from ellision
                return [word]
        return [word]

    def _setup(self, word) -> List[str]:
        """
        Prepares a word for syllable processing.

        If the word starts with a prefix, process it separately.
        :param word:
        :return:
        """
        if len(word) == 1:
            return [word]
        if word in self.constants.EXCEPTIONS.keys():
            # do this first so that seu gets matched as an exception
            # and doesn't trigger the 'se' prefix
            return self.constants.EXCEPTIONS[word]
        splits = self._prefix_split(word)
        # more readable than a list comp. with flatten ;)
        final = []
        for s in splits:
            final += string_utils.remove_blank_spaces(self._process(s))
        return final

    def _legal_onset(self, word) -> bool:
        if len(word) < 2:
            return True
        if self._contains_vowels(word[:2]):
            # either of the first two letters are vowels
            # so this is legal
            return True
        # starts with a two consonants now...
        if word[0] in self.constants.MUTES and word[1] in self.constants.CLUSTERABLE:
            return True
        if word[1] in self.constants.LIQUIDS or word[1] in "sS":
            # simplification, but we'll provisionally
            # allow any consonant + liquid and Greek
            # words like psolen etc etc
            if word[0] not in self.constants.MUTES and word[0] not in self.constants.FRICATIVES:
                return False
            return True
        if word[:1].lower() == "mn":
            return True
        # default
        return False
        

    def convert_consonantal_i(self, word) -> str:
        """Convert i to j when at the start of a word."""
        match = list(self.consonantal_i_matcher.finditer(word))
        if match and word[1] != 'i':
            if word[0].isupper():
                return "J" + word[1:]
            return "j" + word[1:]
        return word

    def _process(self, word: str) -> List[str]:
        """
        Process a word into a list of strings representing the syllables of the word. This
        method describes rules for consonant grouping behaviors and then iteratively applies those
        rules the list of letters that comprise the word, until all the letters are grouped into
        appropriate syllable groups.

        :param word:
        :return:
        """
        # Checking this again lets us add more exceptions, in this instance,
        # compounds like eunto, euntis
        if word in self.constants.EXCEPTIONS.keys():
            # do this first so that seu gets matched as an exception
            # and doesn't trigger the 'se' prefix
            return self.constants.EXCEPTIONS[word]

        #   if a blank arrives from splitting, just return an empty list
        if len(word.strip()) == 0:
            return []
        word = self.convert_consonantal_i(word)
        my_word = " " + word + " "
        letters = list(my_word)
        positions = []
        for dipth in self.diphthongs:
            if dipth in my_word:
                dipth_matcher = re.compile("{}".format(dipth))
                matches = dipth_matcher.finditer(my_word)
                for match in matches:
                    (start, end) = match.span()
                    positions.append(start)
        matches = self.kw_matcher.finditer(my_word)
        for match in matches:
            (start, end) = match.span()
            positions.append(start)
        letters = string_utils.merge_next(letters, positions)
        letters = string_utils.remove_blanks(letters)
        positions.clear()
        if not self._contains_vowels("".join(letters)):
            return ["".join(letters).strip()]  # occurs when only 'qu' appears by ellision
        positions = self._starting_consonants_only(letters)
        while len(positions) > 0:
            letters = string_utils.move_consonant_right(letters, positions)
            letters = string_utils.remove_blanks(letters)
            positions = self._starting_consonants_only(letters)
        positions = self._ending_consonants_only(letters)
        while len(positions) > 0:
            letters = string_utils.move_consonant_left(letters, positions)
            letters = string_utils.remove_blanks(letters)
            positions = self._ending_consonants_only(letters)
        positions = self._find_solo_consonant(letters)
        while len(positions) > 0:
            letters = self._move_consonant(letters, positions)
            letters = string_utils.remove_blanks(letters)
            positions = self._find_solo_consonant(letters)
        positions = self._find_consonant_cluster(letters)
        while len(positions) > 0:
            letters = self._move_consonant(letters, positions)
            letters = string_utils.remove_blanks(letters)
            positions = self._find_consonant_cluster(letters)
        return letters

    def _contains_consonants(self, letter_group: str) -> bool:
        """Check if a string contains consonants."""
        return self.consonant_matcher.search(letter_group) is not None

    def _contains_vowels(self, letter_group: str) -> bool:
        """Check if a string contains vowels."""
        return self.vowel_matcher.search(letter_group) is not None

    def _ends_with_vowel(self, letter_group: str) -> bool:
        """Check if a string ends with a vowel."""
        if len(letter_group) == 0:
            return False
        return self._contains_vowels(letter_group[-1])

    def _starts_with_vowel(self, letter_group: str) -> bool:
        """Check if a string starts with a vowel."""
        if len(letter_group) == 0:
            return False
        return self._contains_vowels(letter_group[0])

    def _starting_consonants_only(self, letters: list) -> list:
        """Return a list of starting consonant positions."""
        for idx, letter in enumerate(letters):
            if not self._contains_vowels(letter) and self._contains_consonants(letter):
                return [idx]
            if self._contains_vowels(letter):
                return []
            if self._contains_vowels(letter) and self._contains_consonants(letter):
                return []
        return []

    def _ending_consonants_only(self, letters: List[str]) -> List[int]:
        """Return a list of positions for ending consonants."""
        reversed_letters = list(reversed(letters))
        length = len(letters)
        for idx, letter in enumerate(reversed_letters):
            if not self._contains_vowels(letter) and self._contains_consonants(letter):
                return [(length - idx) - 1]
            if self._contains_vowels(letter):
                return []
            if self._contains_vowels(letter) and self._contains_consonants(letter):
                return []
        return []

    def _find_solo_consonant(self, letters: List[str]) -> List[int]:
        """Find the positions of any solo consonants that are not yet paired with a vowel."""
        solos = []
        for idx, letter in enumerate(letters):
            if len(letter) == 1 and self._contains_consonants(letter):
                solos.append(idx)
        return solos

    def _find_consonant_cluster(self, letters: List[str]) -> List[int]:
        """
        Find clusters of consonants that do not contain a vowel.
        :param letters:
        :return:
        """
        for idx, letter_group in enumerate(letters):
            if self._contains_consonants(letter_group) and not self._contains_vowels(letter_group):
                return [idx]
        return []

    def _move_consonant(self, letters: list, positions: List[int]) -> List[str]:
        """
        Given a list of consonant positions, move the consonants according to certain
        consonant syllable behavioral rules for gathering and grouping.

        :param letters:
        :param positions:
        :return:
        """
        for pos in positions:
            previous_letter = letters[pos - 1]
            consonant = letters[pos]
            next_letter = letters[pos + 1]
            if self._contains_vowels(next_letter) and self._starts_with_vowel(next_letter):
                return string_utils.move_consonant_right(letters, [pos])
            if self._contains_vowels(previous_letter) and self._ends_with_vowel(
                    previous_letter) and len(previous_letter) == 1:
                return string_utils.move_consonant_left(letters, [pos])
            if previous_letter + consonant in self.constants.ASPIRATES:
                return string_utils.move_consonant_left(letters, [pos])
            if consonant + next_letter in self.constants.ASPIRATES:
                return string_utils.move_consonant_right(letters, [pos])
            if next_letter[0] == consonant:
                return string_utils.move_consonant_left(letters, [pos])
            if consonant in self.constants.MUTES and next_letter[0] in self.constants.LIQUIDS:
                return string_utils.move_consonant_right(letters, [pos])
            if consonant in ['k', 'K'] and next_letter[0] in ['w', 'W']:
                return string_utils.move_consonant_right(letters, [pos])                
            if consonant in ['c', 'C'] and next_letter[0] in self.constants.MUTES:
                return string_utils.move_consonant_left(letters, [pos])
            #if next_letter[0] in self.constants.MUTES and previous_letter[-1] not in self.constants.MUTES:
            if previous_letter[-1] not in self.constants.MUTES:
                # prefer to move a stop back to a fricative etc than forward to make a stop cluster
                return string_utils.move_consonant_left(letters, [pos])
            if self._contains_consonants(next_letter[0]) and self._starts_with_vowel(
                    previous_letter[-1]):
                return string_utils.move_consonant_left(letters, [pos])
            # fall through case
            if self._contains_consonants(next_letter[0]):
                return string_utils.move_consonant_right(letters, [pos])
        return letters

    def get_syllable_count(self, syllables: List[str]) -> int:
        """
        Counts the number of syllable groups that would occur after ellision.

        Often we will want preserve the position and separation of syllables so that they
        can be used to reconstitute a line, and apply stresses to the original word positions.
        However, we also want to be able to count the number of syllables accurately.

        :param syllables:
        :return:

        >>> syllabifier = Syllabifier()
        >>> print(syllabifier.get_syllable_count([
        ... 'Jām', 'tūm', 'c', 'au', 'sus', 'es', 'u', 'nus', 'I', 'ta', 'lo', 'rum']))
        11
        """
        tmp_syllables = copy.deepcopy(syllables)
        return len(string_utils.remove_blank_spaces(
            string_utils.move_consonant_right(tmp_syllables,
                                             self._find_solo_consonant(tmp_syllables))))

