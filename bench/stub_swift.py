#!/usr/bin/env python3
"""Replace every function and initializer body in Swift files with a fatalError stub,
keeping declarations, doc comments, stored properties and types.

  stub_swift.py FILE...        rewrites the files in place

A body is the brace block that follows a `func` or `init` declaration. String
literals (including multi-line and interpolated ones) and comments are skipped
when matching braces. Nested functions disappear with their parent's body.
"""
import re
import sys

DECL = re.compile(r"^[ \t]*(?:@\w+(?:\([^)]*\))?\s+)*(?:(?:public|internal|private|fileprivate|static|class|final|override|mutating|nonmutating|convenience|required|nonisolated|@discardableResult)\s+)*(?:func\s+[^\s(<]+|init[?!]?)\s*[(<]", re.M)


def skip_string(src, i):
    """i points at a quote; return the index after the literal."""
    if src.startswith('"""', i):
        j = i + 3
        while True:
            k = src.find('"""', j)
            if k == -1:
                return len(src)
            if src[k - 1] != "\\":
                return k + 3
            j = k + 3
    j = i + 1
    while j < len(src):
        c = src[j]
        if c == "\\":
            if src.startswith("\\(", j):
                j = skip_balanced(src, j + 1, "(", ")")
                continue
            j += 2
            continue
        if c == '"':
            return j + 1
        if c == "\n":
            return j
        j += 1
    return j


def skip_comment(src, i):
    if src.startswith("//", i):
        k = src.find("\n", i)
        return len(src) if k == -1 else k
    depth, j = 1, i + 2
    while j < len(src) and depth:
        if src.startswith("/*", j):
            depth, j = depth + 1, j + 2
        elif src.startswith("*/", j):
            depth, j = depth - 1, j + 2
        else:
            j += 1
    return j


def skip_balanced(src, i, open_, close):
    """i points at open_; return the index after its matching close."""
    depth, j = 0, i
    while j < len(src):
        if src.startswith("//", j) or src.startswith("/*", j):
            j = skip_comment(src, j)
            continue
        c = src[j]
        if c == '"':
            j = skip_string(src, j)
            continue
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError("unbalanced")


def body_start(src, i):
    """From a declaration start, find the '{' opening its body, or None (a protocol requirement)."""
    j = i
    paren = 0
    while j < len(src):
        if src.startswith("//", j) or src.startswith("/*", j):
            j = skip_comment(src, j)
            continue
        c = src[j]
        if c == '"':
            j = skip_string(src, j)
            continue
        if c in "([<":
            paren += 1
        elif c in ")]>" and paren:
            paren -= 1
        elif c == "{" and paren == 0:
            return j
        elif c == "\n" and paren == 0:
            # a declaration may continue on the next line (where clauses, throws, return types)
            rest = src[j + 1:].lstrip(" \t")
            if not rest or not (rest[0] in "{-:" or rest.startswith(("where", "throws", "rethrows", "async", "->"))):
                return None
        j += 1
    return None


def stub(src):
    out, pos, count = [], 0, 0
    for m in DECL.finditer(src):
        if m.start() < pos:
            continue
        b = body_start(src, m.start())
        if b is None:
            continue
        end = skip_balanced(src, b, "{", "}")
        indent = re.match(r"[ \t]*", src[m.start():]).group(0)
        out.append(src[pos:b + 1])
        out.append(f'\n{indent}    fatalError("not implemented")\n{indent}}}')
        pos = end
        count += 1
    out.append(src[pos:])
    return "".join(out), count


if __name__ == "__main__":
    for path in sys.argv[1:]:
        text = open(path).read()
        new, n = stub(text)
        open(path, "w").write(new)
        print(f"{path}: {n} bodies stubbed, {len(text.splitlines())} -> {len(new.splitlines())} lines")
