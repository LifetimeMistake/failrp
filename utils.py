def parse_arguments(s):
    # Split the input string into tokens
    tokens = []
    current_token = ''
    in_quote = False
    for c in s:
        if c == ' ' and not in_quote:
            if current_token:
                tokens.append(current_token)
                current_token = ''
        elif c == '"':
            in_quote = not in_quote
        else:
            current_token += c
    if current_token:
        tokens.append(current_token)
    # Remove quotes from the tokens
    args = []
    for token in tokens:
        if token.startswith('"') and token.endswith('"'):
            args.append(token[1:-1])
        else:
            args.append(token)
    if "TO" in args:
        args.pop(args.index("TO"))
    return args

