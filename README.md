# Forward email notifications to signal using signal-cli

This project was built to solve my my use-case of sending Grafana alerts via Signal (see grafana/grafana#14952 for the open issue).

Currently this just means that a Docker container running a Python app listens on port 8025 for incoming emails, extracts the
subject and the first image (if it exists), and finally utilizes another container running signal-cli ([bbernhard/signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api))
to send a message to a signal number as specified in the receiver address.

If the receiver address does not contain a valid phone number, the email is then instead forwarded using an external SMTP server.

## Setup
### DANGER
If you run this compose file witht the "ports" section uncommented on a server directly connected to the internet,
you will be running an open SMTP relay and bad actors ***will*** use it to send spam emails.

Either only send emails from other docker containers or run the server in a network behind a firewall if you don't want your IP to be blacklisted.

The easiest way to set up this project is by using docker-compose with a compose file based on the following template:
```yaml
version: "2.4"

services:
  signal-rest:
    image: bbernhard/signal-cli-rest-api:latest
    container_name: signal-rest
    restart: always
    volumes:
      - ./signal-rest:/home/.local/share/signal-cli
  
  email2signal:
    image: leoverto/email2signal:latest
    container_name: email2signal
    restart: always
    # ports:
    #   - 8025:8025
    environment:
      - SIGNAL_REST_URL=http://signal-rest:8080
      - SENDER_NUMBER
      - SMTP_HOST
      - SMTP_USER
      - SMTP_PASSWORD
    depends_on:
      - signal-rest
```

[signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) needs to be setup by either copying the `data` folder from a local signal-cli installation
into `./signal-rest` or exposing port 8080 on the container temporarily and registering a number via the API.

You need to set the variables listed in the docker-compose file (preferrably by using a .env file). If you don't need to forward emails to an external SMTP server
you can set the `SMTP_*` variables to an empty string.

The receiver address for the emails has to follow the format `[SIGNAL_NUMBER]@signal.localdomain`, otherwise they will be forwarded to the SMTP server.

## Grafana
This has not been tested to work with the "Single email" setting. Make sure "Include image" is enabled if you want to receive snapshots of the alert graph.
