import asyncio
import re
import requests
import json
import os
import sys

from typing import Dict
from urllib.parse import urljoin

from aiosmtpd.controller import Controller
from sendmail import send_mail


class EmailHandler:
    def __init__(self, config: Dict[str, str]):
        self.receiver_regex = re.compile(r"(\+\d+)@signal.localdomain")
        self.subject_regex = re.compile(r"Subject: (.*)\n")
        self.image_regex = re.compile(
            r'Content-Type: image/png; name=".*"\n+((?:[A-Za-z\d+/]{4}|\n)*(?:[A-Za-z\d+/]{2}==|[A-Za-z\d+/]{3}=)?)'
        )
        self.config = config
        self.forward_signal = False

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if re.match(self.receiver_regex, address):
            self.forward_signal = True
        else:
            self.forward_signal = False

        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        if self.forward_signal:
            print("Forwarding message to signal")
            return await self.send_signal(envelope)
        else:
            print("Sending email via MTA")
            return send_mail(self.config["smtp_host"], int(self.config["smtp_port"]), self.config["smtp_user"],
                      self.config["smtp_passwd"], envelope)

    async def send_signal(self, envelope):
        try:
            receiver_number = re.search(self.receiver_regex, envelope.rcpt_tos[0]).group(1)
        except TypeError:
            return "500 Malformed receiver address"

        # Remove carriage returns, they break the image checking regex
        content = envelope.content.decode("utf8").replace("\r", "")

        msg = re.search(self.subject_regex, content).group(1)

        payload = {
            "message": msg,
            "number": self.config["sender_number"],
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

        url = urljoin(self.config["signal_rest_url"], "v2/send")
        response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

        if response.status_code == 201:
            return "250 Message accepted for delivery"
        else:
            return "554 Sending signal message has failed"


async def amain(loop: asyncio.AbstractEventLoop):
    try:
        config = {
            "signal_rest_url": os.environ["SIGNAL_REST_URL"],
            "sender_number": os.environ["SENDER_NUMBER"],
            "smtp_host": os.environ["SMTP_HOST"],
            "smtp_user": os.environ["SMTP_USER"],
            "smtp_passwd": os.environ["SMTP_PASSWORD"],
            "smtp_port": os.getenv("SMTP_PORT", "587")
        }
    except KeyError:
        sys.exit("Please set the required environment variables.")

    print("Starting email2signal server")
    email_handler = EmailHandler(config)
    controller = Controller(email_handler, hostname="")
    controller.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(amain(loop=loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
