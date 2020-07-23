import re
import requests
import json
import os
import sys

from aiosmtpd.controller import Controller
from urllib.parse import urljoin


class EmailHandler:
    def __init__(self, signal_rest_url: str, sender_number: str):
        self.receiver_regex = re.compile(r"(\+\d+)@signal.localdomain")
        self.subject_regex = re.compile(r"Subject: (.*)\n")
        self.image_regex = re.compile(
            r'Content-Type: image/png; name=".*"\n+((?:[A-Za-z0-9+/]{4}|\n)*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=))'
        )

        self.signal_rest_url = signal_rest_url
        self.sender_number = sender_number

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if not re.match(self.receiver_regex, address):
            return "550 Malformed receiver address"
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        print(envelope.rcpt_tos)
        try:
            receiver_number = re.search(self.receiver_regex, envelope.rcpt_tos[0]).group(1)
        except TypeError:
            return "500 Malformed receiver address"

        # Remove carriage returns, they break the image checking regex
        content = envelope.content.decode("utf8").replace("\r", "")

        msg = re.search(self.subject_regex, content).group(1)

        payload = {
          "message": msg,
          "number": self.sender_number,
          "recipients": [
            receiver_number
          ]
        }

        if match := re.search(self.image_regex, content):
            image = match.group(1).replace("\n", "")
            payload["base64_attachments"] = [image]

        headers = {
            'Content-Type': 'application/json'
        }

        url = urljoin(self.signal_rest_url, "v2/send")
        response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

        if response.status_code == 201:
            return "250 Message accepted for delivery"
        else:
            return "554 Sending signal message has failed"


def run():
    try:
        signal_rest_url = os.environ["SIGNAL_REST_URL"]
        sender_number = os.environ["SENDER_NUMBER"]
    except KeyError:
        sys.exit("Please set the required environment variables.")

    print("Starting email2signal-rest server")
    email_handler = EmailHandler(signal_rest_url, sender_number)
    controller = Controller(email_handler)
    controller.start()
    input("Server started. Press Return to quit.")
    controller.stop()


if __name__ == "__main__":
    run()
