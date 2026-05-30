from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template


class HTMLRenderer:
    TEMPLATE_DIR = Path("resources")
    TEMPLATE_NAME = "template.html.jinja2"

    def __init__(self, exportpath: Path, user: str) -> None:
        self.env = Environment(loader=FileSystemLoader(self.TEMPLATE_DIR))
        self.template = self.env.get_template(self.TEMPLATE_NAME)
        self.exportpath = exportpath
        self.user = user

    def render(self, messages):
        with open(self.exportpath / "index.html", "w") as f:
            f.write(self.template.render(user=self.user, messages=messages))
