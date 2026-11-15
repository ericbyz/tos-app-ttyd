#!/usr/bin/env python3
"""Generate ttyd.lang for the TOS App Center (26 locales, English fill)."""
NAME_EN = "ttyd Web Terminal"
AUTHOR = "ericbyz"
DESC_EN = (
    "Share the TNAS terminal over the web: a full bash session in the TOS "
    "desktop floating window from any browser. Packaged unmodified from upstream "
    "tsl0922/ttyd (MIT). First launch prompts for a generated credential "
    "(admin / random password, stored in /etc/ttyd/ttyd.env)."
)
NOTE_EN = "1. Repackaged upstream tsl0922/ttyd (MIT) unmodified for TOS."
NOTE_ZH = "1. 将上游 tsl0922/ttyd(MIT)原样封装为 TOS 应用。"

PRIMARY = [
    ("zh-cn", "ttyd 网页终端",
     "在 TOS 悬浮窗里直接打开 TNAS 的 bash 终端,任意浏览器可用,不用 SSH 客户端。"
     "上游 musl 静态二进制原样封装(MIT),首次打开输入安装时自动生成的账号密码"
     "(admin / 随机密码,存于 /etc/ttyd/ttyd.env,可修改后 systemctl restart ttyd)。"
     "终端会话为只读用户,操作 NAS 文件请配合 sudo 场景按需授权。"),
    ("zh-hk", "ttyd 網頁終端",
     "在 TOS 懸浮窗裡直接打開 TNAS 的 bash 終端,任意瀏覽器可用,不用 SSH 客戶端。"
     "上游 musl 靜態二進制原樣封裝(MIT),首次打開輸入安裝時自動生成的賬號密碼"
     "(admin / 隨機密碼,存於 /etc/ttyd/ttyd.env,可修改後 systemctl restart ttyd)。"),
]

ORDER = ["zh-cn", "zh-hk", "en-us", "ko-kr", "ja-jp", "de-de", "fr-fr", "it-it",
         "es-es", "hu-hu", "pl-pl", "tr-tr", "ru-ru", "pt-pt", "cs-cz", "da-dk",
         "nl-nl", "nb-no", "sv-se", "el-gr", "ro-ro", "th-th", "vi-vn", "id-id",
         "ar-sa", "he-il"]

NATIVE = {
    "ja-jp": "ブラウザから NAS の bash ターミナルを直接操作:SSH クライアント不要。上流の musl 静的バイナリを無改修でパッケージ化(MIT)。初回はインストール時に生成された認証情報(admin/ランダムパスワード、/etc/ttyd/ttyd.env)を入力します。",
    "ko-kr": "브라우저에서 NAS bash 터미널을 직접 사용: SSH 클라이언트가 필요 없습니다. 업스트림 musl 정적 바이너리를 무수정 패키징(MIT). 첫 접속 시 설치 중 생성된 자격 증명(admin/랜덤 비밀번호, /etc/ttyd/ttyd.env)을 입력합니다.",
    "de-de": "Bedienen Sie die TNAS-Bash-Shell direkt im Browser — kein SSH-Client nötig. Upstream musl-statisch, unverändert paketiert (MIT). Erster Login mit generierten Zugangsdaten (admin/Zufallspasswort, in /etc/ttyd/ttyd.env).",
    "fr-fr": "Utilisez le shell bash du TNAS directement dans le navigateur, sans client SSH. Binaire musl statique upstream intact (MIT). Première connexion avec identifiants générés (admin/mot de passe aléatoire, /etc/ttyd/ttyd.env).",
    "es-es": "Use la shell bash del TNAS directamente en el navegador, sin cliente SSH. Binario musl estático upstream intacto (MIT). Primer acceso con credenciales generadas (admin/contraseña aleatoria, /etc/ttyd/ttyd.env).",
    "ru-ru": "Работайте с bash-шеллом NAS прямо в браузере — SSH-клиент не нужен. Оригинальный статический musl-бинарник без изменений (MIT). Первый вход с сгенерированными учётными данными (admin/случайный пароль, /etc/ttyd/ttyd.env).",
}

def main(out_path):
    lines = []
    for loc in ORDER:
        name, desc = NAME_EN, NATIVE.get(loc, DESC_EN)
        for l, n, d in PRIMARY:
            if l == loc:
                name, desc = n, d
                break
        note = NOTE_ZH if loc in ("zh-cn", "zh-hk") else NOTE_EN
        lines += [f"[{loc}]", f'name = "{name}"', f'auth = "{AUTHOR}"',
                  f'descript = "{desc}"', f'note = "{note}"', ""]
    open(out_path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("wrote", out_path, len(ORDER), "locales")

if __name__ == "__main__":
    main("ttyd.lang")
