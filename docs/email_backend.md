# email_backend.py

## Overview
Handles sending files as email attachments using SMTP, with support for retries and dynamic subject lines.

## Key Components
- `do(process_parameters, settings, filename)`: Sends the specified file as an email attachment to recipients defined in the process parameters. Handles up to 10 retries and supports TLS and authentication.

## Usage
Call `do` with the appropriate parameters to send a file via email.
