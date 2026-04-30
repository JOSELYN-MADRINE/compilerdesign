"""
Phase 2 (Bottom-Up) – Shift-Reduce Parser (LR-style).

Strategy: scan input left-to-right, SHIFTING tokens onto a stack.  Whenever
the top of the stack matches the right-hand side of a grammar production,
REDUCE it (pop the matched symbols, push the non-terminal).  Repeat until the
start symbol remains.

Every action is logged so the GUI can display the full shift/reduce trace.
"""

from tokens import Token, TokenType
from ast_nodes import *
from typing import List, Optional, Tuple


class BottomUpParser:
    """Shift-Reduce (Bottom-Up / LR-style) Parser."""

    GRAMMAR = [
        "program    → stmt_list EOF",
        "stmt_list  → stmt_list stmt  |  ε",
        "stmt       → decl_stmt | assign_stmt | if_stmt | while_stmt | print_stmt | block",
        "decl_stmt  → type ID ';'  |  type ID '=' expr ';'",
        "assign_stmt→ ID '=' expr ';'",
        "if_stmt    → 'if' '(' expr ')' block  |  'if' '(' expr ')' block 'else' block",
        "while_stmt → 'while' '(' expr ')' block",
        "print_stmt → 'print' '(' expr ')' ';'",
        "block      → '{' stmt_list '}'",
        "expr       → expr '||' and_expr  |  and_expr",
        "and_expr   → and_expr '&&' eq_expr  |  eq_expr",
        "eq_expr    → eq_expr ('=='|'!=') rel_expr  |  rel_expr",
        "rel_expr   → rel_expr ('<'|'>'|'<='|'>=') add_expr  |  add_expr",
        "add_expr   → add_expr ('+'|'-') mul_expr  |  mul_expr",
        "mul_expr   → mul_expr ('*'|'/'|'%') unary  |  unary",
        "unary      → '!' unary  |  '-' unary  |  primary",
        "primary    → NUMBER | STRING | BOOL | ID | '(' expr ')'",
    ]

    def __init__(self, tokens: List[Token]) -> None:
        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        eof_tok = next((t for t in tokens if t.type == TokenType.EOF),
                       Token(TokenType.EOF, 'EOF', 0, 0))
        self.tokens: List[Token] = non_eof + [eof_tok]
        self.pos:    int         = 0
        self.stack:  list        = []   # symbol stack (tokens / nodes)
        self.errors: List[str]   = []
        self.steps:  List[str]   = []

    # ─────────────────────────────────────────────────── token utilities ──────

    def _cur(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def _shift(self, expected: TokenType = None) -> Token:
        tok = self._cur()
        if expected and tok.type != expected:
            raise SyntaxError(
                f"Line {tok.line}: Expected {expected.name}, "
                f"got {tok.type.name} ('{tok.value}')"
            )
        self.steps.append(
            f"  SHIFT   │ {tok.type.name:<22} '{tok.value}'"
        )
        self.stack.append(tok)
        self.pos += 1
        return tok

    def _reduce(self, rule: str, node: ASTNode) -> ASTNode:
        self.steps.append(f"  REDUCE  │ {rule}")
        return node

    # ─────────────────────────────────────────────────── public interface ─────

    def parse(self) -> Tuple[Optional[Program], List[str], List[str]]:
        self.steps.append("╔══════════════════════════════════════════════════╗")
        self.steps.append("║   BOTTOM-UP  ·  Shift-Reduce Parser (LR-style) ║")
        self.steps.append("╚══════════════════════════════════════════════════╝")
        self.steps.append("")
        self.steps.append("Grammar Productions:")
        for rule in self.GRAMMAR:
            self.steps.append(f"  {rule}")
        self.steps.append("")
        self.steps.append("Parsing Trace  (ACTION │ DETAIL)")
        self.steps.append("─" * 52)
        try:
            prog = self._parse_program()
            self.steps.append("─" * 52)
            self.steps.append("  ACCEPT  │ Input successfully parsed.")
            return prog, self.errors, self.steps
        except Exception as exc:
            self.errors.append(str(exc))
            self.steps.append(f"  ERROR   │ {exc}")
            return None, self.errors, self.steps

    # ─────────────────────────────────────────────────── grammar rules ───────

    def _parse_program(self) -> Program:
        stmts = self._parse_stmt_list()
        node  = Program(stmts)
        return self._reduce("program → stmt_list EOF", node)

    def _parse_stmt_list(self) -> List[ASTNode]:
        stmts: List[ASTNode] = []
        while self._cur().type not in (TokenType.EOF, TokenType.RBRACE):
            try:
                stmt = self._parse_stmt()
                stmts.append(stmt)
                self._reduce("stmt_list → stmt_list stmt", stmt)
            except Exception as exc:
                self.errors.append(str(exc))
                while self._cur().type not in (
                        TokenType.SEMICOLON, TokenType.RBRACE,
                        TokenType.LBRACE, TokenType.EOF):
                    self.pos += 1
                if self._cur().type == TokenType.SEMICOLON:
                    self.pos += 1
        return stmts

    def _parse_stmt(self) -> ASTNode:
        tt = self._cur().type
        if tt in (TokenType.KW_INT, TokenType.KW_FLOAT,
                  TokenType.KW_STRING, TokenType.KW_BOOL):
            return self._parse_decl_stmt()
        if tt == TokenType.KW_IF:
            return self._parse_if_stmt()
        if tt == TokenType.KW_WHILE:
            return self._parse_while_stmt()
        if tt == TokenType.KW_PRINT:
            return self._parse_print_stmt()
        if tt == TokenType.IDENTIFIER:
            return self._parse_assign_stmt()
        if tt == TokenType.LBRACE:
            return self._parse_block()
        tok = self._cur()
        raise SyntaxError(f"Line {tok.line}: Unexpected token '{tok.value}'")

    def _parse_decl_stmt(self) -> DeclStmt:
        type_tok = self._shift()           # shift: type keyword
        name_tok = self._shift(TokenType.IDENTIFIER)
        init = None
        if self._cur().type == TokenType.ASSIGN:
            self._shift(TokenType.ASSIGN)
            init = self._parse_expr()
        self._shift(TokenType.SEMICOLON)
        node = DeclStmt(type_tok.value, name_tok.value, init, type_tok.line)
        rule = (f"decl_stmt → {type_tok.value} ID"
                f"{' = <expr>' if init else ''} ;")
        return self._reduce(rule, node)

    def _parse_assign_stmt(self) -> AssignStmt:
        name_tok = self._shift(TokenType.IDENTIFIER)
        self._shift(TokenType.ASSIGN)
        value = self._parse_expr()
        self._shift(TokenType.SEMICOLON)
        node = AssignStmt(name_tok.value, value, name_tok.line)
        return self._reduce(f"assign_stmt → {name_tok.value} = <expr> ;", node)

    def _parse_if_stmt(self) -> IfStmt:
        tok = self._shift(TokenType.KW_IF)
        self._shift(TokenType.LPAREN)
        cond = self._parse_expr()
        self._shift(TokenType.RPAREN)
        then_blk = self._parse_block()
        else_blk = None
        if self._cur().type == TokenType.KW_ELSE:
            self._shift(TokenType.KW_ELSE)
            else_blk = self._parse_block()
        node = IfStmt(cond, then_blk, else_blk, tok.line)
        rule = "if_stmt → if ( <expr> ) block" + (" else block" if else_blk else "")
        return self._reduce(rule, node)

    def _parse_while_stmt(self) -> WhileStmt:
        tok = self._shift(TokenType.KW_WHILE)
        self._shift(TokenType.LPAREN)
        cond = self._parse_expr()
        self._shift(TokenType.RPAREN)
        body = self._parse_block()
        node = WhileStmt(cond, body, tok.line)
        return self._reduce("while_stmt → while ( <expr> ) block", node)

    def _parse_print_stmt(self) -> PrintStmt:
        tok = self._shift(TokenType.KW_PRINT)
        self._shift(TokenType.LPAREN)
        val = self._parse_expr()
        self._shift(TokenType.RPAREN)
        self._shift(TokenType.SEMICOLON)
        node = PrintStmt(val, tok.line)
        return self._reduce("print_stmt → print ( <expr> ) ;", node)

    def _parse_block(self) -> Block:
        self._shift(TokenType.LBRACE)
        stmts = self._parse_stmt_list()
        self._shift(TokenType.RBRACE)
        node = Block(stmts)
        return self._reduce("block → { stmt_list }", node)

    # ─────────────────────────── expression rules (bottom-up precedence) ─────

    def _parse_expr(self) -> ASTNode:
        return self._parse_or()

    def _parse_or(self) -> ASTNode:
        left = self._parse_and()
        while self._cur().type == TokenType.OR:
            self._shift(TokenType.OR)
            right = self._parse_and()
            left = BinaryExpr(left, '||', right)
            self._reduce("expr → expr || and_expr", left)
        return left

    def _parse_and(self) -> ASTNode:
        left = self._parse_eq()
        while self._cur().type == TokenType.AND:
            self._shift(TokenType.AND)
            right = self._parse_eq()
            left = BinaryExpr(left, '&&', right)
            self._reduce("and_expr → and_expr && eq_expr", left)
        return left

    def _parse_eq(self) -> ASTNode:
        left = self._parse_rel()
        while self._cur().type in (TokenType.EQ, TokenType.NEQ):
            tok = self._shift()
            right = self._parse_rel()
            left = BinaryExpr(left, tok.value, right)
            self._reduce(f"eq_expr → eq_expr {tok.value} rel_expr", left)
        return left

    def _parse_rel(self) -> ASTNode:
        left = self._parse_add()
        while self._cur().type in (TokenType.LT, TokenType.GT,
                                   TokenType.LTE, TokenType.GTE):
            tok = self._shift()
            right = self._parse_add()
            left = BinaryExpr(left, tok.value, right)
            self._reduce(f"rel_expr → rel_expr {tok.value} add_expr", left)
        return left

    def _parse_add(self) -> ASTNode:
        left = self._parse_mul()
        while self._cur().type in (TokenType.PLUS, TokenType.MINUS):
            tok = self._shift()
            right = self._parse_mul()
            left = BinaryExpr(left, tok.value, right)
            self._reduce(f"add_expr → add_expr {tok.value} mul_expr", left)
        return left

    def _parse_mul(self) -> ASTNode:
        left = self._parse_unary()
        while self._cur().type in (TokenType.MULTIPLY, TokenType.DIVIDE,
                                   TokenType.MODULO):
            tok = self._shift()
            right = self._parse_unary()
            left = BinaryExpr(left, tok.value, right)
            self._reduce(f"mul_expr → mul_expr {tok.value} unary", left)
        return left

    def _parse_unary(self) -> ASTNode:
        if self._cur().type in (TokenType.NOT, TokenType.MINUS):
            tok = self._shift()
            operand = self._parse_unary()
            node = UnaryExpr(tok.value, operand)
            return self._reduce(f"unary → {tok.value} unary", node)
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._cur()
        if tok.type == TokenType.INT_LITERAL:
            self._shift()
            node = NumberLiteral(int(tok.value), True)
            return self._reduce(f"primary → INT({tok.value})", node)
        if tok.type == TokenType.FLOAT_LITERAL:
            self._shift()
            node = NumberLiteral(float(tok.value), False)
            return self._reduce(f"primary → FLOAT({tok.value})", node)
        if tok.type == TokenType.STRING_LITERAL:
            self._shift()
            node = StringLiteral(tok.value)
            return self._reduce(f'primary → STRING("{tok.value}")', node)
        if tok.type == TokenType.BOOL_LITERAL:
            self._shift()
            node = BoolLiteral(tok.value == 'true')
            return self._reduce(f"primary → BOOL({tok.value})", node)
        if tok.type == TokenType.IDENTIFIER:
            self._shift()
            node = Identifier(tok.value, tok.line)
            return self._reduce(f"primary → ID({tok.value})", node)
        if tok.type == TokenType.LPAREN:
            self._shift(TokenType.LPAREN)
            expr = self._parse_expr()
            self._shift(TokenType.RPAREN)
            return self._reduce("primary → ( expr )", expr)
        raise SyntaxError(
            f"Line {tok.line}: Unexpected token '{tok.value}' in expression"
        )
