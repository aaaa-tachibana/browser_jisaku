import socket
import ssl


class URL:
    def __init__(self, url):
        url = url.strip()
        self.scheme, url = url.split("://", 1)
        self.scheme = self.scheme.strip().casefold()
        assert self.scheme in ["http", "https"]

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in url:
            url += "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # ポート番号が指定されている場合は取得
        if ":" in self.host:
            self.host, self.port = self.host.split(":", 1)
            self.port = int(self.port)

    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path

    def request(self):
        # TCP/IPソケットの作成
        s = socket.socket(
            family=socket.AF_INET,  # IPv4
            type=socket.SOCK_STREAM,  # 任意の量で通信できる
            proto=socket.IPPROTO_TCP,  # TCP
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
    
    def resolve(self, url):
        # 通常のURL
        if "://" in url:
            return URL(url)
        # 相対URL（fonts.css → /fonts.css など）
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            url = dir + "/" + url
        # スキーム相対URL
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host +
                       ":" + str(self.port) + url)   
