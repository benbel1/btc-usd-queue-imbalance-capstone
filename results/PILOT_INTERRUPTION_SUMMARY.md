# Interruption summary

All times UTC. Connection errors recovered automatically; no collector restart was performed. The two previously reported prolonged episodes were approximately Sep 26 23:33–23:41 and Sep 27 12:48–12:52. Exact invalid observation intervals below are derived from observations.csv; monitor.jsonl retains alert/recovery times.

Total invalid seconds: 778; contiguous invalid intervals: 9.

| Start | End (inclusive) | Invalid seconds |
|---|---|---:|
| 2026-09-25T20:45:38+00:00 | 2026-09-25T20:45:38+00:00 | 1 |
| 2026-09-25T22:32:59+00:00 | 2026-09-25T22:33:01+00:00 | 3 |
| 2026-09-26T02:37:40+00:00 | 2026-09-26T02:37:42+00:00 | 3 |
| 2026-09-26T02:58:06+00:00 | 2026-09-26T02:58:08+00:00 | 3 |
| 2026-09-26T03:17:33+00:00 | 2026-09-26T03:17:35+00:00 | 3 |
| 2026-09-26T23:32:54+00:00 | 2026-09-26T23:41:07+00:00 | 494 |
| 2026-09-26T23:56:11+00:00 | 2026-09-26T23:56:23+00:00 | 13 |
| 2026-09-27T12:47:57+00:00 | 2026-09-27T12:52:01+00:00 | 245 |
| 2026-09-27T12:52:09+00:00 | 2026-09-27T12:52:21+00:00 | 13 |

Connection error counts:
- ConnectionClosedError: no close frame received or sent: 4
- ValueError: heartbeat_timeout: 4
- gaierror: [Errno 11001] getaddrinfo failed: 353
