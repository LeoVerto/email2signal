import smtplib
import ssl

from socket import gaierror

from aiosmtpd.smtp import Envelope


def send_mail(host: str, port: int, user: str, password: str, e: Envelope) -> str:
    context = ssl.create_default_context()

    try:
        server = smtplib.SMTP(host, port)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user, password)
        server.sendmail(user, e.rcpt_tos, e.content, e.mail_options, e.rcpt_options)

    except (gaierror, ConnectionRefusedError):
        return "421 Failed to connect to the server. Bad connection settings?"
    except smtplib.SMTPAuthenticationError:
        return "530 Failed to connect to the server. Wrong user/password?"
    except smtplib.SMTPException as e:
        return "554 SMTP error occurred: " + str(e)
    finally:
        server.quit()

    return "250 OK"
