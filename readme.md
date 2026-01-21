# I JUST WANTED TO… GRAFUNA RED TEAM

Observability is about visibility.  
Visibility works both ways.
If you can see it, someone else can too.

This repo contains the public bits of my recent talk: slides + small helper scripts.  
Everything here is **read-only / educational** unless you decide to be creative (don’t).

## Artifacts

- Slides (PDF): **Gordey - Grafana - ZN2025.pdf** 
- Script: **grafana_inventory.py** 
- Script: **grafana\_mssql\_health_mapper.py** 
- Script: **grafana\_infinity\_proxy_poc.py** 

## What the talk is about

Cloud-native observability stack (Prometheus / Grafana / friends) is:<br>
- everywhere,<br>
- powerful,<br>
- and often shipped with “it’s fine” defaults.<br>

The paradox: we built monitoring to **reduce** incidents, and accidentally created a new attack surface to **route** them.

Covered topics (high level):<br>
- `/metrics`, `/debug`, `/pprof`, “helpful” APIs, and why they are *helpful* to the wrong people.<br>
- Grafana as a **control plane** (dashboards, plugins, datasources, users/roles).<br>
- Misconfigs at scale, and why “internal service” is a fantasy with good marketing.<br>
- Red team checklist + blue team mitigations (aka “bind to localhost and pray”).

**If you observe long enough, observability will gaze back into you.<br>
(And it will file a ticket.)**

# Ultrasonic Vibecoding Session 

I made these during an ultrafast vibecoding session.
They work just enough to be dangerous, and not enough to be proud.

If you want to use them, you have to fix them.<br>
Fixing them is the CAPTCHA.<br>
Passing the CAPTCHA proves you are (probably) a human.<br>

# Requirements

- Python 3.8+
- `requests`

```bash
pip install requests
```


## `grafana_inventory.py`

A minimal inventory collector for Grafana:
- pulls metadata (health, users, datasources, plugins, dashboards/folders)
- outputs a Markdown report
- **does not write** to Grafana (GET-only)
- redacts `user:pass@host` in URLs

### Usage

```bash
python3 grafana_inventory.py \
  --base-url "https://grafana.example.com" \
  --output grafana_inventory.md \
  --api-key "<TOKEN>"
```

You can also provide the token via env:

```bash
export GRAFANA_API_KEY="<TOKEN>"
python3 grafana_inventory.py --base-url "https://grafana.example.com"
```

Notes:

* Works with subpaths (`https://host/grafana`).
* Running without a token is allowed (and sometimes informative): you’ll simply inventory what anonymous users can see.
* Output is intentionally boring. Boring is good. Boring is secure. (Usually.)
* 
![grafana_inventory output](grafana_inventory.jpg)


## `grafana_mssql_health_mapper.py` 

**What it is:**  
A Grafana **MSSQL datasource** abuse-utility that turns `/api/datasources/.../health` into a crude **connectivity probe**.

**What it does (in human terms):**
- Takes a Grafana MSSQL datasource<br>
- Rewrites its target server to `host:port` (over and over)<br>
- Calls the datasource **health check**<br>
- Infers “something answers / nothing answers / something times out” from the result text + timing<br>
- Rotates auth token periodically because the platform gets bored watching you do this<br>

**Why it exists:**  
Because “internal-only” is a bedtime story, and datasources are often a programmable network boundary with a GUI.

**What it is NOT:**<br>
- Not a scanner<br>
- Not reliable truth<br>
- Not subtle<br>
- Not production anything<br>

**Inputs / knobs (expected):**<br>
- Grafana base URL<br>
- A session/API token<br>
- Datasource ID (MSSQL)<br>
- Hosts (CIDR/ranges)<br>
- Ports list<br>
- Timeouts / concurrency-ish behavior (depending on your edits)<br>

**Outputs:**<br>
- A stream of “maybe open / maybe closed / maybe filtered / maybe Grafana hates you”<br>
- You’ll want to pipe it into something structured if you plan to pretend it’s science

**Known sins:**<br>
- Error-string parsing as a “protocol”<br>
- Heuristics that will lie when latency, proxies, or rate limits decide to cosplay as physics<br>
- If you run it too hard, Grafana starts doing Grafana things (tokens, throttling, sadness)<br>

**Fix-me CAPTCHA ideas:**<br>
- Add JSONL output (`host`, `port`, `status`, `latency_ms`, `raw_error`)<br>
- Make status taxonomy explicit (no “maybe”)<br>
- Add backoff / rate limiting<br>
- Make datasource selection safer (no hardcoded ID/name assumptions)<br>
- Add dry-run mode (print planned mutations without touching Grafana)<br>

---

## 2) `grafana_infinity_proxy_poc.py` (aka `grafproxy.py`)

**What it is:**  <br>
A local HTTP server that tries to use Grafana’s **Infinity datasource** (`yesoreyeram-infinity-datasource`) as a glorified **fetcher/proxy**, mostly to understand how the pipeline behaves.

**What it does (in human terms):**<br>
- Starts a tiny local HTTP listener<br>
- Finds an Infinity datasource (hardcoded naming assumptions)<br>
- Mutates its config/params<br>
- Calls Grafana `/api/ds/query`<br>
- Extracts a chunk from the response and returns it to you<br>

**Why it exists:**  <br>
Because sometimes you don’t need a full exploit chain — you need to understand the **shape of the plumbing**.

**Current status:**  <br>
PoC / unfinished / “works on my machine” energy.
It’s a sketch of an idea, not a tool.

**What it is NOT:**<br>
- Not a secure proxy<br>
- Not a generic SSRF framework<br>
- Not something you expose to the internet unless you enjoy incident response<br>

**Outputs:**<br>
- Whatever the datasource returns, plus whatever you accidentally leak while learning

**Known sins:**<br>
- Hardcoded expectations about datasource name/type<br>
- Minimal validation<br>
- Weak separation between “request path” and “target URL”<br>
- The kind of code that *teaches you* why code reviews exist

**Fix-me CAPTCHA ideas:**<br>
- Make datasource selection explicit (ID via args/env)<br>
- Properly parse and validate requested URLs (allowlist, scheme checks, no surprises)<br>
- Return structured results + errors (no silent swallowing)<br>
- Add logging that helps debugging without leaking secrets<br>
- Add unit tests, just to experience pain in a controlled environment<br>


## Safety / Legal

* Use only on systems you own or have explicit permission to test.
* If you point this at random internet endpoints: congratulations, you became the incident/problem/criminal case.

## Credits

Sergey Gordeychik.

If you found this useful, patch your observability stack. If you found it scary, patch it twice.

## License

Code: MIT 

Slides: CC BY 4.0 

Or pick something else.

