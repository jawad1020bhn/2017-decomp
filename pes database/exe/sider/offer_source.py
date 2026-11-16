#!/usr/bin/env python3
"""Makes the assembly of the offers for the user's players (incoming.c) that money_cave.py
keeps as INCOMING_SOURCE.

    python3 offer_source.py            prints the assembly, ready to paste
    python3 offer_source.py <file>     writes it to <file>

Needs gcc with -m32 (Debian: `apt install gcc-multilib`). The module itself needs no
compiler: money_cave.py assembles the text with keystone(), and the bytes it makes are the
bytes MLTransfers.lua ships, so `python3 money_cave.py build` checks the two against each
other on any machine.

What the cleaning does: gcc's directives and comments go (keystone wants code), its `.L<n>`
labels become `L<n>` and its `ds:` segment prefixes go. What is left is plain Intel syntax
in the same form as the other routines of the modules.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def assembly(path=os.path.join(HERE, 'incoming.c')):
    """gcc's assembly of incoming.c, cleaned for keystone()."""
    out = subprocess.run(['gcc', '-m32', '-Os', '-masm=intel', '-fno-pic', '-fno-stack-protector',
                          '-fno-asynchronous-unwind-tables', '-S', path, '-o', '-'],
                         capture_output=True, text=True, check=True).stdout
    lines = []
    for line in out.split('\n'):
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('\t.'):
            continue                                   # a directive
        if re.match(r'^\s*\.(section|text|globl|type|size|align|p2align|ident|file|cfi)', line):
            continue
        line = re.sub(r'\bds:', '', line)
        line = re.sub(r'\.L(\d+)', r'L\1', line)
        line = re.sub(r'^(\s*)\.L(\d+):', r'\1L\2:', line)
        line = line.replace(' :', ':')                      # %= labels: `name12 :`
        # gcc writes an absolute address without brackets; keystone would take it for a number
        line = re.sub(r'\b(DWORD|WORD|BYTE) PTR (?!\[)(0x[0-9a-fA-F]+|\d+)', r'\1 PTR [\2]', line)
        lines.append(line)
    text = '\n'.join(lines) + '\n'
    assert '.L' not in text and 'ds:' not in text, 'the cleaning missed something'
    return text


if __name__ == '__main__':
    text = assembly()
    if len(sys.argv) > 1:
        open(sys.argv[1], 'w').write(text)
        print('%s: %d lines' % (sys.argv[1], text.count('\n')))
    else:
        sys.stdout.write(text)
