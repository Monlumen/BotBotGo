
class Dimension:
    def __init__(self, title, instruction, content=None, refined_content=None, page_relevance=None):
        self.title = title
        self.instruction = instruction
        self.content = content
        self.refined_content = refined_content
        self.page_relevance = page_relevance if page_relevance else []
            # [(str, str, float)]  名称, 关联点, 评分

    def to_dict(self):
        return {
            "title": self.title,
            "instruction": self.instruction,
            "content": self.content,
            "page_relevance": self.page_relevance,
            "refined_content": self.refined_content
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            title=data.get("title"),
            instruction=data.get("instruction"),
            content=data.get("content",None),
            page_relevance=[(name, rel_point, rel_rating)
                            for name, rel_point, rel_rating
                            in data.get("page_relevance", None)],
            refined_content=data.get("refined_content", None)
        )
        return obj

    def title_content(self):
        return '["' + self.title + '", "' + self.content + '"]'

    def useful_pages(self) -> [(str, str, float)]:
        if not self.page_relevance:
            return []
        self.page_relevance.sort(key=lambda x: x[2], reverse=True)
        maximum_rating = self.page_relevance[0][2]
        page_rels = []
        for idx in range(len(self.page_relevance)):
            page_name, rel_keyword, rel_rating = self.page_relevance[idx]
            if idx >= 3 and rel_rating < maximum_rating - 2:
                break
            page_rels += [(page_name, rel_keyword, rel_rating)]
        return page_rels