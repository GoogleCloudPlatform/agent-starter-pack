# PYTHON_ARGCOMPLETE_OK
import argparse

import argcomplete


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("arg", choices=["arg"])
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    print(args.arg)


if __name__ == "__main__":
    main()
