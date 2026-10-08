import cminus
from cminus.ast_nodes import BinaryOp, IntLiteral


def test_package_imports():
    assert cminus.__version__


def test_ast_nodes_construct():
    node = BinaryOp("+", IntLiteral(1, line=3, column=5), IntLiteral(2))
    assert node.left.line == 3 and node.resolved_type is None
