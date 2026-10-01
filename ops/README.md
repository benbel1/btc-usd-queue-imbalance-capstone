# Cloud collection operations — commissioned October 1, 2026

These helpers add operational supervision, integrity checking and backups without changing the hypothesis, predictors, causal sampler, ten-second return target, feature eligibility or evaluation rules. No main-study scoring runs on the collector VM.

## Deployed configuration

- Existing project `PROJECT_ID`, VM `capstone-btc-collector`, zone `us-east1-b`; standard e2-micro and 30 GB Standard Persistent Disk retained. No duplicate VM or extra disk.
- Linux account `capstone`; project `/opt/capstone-btc`; existing `.venv`.
- Collector unit `capstone-btc-collector.service`, enabled at boot; supervisor PID 1519 and collector PID 1522 at commissioning handoff. Collector began `2026-10-01T19:53:38.483943Z`. PIDs will change on hourly segments/restarts.
- Data: project-relative `data/cloud-study-20261002/segment-*/collection/`. Pre-window rows are commissioning only.
- Backup unit `capstone-btc-backup.service`, timer `capstone-btc-backup.timer`, hourly and enabled at boot. Closed segments only; maximum ordinary offsite lag can approach two hours depending on segment/timer alignment. Active-segment raw evidence remains only on the VM until sealing.
- Private Standard bucket `gs://BACKUP_BUCKET`, us-east1, uniform access and public-access prevention. VM identity `BACKUP_SERVICE_ACCOUNT` has bucket-only object creator/viewer roles; no downloadable key, no delete permission or project-wide role.

## Prospective study

See `study-window.json`, recorded before main-study outcomes. Window: October 2 00:00 UTC inclusive to November 1 00:00 UTC exclusive. Training October 2–19 (18 days); validation October 20–25 (6); test October 26–31 (6). Require at least 95% valid seconds on at least 24 days, including at least five test days. Heavy analysis belongs on another machine after collection. Do not silently shift the window or alter evaluation rules after seeing outcomes.

## Segment lifecycle and integrity

The supervisor locks its data directory and starts a fresh unique segment every hour or after process recovery. It sends SIGINT for graceful collector shutdown and waits for gzip/metadata closure. systemd restarts unexpected supervisor failures, kills orphaned children, and boots the service after a VM restart. Crashed segments are left byte-for-byte intact and receive a separate `recovery-review.json` marker. Incomplete gzip is backed up unchanged with an explicit warning. It is not silently repaired or treated as complete. Research originals and all prior cloud/Windows verification files are retained.

Application logs rotate at 1 MiB with five backups; journal output is rate limited. Raw feed evidence is not rotated away or deleted. At less than 3 GiB available disk, collection closes its segment and waits; the external endpoint becomes unhealthy. Inspect the disk before restarting anything.

## Backups and cost guard

Uploads use `ifGenerationMatch=0`. Existing objects must have matching size and SHA-256 metadata; every newly accepted file is downloaded and hashed before a local verification marker is written. A serialized uploader caps total bucket objects at 10 GiB and warns at 8 GiB. It never deletes local or cloud evidence. The fixed study window, readiness record, exact source hashes and pip freeze were also separately uploaded and download-verified under `run-context/cloud-study-20261002/`.

This is an application storage guard, not a Google billing cap. Free allowances are shared according to Google's billing rules. Hourly uploads/listing are intended to fit ordinary free operation quotas. Unexpected retries, other account usage, outbound transfers or prolonged retention may still incur charges. Public IPv4 charges are separate. 

The 900-second check used 1,966,544 bytes across its collection files, projecting 5.27 GiB/30 days. The first one-minute snapshot-heavy check projected much more. Market activity and reconnect snapshots vary, so this is not a capacity guarantee. The updated 10 GiB cap exceeds this projection, but growth is variable; resolve any 8 GiB warning rather than deleting raw evidence. With the cap reached, collection continues on the VM but new backups stop. Review storage requirements before increasing the cap.

## External monitoring

`/healthz` on port 8080 returns only a small health/reason JSON response. Firewall `capstone-allow-uptime-health` permits the 27 Google US uptime-check IPs observed at setup, and only on the existing VM tag. No public data browsing endpoint exists. Revisit Google's checker IP list if the service changes it.

Uptime check `UPTIME_CHECK_ID` checks the GCE instance identity from Iowa, Oregon and Virginia every minute; it follows the instance instead of a hardcoded ephemeral address. Alert policy `FAILURE_ALERT_POLICY_ID` emails `COLLECTOR_ALERT_EMAIL` when at least two locations fail for two minutes. Local health fails after valid observations exceed 60 seconds old, when backup status is unhealthy or older than two hours, or when disk space is low. VM/process outages fail the external check even if local monitoring cannot run. Delivery is not instantaneous; allow check interval, condition duration and provider latency.

The deliberate initial failure opened an incident at 19:42 UTC and recovered at 19:43:35; email delivery was confirmed. All three external locations passed at 19:55:50 after the reboot and address change. At the planned study end the collector exits; treat the resulting offline alert as expected completion, then disable collection monitoring after confirming final backup. No final model analysis is automatic.

## Commissioning evidence

- Original 60-second smoke: 60 rows, 55 valid, 1,038 raw records; invalid reasons 1 disconnected/no snapshot and 4 heartbeat timeouts. CSV hash and gzip integrity match.
- Preserved interrupted check: 352 rows, 350 valid, 6,188 raw records, interrupted status; CSV hash and gzip integrity match.
- New `data/cloud-commission-20261001T192619Z`: 900 rows, 899 valid, 15,913 messages, no connection errors; checksum/gzip verified. Peak cgroup memory approximately 41 MiB and CPU approximately 8% of one core during the live check.
- Ten original research tests and four operational tests passed. Operational tests cover duplicate rejection, gap/session preservation, explicit invalid missing seconds, incomplete gzip rejection/preservation and valid-versus-invalid/partial-line freshness.
- Graceful restart sealed the interrupted segment and preserved prior sealed-file hashes. Deliberate SIGKILL caused automatic systemd restart into a fresh segment and retained the incomplete gzip with its review marker.
- Approved VM stop/start attached the scoped identity; boot startup and NTP synchronization verified. Ephemeral IP changed, and all external checks recovered.
- Suspending the commissioning collector kept its PID alive but produced 101-second stale valid data and HTTP 503. It was resumed before final deployment.
- Twenty commissioning files and four fixed run-context files were upload/download hash verified. Deliberate crash-damaged evidence was explicitly reported as incomplete, not concealed.

## Safe operations

Use the VM name and IAP:

```sh
gcloud compute ssh capstone@capstone-btc-collector --project=PROJECT_ID --zone=us-east1-b --tunnel-through-iap
sudo systemctl status capstone-btc-collector capstone-btc-backup.timer
```

Inspect `health.json`, `backup-status.json`, segment metadata and `service.log` before intervening. Never launch a second manual collector alongside systemd. Never resume an old output directory. systemd files contain deployment-specific paths; review them before installing elsewhere. The service ends at November 1 00:00 UTC; confirm the final sealed segment is backed up and stop the backup timer/alert policy after collection is finished and evidence is secured.

Assemble only on a separate analysis machine after downloading preserved segments:

```sh
python ops/assemble_segments.py /evidence/cloud-study-20261002/segment-* --out assembled-october --start 2026-10-02T00:00:00+00:00 --end 2026-11-01T00:00:00+00:00
```

The assembler checks recorded hashes/counts, validates gzip, rejects duplicates, namespaces sessions by segment, and emits explicit invalid rows for missing seconds over the entire fixed window, including endpoints. It never imputes prices. Unsealed or incomplete evidence requires explicit review and `--allow-incomplete`; the report records that choice and excludes partial CSV tails. Then use the existing feature builder and main-mode analysis unchanged; inspect coverage before interpreting any model metrics.

The backup cap was increased to 10 GiB with an 8 GiB warning on October 1, 2026. This may exceed the shared Free Tier storage allowance; no additional disk or other service is added. The cap is inclusive: an upload reaching exactly 10 GiB is permitted; exceeding it is rejected. Warning begins at exactly 8 GiB.

## Positive email confirmations

Google Cloud policy START_CONFIRMATION_POLICY_ID confirms formal-start health during October 2 00:05�00:15 UTC; policy DAILY_CONFIRMATION_POLICY_ID confirms current health daily in that UTC window October 3�31 (the previous evening at 8:05 pm New York). Each requires all three existing external check locations to pass over three minutes, samples under two minutes old, and a further one-minute condition duration. Delivery can be later due to metric ingestion and email latency. Only opening notifications are enabled; there are no recovery or recurring-open reminders for these confirmation policies. Google presents these positive confirmations using its incident email format. If unhealthy in the window, no all-clear is sent; the original failure policy remains independent. Time gates prevent these confirmations after the study ends. These are current-health checks, not daily coverage audits or proof the active segment has been backed up.
