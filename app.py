import asyncio
import re
import requests
import json
import os
import sys

from typing import Dict
from urllib.parse import urljoin

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session, SMTP
from sendmail import send_mail


class EmailHandler:
    def __init__(self, config: Dict[str, str]):
        self.receiver_regex = re.compile(r"(\+?\d+)@signal.localdomain")
        self.subject_regex = re.compile(r"Subject: (.*)\n")
        self.image_regex = re.compile(
            r'Content-Type: image/png; name=".*"\n+((?:[A-Za-z\d+/]{4}|\n)*(?:[A-Za-z\d+/]{2}==|[A-Za-z\d+/]{3}=)?)'
        )
        self.config = config

    async def handle_RCPT(self, server: SMTP, session: Session, envelope: Envelope, address, rcpt_options: list[str]) -> str:
        # match and process signal number
        if match := re.search(self.receiver_regex, address):
            try:
                number = match.group(1)
            except TypeError:
                return "500 Malformed receiver address"

            if not address.startswith("+"):
                number = "+" + number

            envelope.rcpt_tos.append(number)
        # simply append normal mail address
        else:
            envelope.rcpt_tos.append(address)

        return "250 OK"

    async def handle_DATA(self, server: SMTP, session: Session, envelope: Envelope) -> str:
        signal_numbers = []
        mail_addresses = []
        for addr in envelope.rcpt_tos:
            # a real email address cannot start with a special char
            if addr.startswith("+"):
                signal_numbers.append(addr)
            else:
                mail_addresses.append(addr)

        # send signal message if required
        if len(signal_numbers) > 0:
            print("Forwarding message to signal")
            success = await self.send_signal(envelope, signal_numbers)

            if not success:
                return "554 Sending signal message has failed"

        # send email if required
        if len(mail_addresses) == 0:
            return "250 Message accepted for delivery"
        else:
            envelope.rcpt_tos = mail_addresses

            print(f"Sending email via MTA. From: {envelope.mail_from} To: {envelope.rcpt_tos}")
            return send_mail(self.config["smtp_host"], int(self.config["smtp_port"]), self.config["smtp_user"],
                             self.config["smtp_passwd"], envelope)

    async def send_signal(self, envelope: Envelope, signal_receivers: list[str]) -> bool:
        # Remove carriage returns, they break the image checking regex
        content = envelope.content.decode("utf8").replace("\r", "")

        msg = re.search(self.subject_regex, content).group(1)

        payload = {
            "message": msg,
            "number": self.config["sender_number"],
            "recipients": signal_receivers
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
            return True
        else:
            return False


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
