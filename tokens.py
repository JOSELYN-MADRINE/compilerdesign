from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    # Literals
    INT_LITERAL    = auto()
    FLOAT_LITERAL  = auto()
    STRING_LITERAL = auto()
    BOOL_LITERAL   = auto()

    # Identifier
    IDENTIFIER = auto()

    # Type keywords
    KW_INT    = auto()
    KW_FLOAT  = auto()
    KW_STRING = auto()
    KW_BOOL   = auto()

    # Control-flow keywords
    KW_IF    = auto()
    KW_ELSE  = auto()
    KW_WHILE = auto()
    KW_PRINT = auto()
    KW_TRUE  = auto()
    KW_FALSE = auto()

    # Arithmetic operators
    PLUS     = auto()
    MINUS    = auto()
    MULTIPLY = auto()
    DIVIDE   = auto()
    MODULO   = auto()

    # Comparison operators
    EQ  = auto()   # ==
    NEQ = auto()   # !=
    LT  = auto()   # <
    GT  = auto()   # >
    LTE = auto()   # <=
    GTE = auto()   # >=

    # Logical operators
    AND = auto()   # &&
    OR  = auto()   # ||
    NOT = auto()   # !

    # Assignment
    ASSIGN = auto()  # =

    # Delimiters
    LPAREN    = auto()   # (
    RPAREN    = auto()   # )
    LBRACE    = auto()   # {
    RBRACE    = auto()   # }
    SEMICOLON = auto()   # ;

    # Special
    EOF     = auto()
    UNKNOWN = auto()


KEYWORDS: dict[str, TokenType] = {
    'int':    TokenType.KW_INT,
    'float':  TokenType.KW_FLOAT,
    'string': TokenType.KW_STRING,
    'bool':   TokenType.KW_BOOL,
    'if':     TokenType.KW_IF,
    'else':   TokenType.KW_ELSE,
    'while':  TokenType.KW_WHILE,
    'print':  TokenType.KW_PRINT,
    'true':   TokenType.KW_TRUE,
    'false':  TokenType.KW_FALSE,
}


@dataclass
class Token:
    type:  TokenType
    value: str
    line:  int
    col:   int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.col})"
