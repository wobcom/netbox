from functools import wraps

def if_markdown(fn):
    @wraps(fn)
    def wrapped(self, s, *args, **kwargs):
        if self.no_markdown:
            return s
        return fn(self, s, *args, **kwargs)
    return wrapped


class Markdownify():
    def __init__(self, no_markdown=False):
        self.no_markdown = no_markdown

    @if_markdown
    def bold(self, s):
        return '**{}**'.format(s)

    def h(self, s, n):
        return '{} {}'.format('#'*n, s)

    @if_markdown
    def h1(self, s):
        return self.h(s, 1)

    @if_markdown
    def h2(self, s):
        return self.h(s, 2)

    @if_markdown
    def h3(self, s):
        return self.h(s, 3)
