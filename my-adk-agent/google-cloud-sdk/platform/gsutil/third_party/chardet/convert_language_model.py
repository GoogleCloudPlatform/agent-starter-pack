#!/usr/bin/env python

######################## BEGIN LICENSE BLOCK ########################
# Contributor(s):
#   10.02.2015 - helour - first attempt
#   08.08.2016 - Dan Blanchard - first usable release
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301  USA
#
######################### END LICENSE BLOCK #########################

"""
Convert old style SBCS model to new
"""

import os
import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from string import ascii_letters

import chardet
from chardet import __version__
from chardet.metadata.languages import LANGUAGES
from chardet.sbcharsetprober import SingleByteCharSetModel

# Turn ascii_letters into a set to make other ops easier
ascii_letters = set(ascii_letters)


def normalize_name(charset_name):
    """Convert name to proper Python constant format"""
    # Title case to start
    charset_name = charset_name.upper()
    # Underscores instead of hyphens
    charset_name = charset_name.replace("-", "_")
    return charset_name


def convert_sbcs_model(old_model, alphabet):
    """Create a SingleByteCharSetModel object representing the charset."""
    # Setup tables necessary for computing transition frequencies for model
    char_to_order = dict(enumerate(old_model["char_to_order_map"]))
    pos_ratio = old_model["typical_positive_ratio"]
    keep_ascii_letters = old_model["keep_english_letter"]

    curr_model = SingleByteCharSetModel(
        charset_name=old_model["charset_name"],
        language=old_model["language"],
        char_to_order_map=char_to_order,
        # language_model is filled in later
        language_model=None,
        typical_positive_ratio=pos_ratio,
        keep_ascii_letters=keep_ascii_letters,
        alphabet=alphabet,
    )
    return curr_model


def print_char_to_order(var_name, order_map, charset_name, output_file):
    print(f"{var_name} = {{", file=output_file)
    for char, order in sorted(order_map.items()):
        char_bytes = bytes(bytearray((char,)))
        try:
            unicode_char = char_bytes.decode(charset_name)
        except UnicodeError:
            unicode_char = None
        print(f"     {char!r}: {order!r},  # {unicode_char!r}", file=output_file)
    print("}\n", file=output_file)


def print_language_model(var_name, language_model, output_file, char_ranks):
    print(
        "# 3: Positive\n# 2: Likely\n# 1: Unlikely\n# 0: Negative\n",
        file=output_file,
    )
    print(f"{var_name} = {{", file=output_file)
    for first_char, sub_dict in sorted(language_model.items()):
        # Skip empty sub_dicts
        if not sub_dict or first_char not in char_ranks:
            continue
        print(f"    {char_ranks[first_char]!r}: {{  # {first_char!r}", file=output_file)
        for second_char, likelihood in sorted(sub_dict.items()):
            if second_char not in char_ranks:
                continue
            print(
                f"        {char_ranks[second_char]!r}: {likelihood!r},  # "
                f"{second_char!r}",
                file=output_file,
            )
        print("    },", file=output_file)
    print("}\n", file=output_file)


def convert_models_for_lang(language):
    """Convert old SingleByteCharSetModels for the given language"""
    # Validate language
    language = language.title()
    lang_metadata = LANGUAGES.get(language)
    if not lang_metadata:
        raise ValueError(
            f"Unknown language: {language}. If you are adding a model for a"
            " new language, you must first update metadata/"
            "languages.py"
        )
    lang_mod_name = f"lang{language.lower()}model"
    if not os.path.exists(os.path.join("chardet", lang_mod_name + ".py")):
        print(f"Skipping {language} because it does not have an old model.")
        return
    lang_mod = getattr(chardet, lang_mod_name)
    print(
        f"\n{language}\n----------------------------------------------------------------"
    )
    print(f"Keep ASCII Letters: {lang_metadata.use_ascii}")
    print(f"Alphabet: {lang_metadata.alphabet}")

    # Create char-to-order maps (aka char-to-rank dicts)
    charset_models = {}
    char_ranks = {}
    order_to_chars = {}
    for var_name in dir(lang_mod):
        if not ("Model" in var_name and "LangModel" not in var_name):
            continue
        old_model = getattr(lang_mod, var_name)
        charset_name = old_model["charset_name"]

        print(f"Converting charset model for {charset_name}")
        sys.stdout.flush()
        charset_models[charset_name] = convert_sbcs_model(
            old_model, lang_metadata.alphabet
        )
        # Since we don't know which charsets have which characters, we have to
        # try to reconstruct char_ranks (for letters only, since that's all
        # the old language models contain)
        for byte_hex, order in charset_models[charset_name].char_to_order_map.items():
            # order 64 was basically ignored before because of the off by one
            # error, but it's hard to know if training took that into account
            if order > 64:
                continue
            # Convert to bytes in Python 2 and 3
            char = bytes(bytearray((byte_hex,)))
            try:
                unicode_char = char.decode(charset_name)
            except UnicodeDecodeError:
                continue
            if unicode_char not in char_ranks:
                char_ranks[unicode_char] = order
                order_to_chars[order] = unicode_char
            elif char_ranks[unicode_char] != order:
                raise ValueError(f"Unstable character ranking for {unicode_char}")

    old_lang_model = getattr(lang_mod, f"{language.title()}LangModel")
    language_model = {}
    # Preserve off-by-one error here by ignoring first column and row
    for i in range(1, 64):
        if i not in order_to_chars:
            continue
        lang_char = order_to_chars[i]
        language_model[lang_char] = {}
        for j in range(1, 64):
            if j not in order_to_chars:
                continue
            lang_char2 = order_to_chars[j]
            language_model[lang_char][lang_char2] = old_lang_model[(i * 64) + j]

    # Write output files
    print(f"Writing output file for {language}\n\n")
    sys.stdout.flush()
    with open(f"lang{language.lower()}model.py", "w", encoding="utf-8") as output_file:
        upper_lang = language.upper()
        # print header to set encoding
        print(
            "from chardet.sbcharsetprober import SingleByteCharSetModel\n\n",
            file=output_file,
        )

        lm_name = f"{upper_lang}_LANG_MODEL"
        print_language_model(lm_name, language_model, output_file, char_ranks)

        print(
            "# 255: Undefined characters that did not exist in training text\n"
            "# 254: Carriage/Return\n"
            "# 253: symbol (punctuation) that does not belong to word\n"
            "# 252: 0 - 9\n"
            "# 251: Control characters\n\n"
            "# Character Mapping Table(s):",
            file=output_file,
        )
        for charset_name, sbcs_model in charset_models.items():
            normal_name = normalize_name(charset_name)
            char_to_order_name = f"{normal_name}_{upper_lang}_CHAR_TO_ORDER"
            print_char_to_order(
                char_to_order_name,
                sbcs_model.char_to_order_map,
                charset_name,
                output_file,
            )

            sbcs_model_name = f"{normal_name}_{upper_lang}_MODEL"
            sbcs_model.char_to_order_map.clear()
            sbcs_model_repr = (
                repr(sbcs_model)
                .replace("None", lm_name)
                .replace("{}", char_to_order_name)
                .replace(", ", (",\n" + " " * (len(sbcs_model_name) + 26)))
            )
            print(f"{sbcs_model_name} = {sbcs_model_repr}\n", file=output_file)


def main():
    parser = ArgumentParser(
        description=__doc__, formatter_class=ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "language",
        help="The name of the language the input documents are "
        "in. Also the name of the language the generated "
        "model will detect. If no language is specified, "
        "models for all languages known to chardet will be"
        " trained.",
        nargs="*",
    )
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()

    if not args.language:
        args.language = list(sorted(LANGUAGES.keys()))

    for language in args.language:
        convert_models_for_lang(language)


if __name__ == "__main__":
    main()
