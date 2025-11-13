import requests
import re


class Anki:
    def __init__(self, port=8765):
        self.port = port

    def _post(self, action, params, version=6):
        """AnkiConnectにリクエストを送信"""
        response = requests.post(f"http://localhost:{self.port}", json={
            "action": action,
            "version": version,
            "params": params
        })
        data = response.json()
        if data.get("error"):
            raise Exception(f"AnkiConnect Error: {data['error']}")
        return data.get("result")

    def get_notes(self, query):
        """
        指定したクエリに一致するノート情報を取得

        Args:
            query (str): デッキや条件を指定するクエリ (例: "deck:English::Listening")

        Returns:
            list: ノートの詳細情報
        """
        note_ids = self._post("findNotes", {"query": query})
        return self._post("notesInfo", {"notes": note_ids})

    def update_notes(self, notes):
        """
        ノート情報を更新

        Args:
            notes (list): 更新するノート情報
        """
        for note in notes:
            note_id = note['noteId']
            fields = {key: value['value'] for key, value in note['fields'].items()}
            self._post("updateNoteFields", {"note": {"id": note_id, "fields": fields}})
            print(f"Updated note: {note_id}")


class Formatter:
    CLEANUP_PATTERN = re.compile(r'<br>|</?div>|&nbsp;')
    PUNCTUATION_PATTERN = re.compile(r'([.!?])(?!\s)')
    WHITESPACE_PATTERN = re.compile(r'\s{2,}')
    
    @staticmethod
    def format_listening_html(string):
        """
        Listeningのデッキの整形用
        
        Args:
            string (str): 整形する対象の文字列 (例: "<div><div><div> Hello, World! [sound:hogehoge.wav]</div></div></div>")
        
        Returns:
            str: 整形された文字列
        """
        # 不要なタグや空白を削除
        string = Formatter.CLEANUP_PATTERN.sub('', string)

        # 特定の文字列を保護
        patterns = [
            (r'\[sound:[^\]]+\]', "__SOUND_TAG_"),
            (r'\.\.\.', "__ELLIPSIS_TAG_"),
            (r'!\?', "__EXCLAMATION_TAG_")
        ]

        # 各パターンを保護
        protected = {}
        for pattern, tag_base in patterns:
            matches = re.findall(pattern, string)
            for i, match in enumerate(matches):
                placeholder = f"{tag_base}{i}__"
                string = string.replace(match, placeholder)
                protected[placeholder] = match

        # ., !, ?のあとにスペースを入れる
        string = Formatter.PUNCTUATION_PATTERN.sub(r'\1 ', string)


        # 保護したタグを元に戻す
        for placeholder, original in protected.items():
            string = string.replace(placeholder, original)

        # 文間の空白を1つに統一
        string = Formatter.WHITESPACE_PATTERN.sub(' ', string)
        return string.strip()


def reform_listening():
    """
    deck:English::Listeningのノート内容を整形して更新
    """
    anki = Anki(port=8765)
    formatter = Formatter()

    # ノートを取得
    notes = anki.get_notes("deck:English::Listening")

    # ノート内容を整形
    for note in notes:
        if not 'Text' in note['fields']:
            print("ignore:", note)
            continue

        text_field = note['fields']['Text']['value']
        note['fields']['Text']['value'] = formatter.format_listening_html(text_field)

    # 更新
    anki.update_notes(notes)


if __name__ == "__main__":
    reform_listening()
