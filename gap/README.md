<!-- ai-generated: 100% - Codex measured a real downstream latency toxic and interpreted both independent percentiles. -->

# Why the client and server disagree

On 2026-10-10, checker 0.8.1, login `konradxxx777`, the final gap experiment used
Toxiproxy 2.12.0, proxy `svcdesk`, listening on `0.0.0.0:8666` and forwarding
to `svcdesk:8080`. A downstream latency toxic with toxicity 1, latency 500 ms
and jitter 0 ms delayed responses outside the application. Both configuration
objects were created through the actual Toxiproxy HTTP API, not invented in JSON.

Command from the repository root on Docker Desktop:

```sh
docker compose --profile gap up -d svcdesk kb-index toxiproxy
python3 gap/setup.py
./itsmlab.sh load 3 --base-url http://host.docker.internal:8666 --service-url kb-index=http://host.docker.internal:8081
```

After the 5-second warm-up, the published open-loop load ran for 60 seconds
at 40 requests/s over 64 connections. The client saw 2,380 completed responses
(2,371 HTTP 200 and 9 HTTP 502). Its p50 was 528.0 ms and p99 was 632.1 ms;
the server's histogram p99 over that same run's increments was 124.3 ms.
The directly measured upstream p99 was 123.1 ms. Numbers recorded in `gap.json`
are in seconds, rounded to the precision printed by `load`:
0.6321 − 0.1243 = 0.5078 s, or 507.8 ms.

The middleware timer starts and stops inside svcdesk and includes awaiting
the real upstream call. It does not include a downstream proxy withholding
an already-produced response. The load generator measures from scheduled
dispatch until receipt, including the proxy, network and any queueing.
Hence the client experiences roughly the injected 500 ms extra even though
the application histogram barely changes. A service-side-only dashboard
would miss this user-visible degradation; pair it with an external probe.

This is a difference of two independently estimated p99s, not the p99 of
per-request client-minus-server differences. Different tail
ordering, the histogram's within-bucket interpolation and network overhead
prevent an exact equality with 500 ms. The observed 507.8 ms is consistent
with the toxic; the checker repeats its own 30-second experiment and accepts
max(15 ms, 30%) variation in the measured gap. We do not subtract the
artificial delay from the service's normal SLO or pretend its timer measured
the client's full experience.

During the final measurement no build, restart, other load or model inference
ran concurrently. An earlier trial overlapped a service rebuild and was
discarded because counter resets invalidate a clean before/after comparison.
The recorded evidence is the subsequent uninterrupted run with the final toxic.

We initially tried 100 ms with 10 ms jitter: three direct repetitions of the
checker's exact 30-second instrument measured gaps 104.637, 105.848 and
104.984 ms, but one full checker run measured 204.7 ms and failed the evidence
comparison. The exact cause of that client-side outlier is not established;
we do not attribute it conclusively to packetisation or edit evidence to fit it.
The final experiment uses a larger, constant intervention within M-30's limits,
removing jitter and making the signal larger relative to scheduling/network
noise. Three independent 30-second checks of 500/0 measured 526.864,
501.217 and 504.315 ms before the recorded full published load. This range is
only about 5% of the imposed signal. Both old successful and failed trials are
reported rather than treating one successful repetition as proof of stability.
The normal histogram still describes the server's distribution; it is not
expected to resolve the artificially delayed client's 632.1 ms p99.

The proxy is only in front of port 8666. Normal port 8080 bypasses this toxic,
and the main checker builds its own isolated proxy for Stretch; it never
trusts a pre-existing local toxic. `setup.py` only updates the lab's named
proxy and named latency toxic, making the experiment repeatable.
