import socket
import ssl
import tkinter
import tkinter.font as tkfont

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        
        if "/" not in url:
            url += "/"
        self.host , url = url.split("/", 1)
        self.path = "/" + url

        # ポート番号が指定されている場合は取得
        if ":" in self.host:
            self.host, self.port = self.host.split(":", 1)
            self.port = int(self.port)

    def request(self):
        # TCP/IPソケットの作成
        s = socket.socket(
            family=socket.AF_INET, # IPv4
            type=socket.SOCK_STREAM, # 任意の量で通信できる
            proto=socket.IPPROTO_TCP, # TCP
        )

        # 指定されたホストに接続
        s.connect((self.host, self.port))

        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # GETリクエスト文字列作成
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        # Hostヘッダー追加
        request += "Host: {}\r\n".format(self.host)
        # ヘッダーの終わりを示す空行を追加
        request += "\r\n"
        # リクエストを送信
        s.send(request.encode("utf-8"))

        # ソケットからファイルのようなオブジェクトを作成
        response = s.makefile("r", encoding="utf-8", newline="\r\n")
        statusline = response.readline()
        # バージョン、ステータスコード、説明を取得
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            # ヘッダー名と値を取得
            header, value = line.split(": ", 1)
            response_headers[header.casefold()] = value.strip()
        
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        
        # レスポンスボディを取得
        content = response.read()
        s.close()

        return content

class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, parent, attributes):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return "<{}>".format(self.tag)

SELF_CLOSING_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"
}

class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
    
    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()
    
    def add_text(self, text):
        if text.isspace():
            return
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)
    
    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"):
            return

        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, parent, attributes)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, parent, attributes)
            self.unfinished.append(node)
    
    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""
            
        return tag, attributes

# HTMLパーサーデバッグ用
def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

FONTS = {}
# フォントをキャッシング
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkfont.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

# windowのサイズ
WIDTH, HEIGHT = 800, 600
# 文字を表示する時の水平方向、垂直方向のステップ
HSTEP, VSTEP = 13,18

class Layout:
    def __init__(self, tree):
        self.display_list = []
        self.line = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        self.recurse(tree)
        self.flush()
    
    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
    
    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
    
    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)
    
    # 単語を行に追加
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        # 行の幅が画面の幅を超えた場合はフラッシュ
        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")
    
    # 文字のレンダリング位置をフォントサイズに合わせて調整し、行を確定してレンダリングリストに追加
    def flush(self):
        if not self.line: return

        # 行内で最も高い ascent に合わせてベースラインを決める
        max_ascent = max(font.metrics("ascent") for x, word, font in self.line)
        baseline = self.cursor_y + 1.25 * max_ascent

        # 各単語をベースラインにあわせて配置
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        # 次の行の開始位置へ進める
        max_descent = max(font.metrics("descent") for x, word, font in self.line)
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = HSTEP
        self.line = []

# スクロールする時のステップ
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT
        )
        self.canvas.pack()
        
        # スクロール関連
        self.scroll = 0
        self.max_scroll = 0
        self.window.bind("<Down>", self.scroll_down)
        self.window.bind("<Up>", self.scroll_up)
    
    def draw(self):
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x,y - self.scroll,text=word, font=font, anchor="nw")

    def load(self, url):
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        self.display_list = Layout(self.nodes).display_list
        self.max_scroll = self.calculate_max_scroll()
        self.draw()

    def scroll_down(self, e):
        self.scroll = min(self.max_scroll, self.scroll + SCROLL_STEP)
        self.draw()
    
    def scroll_up(self, e):
        self.scroll = max(0, self.scroll - SCROLL_STEP)
        self.draw()
    
    def calculate_max_scroll(self):
        if not self.display_list:
            return 0
        max_y = self.display_list[-1][1]
        return max(0, max_y + VSTEP - HEIGHT)
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--tree":
        body = URL(sys.argv[2]).request()
        nodes = HTMLParser(body).parse()
        print_tree(nodes)
    else:
        Browser().load(URL(sys.argv[1]))
        tkinter.mainloop()