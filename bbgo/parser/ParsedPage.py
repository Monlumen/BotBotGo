import re

class ParsedPage:
    def __init__(self, name: str, url: str, lines: [(int, str)],
                 replace_link_tag=True, replace_header_tag=True,
                 emoji: str="",
                 rating=0, annotation=None, translation=None):
        self.name = name
        self.url = url
        self.emoji = emoji
        self.replace_link_tag = replace_link_tag
        self.replace_header_tag = replace_header_tag
        self.lines = set()
        self.add_lines(set(lines))

        self.rating = rating # step 2
        self.annotation = annotation # step 2
        self.translation = translation # step 4

    def add_lines(self, new_lines):
        new_lines_set = set()
        for idx, content in new_lines:
            content = content.replace("<link>","").replace("</link>","") if self.replace_link_tag else content
            if self.replace_header_tag:
                content = re.sub(r"<h(\d)>", lambda m: "#" * int(m.group(1)) + " ", content)
                content = re.sub(r"</h\d>", "", content)
            new_lines_set.add((idx, content))
        self.lines = self.lines.union(set(new_lines_set))

    @property
    def title(self):
        return self.name

    @title.setter
    def title(self, new_title):
        self.name = new_title

    @property
    def content(self):
        return "".join(line[1] for line in sorted(self.lines, key=lambda x: x[0])) \
            if self.translation is None else self.translation

    def __str__(self):
        url_part = "(" + str(self.url) + ")\n" if self.url else ""
        rating_part = "相关性: " + str(self.rating) + "\n" if self.rating else ""
        annotaion_part = "注释: " + str(self.annotation) + "\n" if self.annotation else ""
        return f'"{self.name}"\n{url_part}{rating_part}{annotaion_part}{self.content}'

    def to_dict(self):
        """将 ParsedPage 转换为字典格式"""
        return {
            "name": self.name,
            "url": self.url,
            "emoji": self.emoji,
            "replace_link_tag": self.replace_link_tag,
            "replace_header_tag": self.replace_header_tag,
            "lines": list(self.lines),
            "rating": self.rating,
            "annotation": self.annotation,
            "translation": self.translation
        }

    @classmethod
    def from_dict(cls, data):
        """从字典格式恢复 ParsedPage"""
        obj = cls(
            name=data["name"],
            url=data.get("url", ""),
            lines=[(entry[0], entry[1]) for entry in data["lines"]],
            replace_link_tag=data["replace_link_tag"],
            replace_header_tag=data["replace_header_tag"],
            emoji=data.get("emoji", ""),
            rating=data.get("rating", 0),
            annotation=data.get("annotation", None),
            translation=data.get("translation", None)
        )

        return obj