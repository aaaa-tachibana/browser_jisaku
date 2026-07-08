import socket
import ssl
import tkinter

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

# 字句解析器
def lex(body):
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c
    return text

# windowのサイズ
WIDTH, HEIGHT = 800, 600
# 文字を表示する時の水平方向、垂直方向のステップ
HSTEP, VSTEP = 13,18
# 改行で段落区切りに見せるための垂直方向のステップ
PARAGRAPH_STEP = VSTEP * 1.2
# スクロールする時のステップ
SCROLL_STEP = 100

def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        # 改行処理
        if c == "\n":
            cursor_x = HSTEP
            cursor_y += PARAGRAPH_STEP
            continue
        
        # 表示リストに追加
        display_list.append(
            (cursor_x, cursor_y, c)
        )
        cursor_x += HSTEP
        # 水平方向のステップが画面の幅を超えた場合は垂直方向のステップを増やす
        if cursor_x >= WIDTH - HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP
    return display_list

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
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x,y - self.scroll,text=c)

    def calculate_max_scroll(self):
        if not self.display_list:
            return 0
        max_y = self.display_list[-1][1]
        return max(0, max_y + VSTEP - HEIGHT)

    def load(self, url):
        body = url.request()
        text = lex(body)

        self.display_list = layout(text)
        self.max_scroll = self.calculate_max_scroll()
        self.draw()

    def scroll_down(self, e):
        self.scroll = min(self.max_scroll, self.scroll + SCROLL_STEP)
        self.draw()
    
    def scroll_up(self, e):
        self.scroll = max(0, self.scroll - SCROLL_STEP)
        self.draw()

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()