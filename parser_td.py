"""
Phase 2 (Top-Down) – Recursive Descent Parser (LL parsing).

Strategy: start from the grammar's start symbol (program) and expand each
non-terminal top-down until terminals match the input.  Each grammar rule
maps directly to one method in this class.

Grammar summary
───────────────
program    → stmt_list EOF
stmt_list  → stmt*
stmt       → decl_stmt | assign_stmt | if_stmt | while_stmt | print_stmt | block
decl_stmt  → type ID ['=' expr] ';'
assign_stmt→ ID '=' expr ';'
if_stmt    → 'if' '(' expr ')' block ['else' block]
while_stmt → 'while' '(' expr ')' block
print_stmt → 'print' '(' expr ')' ';'
block      → '{' stmt_list '}'
expr       → or_expr
or_expr    → and_expr ('||' and_expr)*
and_expr   → eq_expr  ('&&' eq_expr)*
eq_expr    → rel_expr (('=='|'!=') rel_expr)*
rel_expr   → add_expr (('<'|'>'|'<='|'>=') add_expr)*
add_expr   → mul_expr (('+'|'-') mul_expr)*
mul_expr   → unary   (('*'|'/'|'%') unary)*
unary      → ('!'|'-') unary | primary
primary    → NUMBER | STRING | BOOL | ID | '(' expr ')'
"""

from tokens import Token, TokenType
from ast_nodes import *
from typing import List, Optional, Tuple


class TopDownParser:
    """Recursive-Descent (Top-Down / LL) Parser."""

    def __init__(self, tokens: List[Token]) -> None:
        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        eof_tok = next((t for t in tokens if t.type == TokenType.EOF),
                       Token(TokenType.EOF, 'EOF', 0, 0))
        self.tokens:  List[Token] = non_eof + [eof_tok]
        self.pos:     int         = 0
        self.errors:  List[str]   = []
        self.steps:   List[str]   = []

    # ─────────────────────────────────────────────────── token utilities ──────

    def _cur(self) -> Token:
        return self.tokens[self.pos]

    def _match(self, *types: TokenType) -> bool:
        return self._cur().type in types

    def _consume(self, expected: TokenType = None) -> Token:
        tok = self._cur()
        if expected and tok.type != expected:
            raise SyntaxError(
                f"Line {tok.line}: Expected {expected.name}, "
                f"got {tok.type.name} ('{tok.value}')"
            )
        self.pos += 1
        return tok

    def _log(self, msg: str) -> None:
        self.steps.append(msg)

    # ─────────────────────────────────────────────────── public interface ─────

    def parse(self) -> Tuple[Optional[Program], List[str], List[str]]:
        self._log("╔══════════════════════════════════════════════════╗")
        self._log("║   TOP-DOWN  ·  Recursive Descent Parser (LL)    ║")
        self._log("╚══════════════════════════════════════════════════╝")
        self._log("")
        self._log("Grammar rules applied (predict → expand):")
        self._log("")
        try:
            prog = self._parse_program()
            return prog, self.errors, self.steps
        except SyntaxError as exc:
            self.errors.append(str(exc))
            return None, self.errors, self.steps

    # ─────────────────────────────────────────────────── grammar rules ───────

    def _parse_program(self) -> Program:
        self._log("► program → stmt_list EOF")
        stmts = self._parse_stmt_list()
        self._consume(TokenType.EOF)
        return Program(stmts)

    def _parse_stmt_list(self) -> List[ASTNode]:
        stmts: List[ASTNode] = []
        while not self._match(TokenType.EOF, TokenType.RBRACE):
            try:
                stmt = self._parse_stmt()
                if stmt:
                    stmts.append(stmt)
            except SyntaxError as exc:
                self.errors.append(str(exc))
                # panic-mode recovery: skip to next ';' or block boundary
                while not self._match(TokenType.SEMICOLON, TokenType.RBRACE,
                                       TokenType.LBRACE, TokenType.EOF):
                    self.pos += 1
                if self._match(TokenType.SEMICOLON):
                    self.pos += 1
        return stmts

    def _parse_stmt(self) -> Optional[ASTNode]:
        tok = self._cur()
        if self._match(TokenType.KW_INT, TokenType.KW_FLOAT,
                       TokenType.KW_STRING, TokenType.KW_BOOL):
            self._log(f"  stmt → decl_stmt  [{tok.value} at line {tok.line}]")
            return self._parse_decl_stmt()
        if self._match(TokenType.KW_IF):
            self._log(f"  stmt → if_stmt  [line {tok.line}]")
            return self._parse_if_stmt()
        if self._match(TokenType.KW_WHILE):
            self._log(f"  stmt → while_stmt  [line {tok.line}]")
            return self._parse_while_stmt()
        if self._match(TokenType.KW_PRINT):
            self._log(f"  stmt → print_stmt  [line {tok.line}]")
            return self._parse_print_stmt()
        if self._match(TokenType.IDENTIFIER):
            self._log(f"  stmt → assign_stmt  ['{tok.value}' at line {tok.line}]")
            return self._parse_assign_stmt()
        if self._match(TokenType.LBRACE):
            self._log(f"  stmt → block  [line {tok.line}]")
            return self._parse_block()
        raise SyntaxError(f"Line {tok.line}: Unexpected token '{tok.value}'")

    def _parse_decl_stmt(self) -> DeclStmt:
        type_tok = self._consume()
        name_tok = self._consume(TokenType.IDENTIFIER)
        init = None
        if self._match(TokenType.ASSIGN):
            self._consume(TokenType.ASSIGN)
            init = self._parse_expr()
        self._consume(TokenType.SEMICOLON)
        self._log(f"    ✓ decl_stmt → {type_tok.value} {name_tok.value}"
                  f" {'= <expr>' if init else ''} ;")
        return DeclStmt(type_tok.value, name_tok.value, init, type_tok.line)

    def _parse_assign_stmt(self) -> AssignStmt:
        name_tok = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.ASSIGN)
        value = self._parse_expr()
        self._consume(TokenType.SEMICOLON)
        self._log(f"    ✓ assign_stmt → {name_tok.value} = <expr> ;")
        return AssignStmt(name_tok.value, value, name_tok.line)

    def _parse_if_stmt(self) -> IfStmt:
        tok = self._consume(TokenType.KW_IF)
        self._consume(TokenType.LPAREN)
        cond = self._parse_expr()
        self._consume(TokenType.RPAREN)
        then_blk = self._parse_block()
        else_blk = None
        if self._match(TokenType.KW_ELSE):
            self._consume(TokenType.KW_ELSE)
            else_blk = self._parse_block()
        self._log(f"    ✓ if_stmt → if ( <expr> ) block"
                  f"{' else block' if else_blk else ''}")
        return IfStmt(cond, then_blk, else_blk, tok.line)

    def _parse_while_stmt(self) -> WhileStmt:
        tok = self._consume(TokenType.KW_WHILE)
        self._consume(TokenType.LPAREN)
        cond = self._parse_expr()
        self._consume(TokenType.RPAREN)
        body = self._parse_block()
        self._log("    ✓ while_stmt → while ( <expr> ) block")
        return WhileStmt(cond, body, tok.line)

    def _parse_print_stmt(self) -> PrintStmt:
        tok = self._consume(TokenType.KW_PRINT)
        self._consume(TokenType.LPAREN)
        val = self._parse_expr()
        self._consume(TokenType.RPAREN)
        self._consume(TokenType.SEMICOLON)
        self._log("    ✓ print_stmt → print ( <expr> ) ;")
        return PrintStmt(val, tok.line)

    def _parse_block(self) -> Block:
        self._consume(TokenType.LBRACE)
        stmts = self._parse_stmt_list()
        self._consume(TokenType.RBRACE)
        self._log("    ✓ block → { stmt_list }")
        return Block(stmts)

    # ─────────────────────────────────────────── expression sub-rules ────────

    def _parse_expr(self) -> ASTNode:
        return self._parse_or()

    def _parse_or(self) -> ASTNode:
        left = self._parse_and()
        while self._match(TokenType.OR):
            op = self._consume().value
            right = self._parse_and()
            left = BinaryExpr(left, op, right)
            self._log("    ✓ or_expr → expr || expr")
        return left

    def _parse_and(self) -> ASTNode:
        left = self._parse_eq()
        while self._match(TokenType.AND):
            op = self._consume().value
            right = self._parse_eq()
            left = BinaryExpr(left, op, right)
            self._log("    ✓ and_expr → expr && expr")
        return left

    def _parse_eq(self) -> ASTNode:
        left = self._parse_rel()
        while self._match(TokenType.EQ, TokenType.NEQ):
            op = self._consume().value
            right = self._parse_rel()
            left = BinaryExpr(left, op, right)
            self._log(f"    ✓ eq_expr → expr {op} expr")
        return left

    def _parse_rel(self) -> ASTNode:
        left = self._parse_add()
        while self._match(TokenType.LT, TokenType.GT,
                          TokenType.LTE, TokenType.GTE):
            op = self._consume().value
            right = self._parse_add()
            left = BinaryExpr(left, op, right)
            self._log(f"    ✓ rel_expr → expr {op} expr")
        return left

    def _parse_add(self) -> ASTNode:
        left = self._parse_mul()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self._consume().value
            right = self._parse_mul()
            left = BinaryExpr(left, op, right)
            self._log(f"    ✓ add_expr → expr {op} expr")
        return left

    def _parse_mul(self) -> ASTNode:
        left = self._parse_unary()
        while self._match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self._consume().value
            right = self._parse_unary()
            left = BinaryExpr(left, op, right)
            self._log(f"    ✓ mul_expr → expr {op} expr")
        return left

    def _parse_unary(self) -> ASTNode:
        if self._match(TokenType.NOT, TokenType.MINUS):
            op = self._consume().value
            operand = self._parse_unary()
            self._log(f"    ✓ unary → {op} unary")
            return UnaryExpr(op, operand)
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._cur()
        if tok.type == TokenType.INT_LITERAL:
            self._consume()
            self._log(f"    ✓ primary → INT_LITERAL({tok.value})")
            return NumberLiteral(int(tok.value), True)
        if tok.type == TokenType.FLOAT_LITERAL:
            self._consume()
            self._log(f"    ✓ primary → FLOAT_LITERAL({tok.value})")
            return NumberLiteral(float(tok.value), False)
        if tok.type == TokenType.STRING_LITERAL:
            self._consume()
            self._log(f'    ✓ primary → STRING_LITERAL("{tok.value}")')
            return StringLiteral(tok.value)
        if tok.type == TokenType.BOOL_LITERAL:
            self._consume()
            self._log(f"    ✓ primary → BOOL_LITERAL({tok.value})")
            return BoolLiteral(tok.value == 'true')
        if tok.type == TokenType.IDENTIFIER:
            self._consume()
            self._log(f"    ✓ primary → IDENTIFIER({tok.value})")
            return Identifier(tok.value, tok.line)
        if tok.type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            expr = self._parse_expr()
            self._consume(TokenType.RPAREN)
            self._log("    ✓ primary → ( expr )")
            return expr
        raise SyntaxError(
            f"Line {tok.line}: Unexpected token '{tok.value}' in expression"
        )
