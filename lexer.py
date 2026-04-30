from tokens import Token, TokenType, KEYWORDS
from typing import List, Tuple


class Lexer:
    """Phase 1 – Lexical Analysis: converts raw source text into a token stream."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.col    = 1
        self.errors: List[str] = []

    # ------------------------------------------------------------------ helpers

    def _current(self) -> str:
        return self.source[self.pos] if self.pos < len(self.source) else '\0'

    def _peek(self, offset: int = 1) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else '\0'

    def _advance(self) -> str:
        ch = self._current()
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace(self) -> None:
        while self._current() in ' \t\r\n':
            self._advance()

    def _skip_line_comment(self) -> None:
        while self._current() not in ('\n', '\0'):
            self._advance()

    # ------------------------------------------------------------------ readers

    def _read_number(self) -> Token:
        start_line, start_col = self.line, self.col
        num, is_float = '', False

        while self._current().isdigit():
            num += self._advance()

        if self._current() == '.' and self._peek().isdigit():
            is_float = True
            num += self._advance()
            while self._current().isdigit():
                num += self._advance()

        tt = TokenType.FLOAT_LITERAL if is_float else TokenType.INT_LITERAL
        return Token(tt, num, start_line, start_col)

    def _read_string(self) -> Token:
        start_line, start_col = self.line, self.col
        self._advance()          # consume opening "
        s = ''
        while self._current() != '"' and self._current() != '\0':
            if self._current() == '\\':
                self._advance()
                esc = self._advance()
                s += {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(esc, esc)
            else:
                s += self._advance()

        if self._current() == '"':
            self._advance()      # consume closing "
        else:
            self.errors.append(f"Line {start_line}: Unterminated string literal")

        return Token(TokenType.STRING_LITERAL, s, start_line, start_col)

    def _read_identifier(self) -> Token:
        start_line, start_col = self.line, self.col
        name = ''
        while self._current().isalnum() or self._current() == '_':
            name += self._advance()

        tt = KEYWORDS.get(name, TokenType.IDENTIFIER)
        # true/false → BOOL_LITERAL
        if tt in (TokenType.KW_TRUE, TokenType.KW_FALSE):
            return Token(TokenType.BOOL_LITERAL, name, start_line, start_col)
        return Token(tt, name, start_line, start_col)

    # ------------------------------------------------------------------ public

    def tokenize(self) -> Tuple[List[Token], List[str]]:
        """Return (token_list, error_list)."""
        tokens: List[Token] = []

        while True:
            self._skip_whitespace()

            if self._current() == '\0':
                tokens.append(Token(TokenType.EOF, 'EOF', self.line, self.col))
                break

            ch   = self._current()
            line = self.line
            col  = self.col

            # ── single-line comment ──────────────────────────────────────────
            if ch == '/' and self._peek() == '/':
                self._advance(); self._advance()
                self._skip_line_comment()
                continue

            # ── numeric literal ──────────────────────────────────────────────
            if ch.isdigit():
                tokens.append(self._read_number())
                continue

            # ── string literal ───────────────────────────────────────────────
            if ch == '"':
                tokens.append(self._read_string())
                continue

            # ── identifier / keyword ─────────────────────────────────────────
            if ch.isalpha() or ch == '_':
                tokens.append(self._read_identifier())
                continue

            # ── two-character operators ──────────────────────────────────────
            two = ch + self._peek()
            if two == '==':
                self._advance(); self._advance()
                tokens.append(Token(TokenType.EQ,  '==', line, col)); continue
            if two == '!=':
                self._advance(); self._advance()
                tokens.append(Token(TokenType.NEQ, '!=', line, col)); continue
            if two == '<=':
                self._advance(); self._advance()
                tokens.append(Token(TokenType.LTE, '<=', line, col)); continue
            if two == '>=':
                self._advance(); self._advance()
                tokens.append(Token(TokenType.GTE, '>=', line, col)); continue
            if two == '&&':
                self._advance(); self._advance()
                tokens.append(Token(TokenType.AND, '&&', line, col)); continue
            if two == '||':
                self._advance(); self._advance()
                tokens.append(Token(TokenType.OR,  '||', line, col)); continue

            # ── single-character tokens ──────────────────────────────────────
            SINGLE = {
                '+': TokenType.PLUS,  '-': TokenType.MINUS,
                '*': TokenType.MULTIPLY, '/': TokenType.DIVIDE,
                '%': TokenType.MODULO,
                '<': TokenType.LT,    '>': TokenType.GT,
                '!': TokenType.NOT,   '=': TokenType.ASSIGN,
                '(': TokenType.LPAREN,')'  : TokenType.RPAREN,
                '{': TokenType.LBRACE,'}': TokenType.RBRACE,
                ';': TokenType.SEMICOLON,
            }
            if ch in SINGLE:
                self._advance()
                tokens.append(Token(SINGLE[ch], ch, line, col))
            else:
                self.errors.append(
                    f"Line {line}, Col {col}: Unknown character '{ch}'"
                )
                self._advance()

        return tokens, self.errors
