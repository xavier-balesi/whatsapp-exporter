import glob
import re
from argparse import ArgumentParser
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from time import strptime

from loguru import logger
from pydantic import BaseModel

from whatsapp_exporter.renderer import HTMLRenderer


class WhatsappMessage(BaseModel):
    name: str
    date: datetime
    date_txt: str
    time_txt: str
    images: list[Path] = []
    videos: list[Path] = []
    text: list[str] = []


class PartialMessage(BaseModel):
    images: list[Path] = []
    videos: list[Path] = []
    text: list[str] = []


class MessageReader:

    FIRST_LINE_REGEX = re.compile(r"(\d{2}/\d{2}/\d{4}, \d{2}:\d{2}) - ([^:]+): (.*)")

    def __init__(self, file: TextIOWrapper) -> None:
        self.file: TextIOWrapper = file

    def read(self):
        end_of_file = False
        message: WhatsappMessage | None = None
        while not end_of_file:
            line = self.file.readline()
            if not line:
                end_of_file = True
                continue
            if self.is_first_line(line):
                if message is not None:
                    logger.debug(f"{message=}")
                    yield message
                message = self.parse_first_line(line)
            else:
                partial_message: PartialMessage = self.parse_other_line(line)
                self.merge_messages(message, partial_message)

    @staticmethod
    def is_first_line(line: str):
        match = MessageReader.FIRST_LINE_REGEX.match(line)
        if not match:
            return False

        return True

    def parse_first_line(self, line: str) -> WhatsappMessage:
        logger.debug(f"parsing first line: {line}")
        match = MessageReader.FIRST_LINE_REGEX.match(line)
        date_str, name, text = match.groups()
        logger.debug(f"{date_str=}")
        logger.debug(f"{name=}")
        logger.debug(f"{text=}")

        # TODO add images and videos parsing
        date = datetime.strptime(date_str, "%d/%m/%Y, %H:%M")
        date_txt = date.strftime("%d-%m-%Y")
        time_txt = date.strftime("%H:%M")
        message = WhatsappMessage(
            name=name, date=date, date_txt=date_txt, time_txt=time_txt, text=[text]
        )
        self.parse_text(message)
        return message

    def parse_other_line(self, line: str) -> PartialMessage:
        logger.debug(f"parsing other line: {line}")
        partial_message = PartialMessage(text=[line])
        self.parse_text(partial_message)
        return partial_message

    @staticmethod
    def parse_text(message: WhatsappMessage | PartialMessage):
        media_re = re.compile(r"\u200e([^ ]+) \(.*\)")
        new_text = []

        for text in message.text:
            match = media_re.match(text)
            if match:
                media = match.groups()[0]
                if media.startswith("IMG-"):
                    message.images.append(Path(media))
                elif media.startswith("VID-"):
                    message.videos.append(Path(media))
            else:
                new_text.append(text)

        message.text = new_text

    @staticmethod
    def merge_messages(message: WhatsappMessage, partial_message: PartialMessage):
        message.text.extend(partial_message.text)
        message.images.extend(partial_message.images)
        message.videos.extend(partial_message.videos)


class WhatsappExporter:

    def __init__(self, exportpath: Path) -> None:
        self.exportpath: Path = exportpath
        self._check_directory()

        self.txt: Path = self._find_txt_file()

    def process(self):
        with open(self.txt) as f:
            reader = MessageReader(f)
            messages = [message for message in reader.read()]

        return messages

    def _check_directory(self):
        if not self.exportpath.exists():
            raise Exception("Directory doesn't exist")

        if not self.exportpath.is_dir():
            raise Exception(f"{self.exportpath} is not a directory")

    def _find_txt_file(self):
        txt_files = glob.glob(f"{self.exportpath}/*.txt")

        if len(txt_files) == 0:
            raise Exception(f"No .txt file found in directory {self.exportpath}")

        if len(txt_files) > 1:
            raise Exception(f"Multiple .txt file found in directory {self.exportpath}")

        logger.info(f"using txt file {txt_files[0]}")

        return Path(txt_files[0])


def main():
    parser = ArgumentParser("Whatsapp Exporter")
    parser.add_argument("exportpath", help="whatsapp export directory path")
    parser.add_argument("user", help="the owner of the discussion")
    args = parser.parse_args()

    whatsapp_exporter = WhatsappExporter(Path(args.exportpath))
    messages = whatsapp_exporter.process()

    renderer = HTMLRenderer(Path(args.exportpath), args.user)
    renderer.render(messages)


if __name__ == "__main__":
    main()
