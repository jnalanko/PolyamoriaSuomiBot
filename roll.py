def to_positive_integer(string, upto):
    if not string.isdigit():
        raise ValueError("Syntaksivirhe: " + string)
    if int(string) <= 0:
        raise ValueError("Virhe: Ei-positiivinen numero: " + string)
    if int(string) > upto:
        raise ValueError("Virhe: Liian iso numero: " + string)
    return int(string)

# Returns the result as a string
def do_roll(expression):
    rolls = []
    sum_of_constants = 0

    expression = expression.replace("+", " + ").replace("-", " - ")

    sign = 1 # +1 or -1

    try: 
        tokens = expression.split()
        if len(tokens) == 0:
            return "Anna heitto muodossa 2d6 + 5"
        if len(tokens) > 20:
            return "Liian monta operaatiota"
        for i, token in enumerate(tokens):
            token = token.strip()
            if i % 2 == 1:
                if token == '+': sign = 1
                elif token == '-': sign = -1
                else: raise ValueError("Syntaksivirhe: " + token)
            else:
                if token.count("d") == 0:
                    # Constant
                    sum_of_constants += int(to_positive_integer(token, 1e6)) * sign
                elif token.count("d") == 1:
                    # Dice
                    n_dice, n_sides = token.split('d')
                    if n_dice == "": n_dice = "1" # Implicit 1
                    n_dice = to_positive_integer(n_dice, 100)
                    n_sides = to_positive_integer(n_sides, 1e6)
                    while n_dice > 0:
                        rolls.append(random.randint(1,n_sides) * sign)
                        n_dice -= 1
                else:
                    raise ValueError("Syntaksivirhe: " + token)
    except ValueError as e: return str(e)

    if sum_of_constants != 0: 
        message = "{} + {} = {}".format(rolls, sum_of_constants, sum(rolls) + sum_of_constants)
    else:
        message = "{} = {}".format(rolls, sum(rolls))
    if len(message) > 1000: return "Liian monta heittoa"
    else: return message
