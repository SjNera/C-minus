import string

# DEFINE
DIGITS = '0123456789'
KEYWORDS = {'int', 'float', 'bool', 'string', 'if', 'else', 'while', 'do', 'for', 'break', 'continue', 'return'}
LETTERS = string.ascii_letters + '_'
LETTERS_DIGITS = LETTERS + DIGITS


# ERRORS
class Error:
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self):
        result = f'{self.error_name}: {self.details}\n'
        result += f'File {self.pos_start.fn}, line {self.pos_start.ln + 1}'
        return result


class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character', details)


class UnterminatedStringError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Unterminated String', details)


class UnterminatedCommentError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Unterminated Comment', details)


class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Invalid Syntax', details)


# POSITION
class Position:
    def __init__(self, idx, ln, col, fn, ftxt):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.fn = fn
        self.ftxt = ftxt

    def advance(self, current_char):
        self.idx += 1
        self.col += 1

        if current_char == '\n':
            self.ln += 1
            self.col = 0

        return self

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.ftxt)


# TOKENS
# Literals
TT_INT = 'INT'            # 12
TT_FLOAT = 'FLOAT'        # 3.5
TT_STRING = 'STRING'      # "Hello"
TT_BOOL = 'BOOL'          # true / false

# Identifiers and Keywords
TT_IDENTIFIER = 'IDENTIFIER'  # age, _Age
TT_KEYWORD = 'KEYWORD'        # if, else, return

# Arithmetic Operators
TT_PLUS = 'PLUS'          # +
TT_MINUS = 'MINUS'        # -
TT_MUL = 'MUL'            # *
TT_DIV = 'DIV'            # /
TT_MOD = 'MOD'            # %

# Relational Operators
TT_LT = 'LT'              # <
TT_LTE = 'LTE'            # <=
TT_GT = 'GT'              # >
TT_GTE = 'GTE'            # >=

# Equality Operators
TT_EQ = 'EQ'              # ==
TT_NEQ = 'NEQ'            # !=

# Logical Operators
TT_AND = 'AND'            # &&
TT_OR = 'OR'              # ||
TT_NOT = 'NOT'            # !

# Assignment
TT_ASSIGN = 'ASSIGN'      # =

# Symbols
TT_LPAREN = 'LPAREN'      # (
TT_RPAREN = 'RPAREN'      # )
TT_LBRACE = 'LBRACE'      # {
TT_RBRACE = 'RBRACE'      # }
TT_COMMA = 'COMMA'        # ,
TT_SEMICOLON = 'SEMICOLON'  # ;

# End of input
TT_EOF = 'EOF'


class Token:
    def __init__(self, type_, value=None, line=None, column=None):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        if self.value is not None:
            return f'{self.type}:{self.value} ({self.line}:{self.column})'
        return f'{self.type} ({self.line}:{self.column})'


# LEXER
class Lexer:
    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.pos = Position(-1, 0, -1, fn, text)
        self.current_char = None
        self.advance()

    def advance(self):
        self.pos.advance(self.current_char)

        self.current_char = (
            self.text[self.pos.idx]
            if self.pos.idx < len(self.text)
            else None
        )

    def make_tokens(self):
        tokens = []

        while self.current_char is not None:

            # WHITESPACE (including newlines)
            if self.current_char in ' \t\r\n':
                self.advance()

            # NUMBERS
            elif self.current_char in DIGITS:
                tokens.append(self.make_number())

            # IDENTIFIERS / KEYWORDS
            elif self.current_char in LETTERS:
                tokens.append(self.make_identifier())

            # STRING
            elif self.current_char == '"':
                token, error = self.make_string()

                if error:
                    return [], error
                tokens.append(token)

            # PLUS
            elif self.current_char == '+':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_PLUS, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # MINUS
            elif self.current_char == '-':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_MINUS, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # MULTIPLICATION
            elif self.current_char == '*':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_MUL, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # DIVISION OR COMMENTS
            elif self.current_char == '/':
                pos_start = self.pos.copy()

                if self.peek() == '/':
                    self.skip_single_line_comment()
                elif self.peek() == '*':
                    error = self.skip_block_comment()
                    if error:
                        return [], error
                else:
                    tokens.append(Token(TT_DIV, None, pos_start.ln + 1, pos_start.col + 1))
                    self.advance()

            # MODULO
            elif self.current_char == '%':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_MOD, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # LESS THAN / LESS THAN OR EQUAL
            elif self.current_char == '<':
                pos_start = self.pos.copy()
                self.advance()

                if self.current_char == '=':
                    self.advance()
                    tokens.append(Token(TT_LTE, None, pos_start.ln + 1, pos_start.col + 1))
                else:
                    tokens.append(Token(TT_LT, None, pos_start.ln + 1, pos_start.col + 1))

            # GREATER THAN / GREATER THAN OR EQUAL
            elif self.current_char == '>':
                pos_start = self.pos.copy()
                self.advance()

                if self.current_char == '=':
                    self.advance()
                    tokens.append(Token(TT_GTE, None, pos_start.ln + 1, pos_start.col + 1))
                else:
                    tokens.append(Token(TT_GT, None, pos_start.ln + 1, pos_start.col + 1))

            # EQUAL / EQUALITY
            elif self.current_char == '=':
                pos_start = self.pos.copy()
                self.advance()

                if self.current_char == '=':
                    self.advance()
                    tokens.append(Token(TT_EQ, None, pos_start.ln + 1, pos_start.col + 1))
                else:
                    tokens.append(Token(TT_ASSIGN, None, pos_start.ln + 1, pos_start.col + 1))

            # NOT / NOT EQUAL
            elif self.current_char == '!':
                pos_start = self.pos.copy()
                self.advance()

                if self.current_char == '=':
                    self.advance()
                    tokens.append(Token(TT_NEQ, None, pos_start.ln + 1, pos_start.col + 1))
                else:
                    tokens.append(Token(TT_NOT, None, pos_start.ln + 1, pos_start.col + 1))

            # LOGICAL AND
            elif self.current_char == '&':
                pos_start = self.pos.copy()
                self.advance()

                if self.current_char == '&':
                    self.advance()
                    tokens.append(Token(TT_AND, None, pos_start.ln + 1, pos_start.col + 1))
                else:
                    return [], IllegalCharError(pos_start, self.pos, "'&' expected another '&'")

            # LOGICAL OR
            elif self.current_char == '|':
                pos_start = self.pos.copy()
                self.advance()

                if self.current_char == '|':
                    self.advance()
                    tokens.append(Token(TT_OR, None, pos_start.ln + 1, pos_start.col + 1))
                else:
                    return [], IllegalCharError(pos_start, self.pos, "'|' expected another '|'")

            # LEFT PARENTHESIS
            elif self.current_char == '(':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_LPAREN, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # RIGHT PARENTHESIS
            elif self.current_char == ')':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_RPAREN, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # LEFT BRACE
            elif self.current_char == '{':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_LBRACE, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # RIGHT BRACE
            elif self.current_char == '}':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_RBRACE, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # COMMA
            elif self.current_char == ',':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_COMMA, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # SEMICOLON
            elif self.current_char == ';':
                pos_start = self.pos.copy()
                tokens.append(Token(TT_SEMICOLON, None, pos_start.ln + 1, pos_start.col + 1))
                self.advance()

            # ILLEGAL CHARACTER
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()

                return [], IllegalCharError(pos_start, self.pos, "'" + char + "'")

        # END OF FILE (the parser relies on this token)
        tokens.append(Token(TT_EOF, None, self.pos.ln + 1, self.pos.col + 1))
        return tokens, None

    def peek(self):
        if self.pos.idx + 1 < len(self.text):
            return self.text[self.pos.idx + 1]

        return None

    # COMMENTS
    def skip_single_line_comment(self):
        while self.current_char is not None and self.current_char != '\n':
            self.advance()

    def skip_block_comment(self):
        pos_start = self.pos.copy()
        self.advance()
        self.advance()

        while self.current_char is not None:
            if self.current_char == '*' and self.peek() == '/':
                self.advance()
                self.advance()
                return None
            self.advance()

        return UnterminatedCommentError(pos_start, self.pos, "expected '*/' before the end of the file")

    # STRING
    def make_string(self):
        string_value = ''
        pos_start = self.pos.copy()
        self.advance()

        while self.current_char is not None and self.current_char != '"':
            string_value += self.current_char
            self.advance()

        if self.current_char == '"':
            self.advance()
            return Token(TT_STRING, string_value, pos_start.ln + 1, pos_start.col + 1), None

        return None, UnterminatedStringError(pos_start, self.pos, "expected closing '\"'")

    # NUMBER
    def make_number(self):
        num_str = ''
        dot_count = 0

        pos_start = self.pos.copy()

        while self.current_char is not None and self.current_char in DIGITS + '.':
            if self.current_char == '.':
                if dot_count == 1:
                    break
                dot_count += 1
                num_str += '.'
            else:
                num_str += self.current_char
            self.advance()

        if dot_count == 0:
            return Token(TT_INT, int(num_str), pos_start.ln + 1, pos_start.col + 1)
        return Token(TT_FLOAT, float(num_str), pos_start.ln + 1, pos_start.col + 1)

    # IDENTIFIERS / KEYWORDS
    def make_identifier(self):
        id_str = ''
        pos_start = self.pos.copy()

        while self.current_char is not None and self.current_char in LETTERS_DIGITS:
            id_str += self.current_char
            self.advance()

        # Keywords
        if id_str in KEYWORDS:
            return Token(TT_KEYWORD, id_str, pos_start.ln + 1, pos_start.col + 1)

        # Boolean literals
        if id_str == 'true':
            return Token(TT_BOOL, True, pos_start.ln + 1, pos_start.col + 1)

        if id_str == 'false':
            return Token(TT_BOOL, False, pos_start.ln + 1, pos_start.col + 1)

        # Normal identifier
        return Token(TT_IDENTIFIER, id_str, pos_start.ln + 1, pos_start.col + 1)