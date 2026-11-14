{
  "findings": [
    {
      "file": "lab5-canary/app/attachment_export.py",
      "start_line": 10,
      "end_line": 11,
      "class": "ssrf",
      "rule": "url-building",
      "message": "The URL built for tar.gz archive is constructed from input, allowing an attacker to control the target URL."
    },
    {
      "file": "lab5-canary/app/rules_loader.py",
      "start_line": 7,
      "end_line": 9,
      "class": "vulnerable-dependency",
      "rule": "pinned-package",
      "message": "The package 'yaml' is pinned to version 5.0.1, which is known to have a vulnerability."
    },
    {
      "file": "lab5-canary/app/ticket_access.py",
      "start_line": 13,
      "end_line": 15,
      "class": "path-traversal",
      "rule": "path-building",
      "message": "The ticket ID is used to build the path for the ticket, which could lead to path traversal if the ID contains special characters."
    },
    {
      "file": "lab5-canary/app/webhook_relay.py",
      "start_line": 6,
      "end_line": 8,
      "class": "injection",
      "rule": "sql-string-format",
      "message": "The event data is directly used in the SQL query, allowing for SQL injection if the data is not properly sanitized."
    }
  ]
}