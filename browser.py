import tkinter

from css_parser import CSSParser, cascade_priority, style
from html_parser import Element, HTMLParser, print_tree
from layout import (
    DocumentLayout,
    HEIGHT,
    VSTEP,
    WIDTH,
    paint_tree,
)
from network import URL

# スクロールする時のステップ
SCROLL_STEP = 100

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()

        # スクロール関連
        self.scroll = 0
        self.max_scroll = 0
        self.window.bind("<Down>", self.scroll_down)
        self.window.bind("<Up>", self.scroll_up)

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, self.canvas)

    def load(self, url):
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        rules = DEFAULT_STYLE_SHEET.copy()
        links = [
            node.attributes["href"]
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "link"
            and node.attributes.get("rel") == "stylesheet"
            and "href" in node.attributes
        ]
        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except Exception:
                continue
            rules.extend(CSSParser(body).parse())
        style(self.nodes, sorted(rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.max_scroll = self.calculate_max_scroll()
        self.draw()

    def scroll_down(self, e):
        self.scroll = min(self.max_scroll, self.scroll + SCROLL_STEP)
        self.draw()

    def scroll_up(self, e):
        self.scroll = max(0, self.scroll - SCROLL_STEP)
        self.draw()

    def calculate_max_scroll(self):
        return max(0, self.document.height + 2 * VSTEP - HEIGHT)

def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--tree":
        body = URL(sys.argv[2]).request()
        nodes = HTMLParser(body).parse()
        print_tree(nodes)
    else:
        Browser().load(URL(sys.argv[1]))
        tkinter.mainloop()
