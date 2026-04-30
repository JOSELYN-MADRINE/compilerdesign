"""AST node definitions used by both parsers and the semantic analyser."""

from dataclasses import dataclass, field
from typing import List, Optional


class ASTNode:
    """Base class for every node in the Abstract Syntax Tree."""


# ═══════════════════════════════════════════════════════════════ statements ═══

@dataclass
class Program(ASTNode):
    statements: List[ASTNode]


@dataclass
class Block(ASTNode):
    statements: List[ASTNode]


@dataclass
class DeclStmt(ASTNode):
    """Type declaration: int x = 5;"""
    var_type:    str
    name:        str
    initializer: Optional[ASTNode]
    line:        int


@dataclass
class AssignStmt(ASTNode):
    """Assignment: x = expr;"""
    name:  str
    value: ASTNode
    line:  int


@dataclass
class IfStmt(ASTNode):
    condition:  ASTNode
    then_block: Block
    else_block: Optional[Block]
    line:       int


@dataclass
class WhileStmt(ASTNode):
    condition: ASTNode
    body:      Block
    line:      int


@dataclass
class PrintStmt(ASTNode):
    value: ASTNode
    line:  int


# ═══════════════════════════════════════════════════════════════ expressions ══

@dataclass
class BinaryExpr(ASTNode):
    left:  ASTNode
    op:    str
    right: ASTNode


@dataclass
class UnaryExpr(ASTNode):
    op:      str
    operand: ASTNode


@dataclass
class NumberLiteral(ASTNode):
    value:  float
    is_int: bool


@dataclass
class StringLiteral(ASTNode):
    value: str


@dataclass
class BoolLiteral(ASTNode):
    value: bool


@dataclass
class Identifier(ASTNode):
    name: str
    line: int
