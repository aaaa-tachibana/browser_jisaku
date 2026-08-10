import tkinter

from css_parser import CSSParser, cascade_priority, style
from html_parser import Element, HTMLParser, Text, print_tree
from layout import (
    DocumentLayout,
    DrawLine,
    DrawOutline,
    DrawRect,
    DrawText,
    HEIGHT,
    Rect,
    VSTEP,
    WIDTH,
    get_font,
    paint_tree,
    tree_to_list,
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
            height=HEIGHT,
        )
        self.canvas.pack()
        self.tabs = []
        self.active_tab = None
        self.chrome = Chrome(self)
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Up>", self.handle_up)
        self.window.bind("<Button-1>", self.handle_click)

    def handle_down(self, e):
        self.active_tab.scroll_down()
        self.draw()

    def handle_up(self, e):
        self.active_tab.scroll_up()
        self.draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.chrome.click(e.x, e.y)
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()

    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)


class Tab:
    def __init__(self, tab_height):
        self.scroll = 0
        self.max_scroll = 0
        self.url = None
        self.tab_height = tab_height

    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll:
                continue
            cmd.execute(self.scroll - offset, canvas)

    def load(self, url):
        self.url = url
        self.scroll = 0
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

    def scroll_down(self):
        self.scroll = min(self.max_scroll, self.scroll + SCROLL_STEP)

    def scroll_up(self):
        self.scroll = max(0, self.scroll - SCROLL_STEP)

    def calculate_max_scroll(self):
        return max(0, self.document.height + 2 * VSTEP - self.tab_height)

    def click(self, x, y):
        y += self.scroll
        objs = [
            obj for obj in tree_to_list(self.document, [])
            if obj.x <= x < obj.x + obj.width
            and obj.y <= y < obj.y + obj.height
        ]
        if not objs:
            return
        # クリックされたオブジェクト
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                # リンクをクリックした
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elt = elt.parent


class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, "normal", "roman")
        self.font_height = self.font.metrics("linespace")
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2 * self.padding
        plus_width = self.font.measure("+") + 2 * self.padding
        self.new_tab_rect = Rect(
            self.padding,
            self.padding,
            self.padding + plus_width,
            self.padding + self.font_height,
        )
        self.bottom = self.tabbar_bottom

    def tab_rect(self, i):
        tabs_start = self.new_tab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2 * self.padding
        return Rect(
            tabs_start + tab_width * i,
            self.tabbar_top,
            tabs_start + tab_width * (i + 1),
            self.tabbar_bottom,
        )

    def paint(self):
        cmds = []
        # 背景と下線を描画
        cmds.append(DrawRect(Rect(0, 0, WIDTH, self.bottom), "white"))
        cmds.append(DrawLine(0, self.bottom, WIDTH, self.bottom, "black", 1))

        # 新しいタブの四角形とプラス記号を描画
        cmds.append(DrawOutline(self.new_tab_rect, "black", 1))
        cmds.append(DrawText(
            self.new_tab_rect.left + self.padding,
            self.new_tab_rect.top,
            "+",
            self.font,
            "black",
        ))
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            if tab == self.browser.active_tab:
                cmds.append(DrawRect(bounds, "lightgray"))
            cmds.append(DrawLine(bounds.left, 0, bounds.left, bounds.bottom, "black", 1))
            cmds.append(DrawLine(bounds.right, 0, bounds.right, bounds.bottom, "black", 1))
            cmds.append(DrawText(
                bounds.left + self.padding,
                bounds.top + self.padding,
                "Tab {}".format(i),
                self.font,
                "black",
            ))
            if tab == self.browser.active_tab:
                cmds.append(DrawLine(0, bounds.bottom, bounds.left, bounds.bottom, "black", 1))
                cmds.append(DrawLine(bounds.right, bounds.bottom, WIDTH, bounds.bottom, "black", 1))
        return cmds

    def click(self, x, y):
        if self.new_tab_rect.contains_point(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains_point(x, y):
                    self.browser.active_tab = tab
                    break


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--tree":
        body = URL(sys.argv[2]).request()
        nodes = HTMLParser(body).parse()
        print_tree(nodes)
    else:
        Browser().new_tab(URL(sys.argv[1]))
        tkinter.mainloop()
