# escrito por Marco Alfonso, 2004 Noviembre

# importamos los símbolos requeridos desde el módulo
from pyparsing import (
    Word,
    one_of,
    nums,
    Group,
    OneOrMore,
    Opt,
    pyparsing_unicode as ppu,
)

# usamos las letras en latin1, que incluye las como 'ñ', 'á', 'é', etc.
alphas = ppu.Latin1.alphas

# Aqui decimos que la gramatica "saludo" DEBE contener
# una palabra compuesta de caracteres alfanumericos
# (Word(alphas)) mas una ',' mas otra palabra alfanumerica,
# mas '!' y esos seian nuestros tokens
saludo = Word(alphas) + "," + Word(alphas) + one_of("! . ?")
tokens = saludo.parse_string("Hola, Mundo !")

# Ahora parseamos una cadena, "Hola, Mundo!",
# el metodo parseString, nos devuelve una lista con los tokens
# encontrados, en caso de no haber errores...
for i, token in enumerate(tokens):
    print(f"Token {i} -> {token}")

# imprimimos cada uno de los tokens Y listooo!!, he aquí a salida
# Token 0 -> Hola
# Token 1 -> ,
# Token 2-> Mundo
# Token 3 -> !

# ahora cambia el parseador, aceptando saludos con mas que una sola palabra antes que ','
saludo = Group(OneOrMore(Word(alphas))) + "," + Word(alphas) + one_of("! . ?")
tokens = saludo.parse_string("Hasta mañana, Mundo !")

for i, token in enumerate(tokens):
    print(f"Token {i} -> {token}")

# Ahora parseamos algunas cadenas, usando el metodo runTests
saludo.run_tests("""\
        Hola, Mundo!
        Hasta mañana, Mundo !
    """,
    fullDump=False,
)

# Por supuesto, se pueden "reutilizar" gramáticas, por ejemplo:
numimag = Word(nums) + "i"
numreal = Word(nums)
numcomplex = numimag | numreal + Opt("+" + numimag)

# Funcion para cambiar a complejo numero durante parsear:
def hace_python_complejo(t):
    valid_python = "".join(t).replace("i", "j")
    for tipo in (int, complex):
        try:
            return tipo(valid_python)
        except ValueError:
            pass


numcomplex.set_parse_action(hace_python_complejo)
numcomplex.run_tests("""\
    3
    5i
    3+5i   
""")

# Excelente!!, bueno, los dejo, me voy a seguir tirando código...
