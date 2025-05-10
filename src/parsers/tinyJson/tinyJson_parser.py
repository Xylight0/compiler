from parsers.common import *

type Json = str | int | dict[str, Json]

#! I added comments throughout the code to explain my thought process and understanding.

def ruleJson(toks: TokenStream) -> Json:
    """
    Parses a JSON stream:
    json: object | string | int;
    """
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt]) #Handles trying each parser function


def ruleObject(toks: TokenStream) -> dict[str, Json]:
    """
    Parses a JSON object:
    object:"{", entryList, "}";
    """
    toks.ensureNext("LBRACE") # Expect "{"
    entries = ruleEntryList(toks) #  # Parse the list of entries
    toks.ensureNext("RBRACE") # Expect "}"
    return entries


def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    """
    Parses a list of entries:
    entryList: entryListEMpty | entryListNotEmpty;
    """
    nextTokenType = toks.lookahead().type # check the type of the next token but not consuming it

    if nextTokenType == "STRING":
        return ruleEntryListNotEmpty(toks) #  Parse the non-empty list
    else:
        return {} # Consume nothing and return an empty dict


def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    """
    Parses a non-empty list of entries:
    entryListNotEmpty: entry | entry, ",", entryListNotEmpty;
    """
    first_key, first_value = ruleEntry(toks) # Parse first entry 
    entries: dict[str, Json] = {first_key: first_value}  # Initialize the dictionary with the first entry

    # loop while the next token is a COMMA, indicating more entries
    while toks.lookahead().type == "COMMA":
        toks.ensureNext("COMMA") # Consume
        nextKey, nextValue = ruleEntry(toks) # Parse next entry
        entries[nextKey] = nextValue # Add parsed entry to the dictonary
        
    return entries


def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    """
    Parses a single key-value entry:
    entry: string, ":", json;
    """
    key = ruleString(toks) #Pparse the string key
    toks.ensureNext("COLON") # Consume ceperator 
    value = ruleJson(toks) # Rrecursively parse 
    return (key, value)


def ruleString(toks: TokenStream) -> str:
    """
    Parses a JSON string value
    """
    token = toks.ensureNext("STRING") # Consume type
    val = token.value # Get value
    return val[1:-1] # Remove qutoes 


def ruleInt(toks: TokenStream) -> int:
    """
    Parses a JSON integer value
    """
    token = toks.ensureNext("INT") # Consume type
    return int(token.value) # Convert to int


def parse(code: str) -> Json:
    """
    parse a tinyJson string
    """
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')

    toks = TokenStream(tokens) # Create Token Stream
    res = ruleJson(toks) # Start parsing
    toks.ensureEof(code) # Ensure all tokens used

    return res