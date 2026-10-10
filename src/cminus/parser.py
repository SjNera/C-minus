from lexer import (
    Lexer, Position, InvalidSyntaxError,
    TT_INT, TT_FLOAT, TT_STRING, TT_BOOL,
    TT_IDENTIFIER, TT_KEYWORD,
    TT_PLUS, TT_MINUS, TT_MUL, TT_DIV, TT_MOD,
    TT_LT, TT_LTE, TT_GT, TT_GTE, TT_EQ, TT_NEQ,
    TT_AND, TT_OR, TT_NOT,
    TT_ASSIGN, TT_LPAREN, TT_RPAREN, TT_LBRACE, TT_RBRACE,
    TT_SEMICOLON, TT_EOF,
)


# ABSTRACT SYNTAX TREE NODES 
class ASTNode:
    pass


class ProgramNode(ASTNode):
    def __init__(self, statements):
        self.statements = statements


class VariableDeclarationNode(ASTNode):
    def __init__(self, type_token, name_token, value_node):
        self.type_token = type_token
        self.name_token = name_token
        self.value_node = value_node


class AssignmentNode(ASTNode):
    def __init__(self, name_token, value_node):
        self.name_token = name_token
        self.value_node = value_node


class BinaryOperationNode(ASTNode):
    def __init__(self, left_node, operator_token, right_node):
        self.left_node = left_node
        self.operator_token = operator_token
        self.right_node = right_node


class UnaryOperationNode(ASTNode):
    def __init__(self, operator_token, child_node):
        self.operator_token = operator_token
        self.child_node = child_node


class LiteralNode(ASTNode):
    def __init__(self, token):
        self.token = token
        self.value = token.value


class VariableAccessNode(ASTNode):
    def __init__(self, token):
        self.token = token
        self.name = token.value


class BlockNode(ASTNode):
    def __init__(self, statements):
        self.statements = statements


class IfNode(ASTNode):
    def __init__(self, condition, body, else_body=None):
        self.condition = condition
        self.body = body
        self.else_body = else_body


class WhileNode(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body


class DoWhileNode(ASTNode):
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition


class ForNode(ASTNode):
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body


class ReturnNode(ASTNode):
    def __init__(self, value_node=None):
        self.value_node = value_node


class BreakNode(ASTNode):
    pass


class ContinueNode(ASTNode):
    pass


# PARSER 
TYPE_KEYWORDS = ('int', 'float', 'bool', 'string')


class Parser:
    def __init__(self, tokens, fn='<stdin>'):
        self.tokens = tokens
        self.fn = fn
        self.token_index = -1
        self.current_token = None
        self.advance()

    def advance(self):
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        return self.current_token

    def peek(self, offset=1):
        index = self.token_index + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return None

    def make_error(self, details):
        token = self.current_token
        position = Position(0, token.line - 1, token.column - 1, self.fn, "")
        return InvalidSyntaxError(position, position, details)

    def describe_current(self):
        token = self.current_token
        if token.type == TT_KEYWORD:
            return f"keyword '{token.value}'"
        return f"'{token.type}'"

    def expect(self, token_type, value=None):
        if self.current_token.type == token_type and (value is None or self.current_token.value == value):
            token = self.current_token
            self.advance()
            return token, None

        expected_string = f"'{value}'" if value else f"'{token_type}'"
        return None, self.make_error(f"Expected {expected_string}, got {self.describe_current()}")

    # PARSE PROGRAM 
    def parse(self):
        statements = []
        while self.current_token.type != TT_EOF:
            statement, error = self.parse_statement()
            if error:
                return None, error
            statements.append(statement)
        return ProgramNode(statements), None

    # STATEMENTS 
    def parse_statement(self):
        # Block Statement
        if self.current_token.type == TT_LBRACE:
            return self.parse_block()

        # Variable Declaration: int x = 5;
        if self.current_token.type == TT_KEYWORD and self.current_token.value in TYPE_KEYWORDS:
            return self.parse_variable_declaration()

        # If Statement
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'if':
            return self.parse_if()

        # While Loop
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'while':
            return self.parse_while()

        # Do-While Loop
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'do':
            return self.parse_do_while()

        # For Loop
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'for':
            return self.parse_for()

        # Return Statement
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'return':
            return self.parse_return()

        # Break Statement
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'break':
            self.advance()
            _, error = self.expect(TT_SEMICOLON)
            if error:
                return None, error
            return BreakNode(), None

        # Continue Statement
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'continue':
            self.advance()
            _, error = self.expect(TT_SEMICOLON)
            if error:
                return None, error
            return ContinueNode(), None

        # Variable Assignment
        if self.current_token.type == TT_IDENTIFIER and self.peek() and self.peek().type == TT_ASSIGN:
            return self.parse_assignment()

        # Fallback: Expression Statement
        expression, error = self.parse_expression()
        if error:
            return None, error
        _, error = self.expect(TT_SEMICOLON)
        if error:
            return None, error
        return expression, None

    def parse_block(self):
        self.advance()  # consume '{'
        statements = []
        while self.current_token.type != TT_RBRACE and self.current_token.type != TT_EOF:
            statement, error = self.parse_statement()
            if error:
                return None, error
            statements.append(statement)

        _, error = self.expect(TT_RBRACE)
        if error:
            return None, error
        return BlockNode(statements), None

    def parse_variable_declaration(self):
        type_token = self.current_token
        self.advance()

        name_token, error = self.expect(TT_IDENTIFIER)
        if error:
            return None, error

        value_node = None
        if self.current_token.type == TT_ASSIGN:
            self.advance()
            value_node, error = self.parse_expression()
            if error:
                return None, error

        _, error = self.expect(TT_SEMICOLON)
        if error:
            return None, error

        return VariableDeclarationNode(type_token, name_token, value_node), None

    def parse_assignment(self, expect_semicolon=True):
        name_token = self.current_token
        self.advance()  
        self.advance()  

        value_node, error = self.parse_expression()
        if error:
            return None, error

        if expect_semicolon:
            _, error = self.expect(TT_SEMICOLON)
            if error:
                return None, error

        return AssignmentNode(name_token, value_node), None

    def parse_if(self):
        self.advance()  
        _, error = self.expect(TT_LPAREN)
        if error:
            return None, error

        condition, error = self.parse_expression()
        if error:
            return None, error

        _, error = self.expect(TT_RPAREN)
        if error:
            return None, error

        body, error = self.parse_statement()
        if error:
            return None, error

        else_body = None
        if self.current_token.type == TT_KEYWORD and self.current_token.value == 'else':
            self.advance()
            else_body, error = self.parse_statement()
            if error:
                return None, error

        return IfNode(condition, body, else_body), None

    def parse_while(self):
        self.advance()  
        _, error = self.expect(TT_LPAREN)
        if error:
            return None, error

        condition, error = self.parse_expression()
        if error:
            return None, error

        _, error = self.expect(TT_RPAREN)
        if error:
            return None, error

        body, error = self.parse_statement()
        if error:
            return None, error

        return WhileNode(condition, body), None

    def parse_do_while(self):
        self.advance()  

        body, error = self.parse_statement()
        if error:
            return None, error

        _, error = self.expect(TT_KEYWORD, 'while')
        if error:
            return None, error

        _, error = self.expect(TT_LPAREN)
        if error:
            return None, error

        condition, error = self.parse_expression()
        if error:
            return None, error

        _, error = self.expect(TT_RPAREN)
        if error:
            return None, error

        _, error = self.expect(TT_SEMICOLON)
        if error:
            return None, error

        return DoWhileNode(body, condition), None

    def parse_for(self):
        self.advance()  
        _, error = self.expect(TT_LPAREN)
        if error:
            return None, error

        #  init (each form below consumes its own ;) 
        init = None
        if self.current_token.type == TT_SEMICOLON:
            self.advance()
        elif self.current_token.type == TT_KEYWORD and self.current_token.value in TYPE_KEYWORDS:
            init, error = self.parse_variable_declaration()
        elif self.current_token.type == TT_IDENTIFIER and self.peek() and self.peek().type == TT_ASSIGN:
            init, error = self.parse_assignment()
        else:
            init, error = self.parse_expression()
            if not error:
                _, error = self.expect(TT_SEMICOLON)
        if error:
            return None, error

        #  condition 
        condition = None
        if self.current_token.type != TT_SEMICOLON:
            condition, error = self.parse_expression()
            if error:
                return None, error
        _, error = self.expect(TT_SEMICOLON)
        if error:
            return None, error

        # update (no trailing ';')
        update = None
        if self.current_token.type != TT_RPAREN:
            if self.current_token.type == TT_IDENTIFIER and self.peek() and self.peek().type == TT_ASSIGN:
                update, error = self.parse_assignment(expect_semicolon=False)
            else:
                update, error = self.parse_expression()
            if error:
                return None, error

        _, error = self.expect(TT_RPAREN)
        if error:
            return None, error

        body, error = self.parse_statement()
        if error:
            return None, error

        return ForNode(init, condition, update, body), None

    def parse_return(self):
        self.advance()  # consume 'return'

        if self.current_token.type == TT_SEMICOLON:
            self.advance()
            return ReturnNode(None), None

        expression, error = self.parse_expression()
        if error:
            return None, error

        _, error = self.expect(TT_SEMICOLON)
        if error:
            return None, error

        return ReturnNode(expression), None

    # EXPRESSION PARSING (Precedence Hierarchy) 

    def parse_expression(self):
        return self.parse_logical_or()

    def parse_logical_or(self):
        return self._parse_binary_operation(self.parse_logical_and, (TT_OR,))

    def parse_logical_and(self):
        return self._parse_binary_operation(self.parse_equality, (TT_AND,))

    def parse_equality(self):
        return self._parse_binary_operation(self.parse_relational, (TT_EQ, TT_NEQ))

    def parse_relational(self):
        return self._parse_binary_operation(
            self.parse_additive,
            (TT_LT, TT_LTE, TT_GT, TT_GTE),
        )

    def parse_additive(self):
        return self._parse_binary_operation(
            self.parse_multiplicative,
            (TT_PLUS, TT_MINUS),
        )

    def parse_multiplicative(self):
        return self._parse_binary_operation(
            self.parse_unary,
            (TT_MUL, TT_DIV, TT_MOD),
        )

    def parse_unary(self):
        if self.current_token.type in (TT_PLUS, TT_MINUS, TT_NOT):
            operator_token = self.current_token
            self.advance()
            node, error = self.parse_unary()
            if error:
                return None, error
            return UnaryOperationNode(operator_token, node), None

        return self.parse_primary()

    def parse_primary(self):
        token = self.current_token

        # Literals
        if token.type in (TT_INT, TT_FLOAT, TT_STRING, TT_BOOL):
            self.advance()
            return LiteralNode(token), None

        # Identifiers
        if token.type == TT_IDENTIFIER:
            self.advance()
            return VariableAccessNode(token), None

        # Parenthesised Expressions
        if token.type == TT_LPAREN:
            self.advance()
            expression, error = self.parse_expression()
            if error:
                return None, error
            _, error = self.expect(TT_RPAREN)
            if error:
                return None, error
            return expression, None

        return None, self.make_error(f"Unexpected {self.describe_current()}")

    def _parse_binary_operation(self, parse_function, operators):
        left, error = parse_function()
        if error:
            return None, error

        while self.current_token.type in operators:
            operator_token = self.current_token
            self.advance()
            right, error = parse_function()
            if error:
                return None, error
            left = BinaryOperationNode(left, operator_token, right)

        return left, None


#  RUN 
def run(fn, text):
    tokens, error = Lexer(fn, text).make_tokens()
    if error:
        return None, error
    return Parser(tokens, fn).parse()