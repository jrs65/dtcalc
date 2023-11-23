"""Time calculation parsing."""

import re
from datetime import datetime, timedelta
from enum import Enum
from typing import ClassVar

__version__ = "2023.11.0"


class TokenType(Enum):
    """An enum for tracking the token type."""

    LITERAL_DATETIME = 1
    LITERAL_DURATION = 2
    LITERAL_NUMBER = 3
    IDENTIFIER = 4
    LEFT_PAREN = 5
    RIGHT_PAREN = 6
    BINOP = 7


class Token:
    """A token to process.

    Attributes
    ----------
    type
        Type of the token.
    value
        The string corresponding to the token.
    """

    def __init__(self, type_: TokenType, value: str):
        self.type = type_
        self.value = value

    def __repr__(self) -> str:
        """Generate a string representation."""
        return f"Token({self.type.name}: {self.value})"


class UnitType(Enum):
    """The unit of a node in a time calculation."""

    DATETIME = 1
    DURATION = 2
    NUMBER = 3


class Node:
    """An AST node for a time calculation."""

    def evaluate(self) -> datetime | timedelta | float:
        """Evaluate the calculation starting at this point."""
        return self._evaluate()  # Must be defined in subclasses

    @property
    def unit(self) -> UnitType:
        """The units of the result."""
        return self._unit  # Must be set in a subclass


class Literal(Node):
    """Baseclass for a literal."""

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        """Represent the calculation in RPN form."""
        return self.text


class DurationLiteral(Literal):
    """AST node for a duration literal."""

    pattern = r"\d+(\.\d+)?[wdhms]"

    _unit = UnitType.DURATION
    _duration_codes: ClassVar[dict[str, str]] = {
        d[0]: d for d in ["seconds", "minutes", "hours", "days", "weeks"]
    }

    def _evaluate(self) -> timedelta:
        unit = self._duration_codes[self.text[-1]]
        num = float(self.text[:-1])

        return timedelta(**{unit: num})


class DatetimeLiteral(Literal):
    """AST node for a datetime literal. ISO8601 format."""

    pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[-+]\d{2}:\d{2})"

    _unit = UnitType.DATETIME

    def _evaluate(self) -> datetime:
        return datetime.fromisoformat(self.text)


class NumberLiteral(Literal):
    """AST node for a number."""

    pattern = r"\d+(\.\d+)?"

    _unit = UnitType.NUMBER

    def _evaluate(self) -> float:
        """Evaluate a literal number."""
        return float(self.text)


class BinOp(Node):
    """Binary infix operator."""

    pattern = r"(\+|\-|\*|\/)"

    def __init__(self, op: str, lhs: Node, rhs: Node):
        final_unit = self._check_units(op, lhs.unit, rhs.unit)

        if final_unit is None:
            raise TypeError("Incompatible types to binary operator.")

        self.op = op
        self.lhs = lhs
        self.rhs = rhs
        self._unit = final_unit

    @classmethod
    def _check_units(cls, op: str, lunit: UnitType, runit: UnitType) -> UnitType:
        """Check the operation types for compatibility and compute the final type.

        Returns `None` if the types are incompatible.
        """
        # List the allowed operations and return types for each combination of units.
        # Only allowed combinations are listed.
        allowed_ops = {
            # Num-Num
            (UnitType.NUMBER, UnitType.NUMBER, "*"): UnitType.NUMBER,
            (UnitType.NUMBER, UnitType.NUMBER, "/"): UnitType.NUMBER,
            (UnitType.NUMBER, UnitType.NUMBER, "+"): UnitType.NUMBER,
            (UnitType.NUMBER, UnitType.NUMBER, "-"): UnitType.NUMBER,
            # Num-Dur and rev
            (UnitType.NUMBER, UnitType.DURATION, "*"): UnitType.DURATION,
            (UnitType.DURATION, UnitType.NUMBER, "*"): UnitType.DURATION,
            (UnitType.DURATION, UnitType.NUMBER, "/"): UnitType.DURATION,
            # Num-Dat and rev (none)
            # Dur-Dur
            (UnitType.DURATION, UnitType.DURATION, "+"): UnitType.DURATION,
            (UnitType.DURATION, UnitType.DURATION, "-"): UnitType.DURATION,
            # Dur-Dat and rev
            (UnitType.DURATION, UnitType.DATETIME, "+"): UnitType.DATETIME,
            (UnitType.DURATION, UnitType.DATETIME, "-"): UnitType.DATETIME,
            (UnitType.DATETIME, UnitType.DURATION, "+"): UnitType.DATETIME,
            (UnitType.DATETIME, UnitType.DURATION, "-"): UnitType.DATETIME,
            # Dat-Dat
            (UnitType.DATETIME, UnitType.DATETIME, "-"): UnitType.DURATION,
        }

        return allowed_ops.get((lunit, runit, op), None)

    @classmethod
    def precedence(cls, op: str) -> int:
        """Get the precedence for the operator."""
        precedence_map = {
            "+": 1,
            "-": 1,
            "*": 2,
            "/": 2,
        }
        return precedence_map[op]

    def _evaluate(self):
        lval = self.lhs.evaluate()
        rval = self.rhs.evaluate()

        match self.op:
            case "+":
                return lval + rval
            case "-":
                return lval - rval
            case "*":
                return lval * rval
            case "/":
                return lval / rval

        raise RuntimeError("Unknown operation.")

    def __repr__(self) -> str:
        """Generate a string representation."""
        return f"({self.op} {self.lhs} {self.rhs})"


class Identifier(Node):
    """An unknown identifier that must be defined before evaluation."""

    pattern = r"[A-Za-z]\w*"
    _unit = UnitType.DATETIME

    def __init__(self, name: str) -> None:
        self.name = name

    def _evaluate(self) -> datetime:
        if self._dt is None or not isinstance(self._dt, datetime):
            raise RuntimeError("Undefined identifier. Use set_value to define it.")
        return self._dt

    def set_value(self, dt: datetime) -> None:
        """Set a datetime value for the identifier."""
        self._dt = dt

    def __repr__(self) -> str:
        """Generate a string representation."""
        return self.name


token_patterns = [
    (DatetimeLiteral.pattern, TokenType.LITERAL_DATETIME),
    (DurationLiteral.pattern, TokenType.LITERAL_DURATION),
    (NumberLiteral.pattern, TokenType.LITERAL_NUMBER),
    (Identifier.pattern, TokenType.IDENTIFIER),
    (r"\(", TokenType.LEFT_PAREN),
    (r"\)", TokenType.RIGHT_PAREN),
    (BinOp.pattern, TokenType.BINOP),
]
token_patterns = [(re.compile(pat), t) for pat, t in token_patterns]


def tokenize(s: str) -> list[Token]:
    """Tokenize a datetime arithmetic expression."""
    tokens = []
    i = 0

    while i < len(s):
        # Chomp whitespace
        if s[i] == " ":
            i += 1
            continue

        # Go over the token patterns and try to identify each
        for regex, t in token_patterns:
            if m := regex.match(s, pos=i):
                item = m.group(0)
                i = m.end()

                tokens.append(Token(t, item))
                break
        else:
            raise RuntimeError(
                f'Could not identify token in remaining string "{s[i:]}". '
                f'Found tokens "{tokens}".',
            )

    return tokens


class ParseError(RuntimeError):
    """Error when parsing the datetime calculation."""


def _parse_atom(
    tokens: list[tuple[str, str]],
    identifiers: dict[str, Identifier],
) -> Node:
    # Parse to process an atom, either a terminal node or a parenthetic expression
    # tokens: list of tokens to process
    # identifiers: a dictionary used to track any identifiers found
    if len(tokens) == 0:
        raise RuntimeError("Expected tokens.")

    token = tokens.pop(0)

    # Check the type of token and process appropriately
    match token.type:
        case TokenType.LITERAL_DATETIME:
            return DatetimeLiteral(token.value)
        case TokenType.LITERAL_DURATION:
            return DurationLiteral(token.value)
        case TokenType.LITERAL_NUMBER:
            return NumberLiteral(token.value)
        case TokenType.IDENTIFIER:
            if token.value not in identifiers:
                identifiers[token.value] = Identifier(token.value)
            return identifiers[token.value]

    # If the token is an opening parenthesis we must recurse to parse it
    if token.type == TokenType.LEFT_PAREN:
        expr = _parse(tokens, identifiers)

        # Check that there was no issue
        if len(tokens) == 0:
            raise ParseError("Unclosed parentheses.")

        token = tokens.pop(0)

        if token.type != TokenType.RIGHT_PAREN:
            raise ParseError(
                f"Expected right parentheses. Found {token.type=}, {token.value=}",
            )

        return expr

    # If we get here we found a token but didn't understand it.
    raise ParseError(f"Found unexpected token. {token.type=} {token.value=}")


def _parse(
    tokens: list[Token],
    identifiers: dict[str, Identifier],
    min_precedence: int = 0,
) -> Node:
    # Worker routine for the parsing.
    # tokens: list of what is remaining
    # identifiers: dict of current identifier names and nodes
    # min_prec: minimum precedence to process at

    lhs = _parse_atom(tokens, identifiers)

    while True:
        # Check if we are at the end of the token list, or those in this parentheses
        if len(tokens) == 0 or tokens[0].type != TokenType.BINOP:
            break

        # Find the precedence of the operator and stop processing if it's lower than the
        # threshold
        if (precedence := BinOp.precedence(tokens[0].value)) < min_precedence:
            break

        token = tokens.pop(0)

        if token.type != TokenType.BINOP:
            raise ParseError(f"Expected binary operation. {token.type=} {token.value=}")

        # Recurse to parse the RHS of the operator
        # Bump the precedence up one as our operators all are left associative
        rhs = _parse(tokens, identifiers, min_precedence=(precedence + 1))

        # Create the AST node
        lhs = BinOp(token.value, lhs, rhs)

    return lhs


class DTCalc:
    """The result of a dtcalc object.

    Attributes
    ----------
    root
        The root of the AST.
    identifiers
        A dictionary of identifiers that much be defined before evaluation.
    """

    def __init__(self, root: Node, identifiers: dict[str, Identifier]):
        self.root = root
        self.identifiers = identifiers

    def evaluate(
        self, **identifiers: dict[str, datetime],
    ) -> datetime | timedelta | float:
        """Perform the calculation.

        Parameters
        ----------
        identifiers
            Keyword arguments setting any unknown identifiers.
        """
        for name, value in identifiers.items():
            self.identifiers[name].set_value(value)

        return self.root.evaluate()

    @classmethod
    def from_string(cls, s: str) -> Node:
        """Parse a datetime calculation.

        Parameters
        ----------
        s
            Datetime calculation string to parse.

        Returns
        -------
        dtcalc
            A parsed object representing the calculation.
        """
        # This is implemented using a precedence climbing parser. See
        # https://eli.thegreenplace.net/2012/08/02/parsing-expressions-by-precedence-climbing
        # for a useful reference.

        tokens = tokenize(s)

        identifiers = {}

        root = _parse(tokens, identifiers)

        return cls(root, identifiers)


def parse(s: str) -> DTCalc:
    """Parse a datetime calculation.

    Parameters
    ----------
    s
        Datetime calculation string to parse.

    Returns
    -------
    dtcalc
        A parsed object representing the calculation.
    """
    return DTCalc.from_string(s)
