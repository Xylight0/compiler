from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt])

def ruleObject(toks: TokenStream) -> dict[str, Json]:
    return {} # TODO

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    return {} # TODO

def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    return {} # TODO

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    return ("", {}) # TODO

def ruleString(toks: TokenStream) -> str:
    return "" # TODO

def ruleInt(toks: TokenStream) -> int:
    return 0 # TODO

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res
