Frequently asked questions
===========================


Is UTF-8 everywhere already?
----------------------------

Not really, that is a dangerous assumption. Looking at https://w3techs.com/technologies/overview/character_encoding may
seem like encoding detection is a thing of the past but not really. Solo based on 33k websites, you will find
3,4k responses without predefined encoding. 1,8k websites were not UTF-8, merely half!

This statistic (w3techs) does not offer any ponderation, so one should not read it as
"I have a 97 % chance of hitting UTF-8 content on HTML content".

(2021 Top 1000 sites from 80 countries in the world according to Data for SEO) https://github.com/potiuk/test-charset-normalizer

First of all, neither requests, chardet or charset-normalizer are dedicated to HTML content.
The detection concern every text document, like SubRip Subtitle files for instance. And by my own experiences, I never had
a single database using full utf-8, many translated subtitles are from another era and never updated.

It is so hard to find any stats at all regarding this matter. Users' usages can be very dispersed, so making
assumptions are unwise.

The real debate is to state if the detection is an HTTP client matter or not. That is more complicated and not my field.

Some individuals keep insisting that the *whole* Internet is UTF-8 ready. Those are absolutely wrong and very Europe and North America-centered,
In my humble experience, the countries in the world are very disparate in this evolution. And the Internet is not just about HTML content.
Having a thorough analysis of this is very scary.

Should I bother using detection?
--------------------------------

In the last resort, yes. You should use well-established standards, eg. predefined encoding, at all times.
When you are left with no clue, you may use the detector to produce a usable output as fast as possible.

Is it backward-compatible with Chardet?
---------------------------------------

If you use the legacy `detect` function,
Then this change is mostly backward-compatible, exception of a thing:

- This new library support way more code pages (x3) than its counterpart Chardet.
- Based on the 30-ich charsets that Chardet support, expect roughly 80% BC results

We do not guarantee this BC exact percentage through time. May vary but not by much.

Isn't it the same as Chardet?
-----------------------------

The objective is the same, provide you with the best answer (charset) we can given any sequence of bytes.
The method actually differs.

We do not "train" anything to build a probe for a specific encoding. In addition to finding any languages (intelligent
design) by some rudimentary statistics (character frequency ordering) we built a mess detector to assist the language
detection.

Any code page supported by your cPython is supported by charset-normalizer! It is that simple, no need to update the
library. It is as generic as we could do.

I can't build standalone executable
-----------------------------------

If you are using ``pyinstaller``, ``py2exe`` or alike, you may be encountering this or close to:

    ModuleNotFoundError: No module named 'charset_normalizer.md__mypyc'

Why?

- Your package manager picked up a optimized (for speed purposes) wheel that match your architecture and operating system.
- Finally, the module ``charset_normalizer.md__mypyc`` is imported via binaries and can't be seen using your tool.

How to remedy?

If your bundler program support it, set up a hook that implicitly import the hidden module.
Otherwise, follow the guide on how to install the vanilla version of this package. (Section: *Optional speedup extension*)
