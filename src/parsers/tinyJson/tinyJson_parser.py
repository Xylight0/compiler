from parsers.common import *


type Json = str | int | dict[str, Json]


def ruleJson(toks: TokenStream) -> Json:
    """
    Parses a JSON stream:
    json: object | string | int;
    """
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt]) #handles trying each parser function


def ruleObject(toks: TokenStream) -> dict[str, Json]:
    """
    Parses a JSON object:
    object:"{", entryList, "}";
    """
    toks.ensureNext("LBRACE") # expect "{"
    entries = ruleEntryList(toks) #  # Parse the list of entries
    toks.ensureNext("RBRACE") # expect "}"
    return entries


def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    """
    Parses a list of entries:
    entryList: entryListEMpty | entryListNotEmpty;
    """
    nextTokenType = toks.lookahead().type # check the type of the next token but not consuming it

    if nextTokenType == "STRING":
        return ruleEntryListNotEmpty(toks) #  parse the non-empty list
    else:
        return {} # consume nothing and return an empty dict


def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    """
    Parses a non-empty list of entries:
    entryListNotEmpty: entry | entry, ",", entryListNotEmpty;
    """
    first_key, first_value = ruleEntry(toks) # parse first entry 
    entries: dict[str, Json] = {first_key: first_value}  # initialize the dictionary with the first entry

    # loop while the next token is a COMMA, indicating more entries
    while toks.lookahead().type == "COMMA":
        toks.ensureNext("COMMA") # consume
        nextKey, nextValue = ruleEntry(toks) # parse next entry
        entries[nextKey] = nextValue # add parsed entry to the dictonary
        
    return entries


def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    """
    Parses a single key-value entry:
    entry: string, ":", json;
    """
    key = ruleString(toks) # Parse the string key
    toks.ensureNext("COLON") # consume ceperator 
    value = ruleJson(toks) # recursively parse 
    return (key, value)


def ruleString(toks: TokenStream) -> str:
    """
    Parses a JSON string value
    """
    token = toks.ensureNext("STRING") # consume type
    val = token.value # get value
    return val[1:-1] # remove qutoes 


def ruleInt(toks: TokenStream) -> int:
    """
    Parses a JSON integer value
    """
    token = toks.ensureNext("INT") # consume type
    return int(token.value) # convert to int


def parse(code: str) -> Json:
    """
    parse a tinyJson string
    """
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')

    toks = TokenStream(tokens) # create Token Stream
    res = ruleJson(toks) # start parsing
    toks.ensureEof(code) # ensure all tokens used

    return res