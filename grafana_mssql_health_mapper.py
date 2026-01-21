#!/usr/bin/env python3

import argparse
import sys
import re
import time
import ipaddress
from requests import Session, Request
from requests.exceptions import RequestException

def parse_ports(ports_str):
    """Parse a string of ports with support for ranges."""
    ports = []
    for part in ports_str.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            ports.extend(range(start, end + 1))
        else:
            ports.append(int(part))
    return sorted(set(ports))

def parse_hosts(hosts_str):
    """Parse a string of hosts with support for CIDRs and ranges."""
    hosts = []
    for part in hosts_str.split():
        if "/" in part:  # CIDR notation
            network = ipaddress.ip_network(part, strict=False)
            hosts.extend(str(ip) for ip in network.hosts())
        elif "-" in part:  # Range notation
            match = re.match(r"(\d+\.\d+\.\d+)\.(\d+)-(\d+)", part)
            if match:
                base, start, end = match.groups()
                hosts.extend(f"{base}.{i}" for i in range(int(start), int(end) + 1))
        else:  # Single host or IP
            hosts.append(part)
    return sorted(set(hosts))

def read_targets(file_path):
    """Read targets from a file."""
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def extract_base_url_and_uid(target_url):
    """Extract the base URL and datasource UID from the target URL."""
    match = re.search(r"(https?://[^/]+)/connections/datasources/edit/([a-zA-Z0-9]+)$", target_url)
    if not match:
        print(f"Error: Invalid target URL format: {target_url}", file=sys.stderr)
        sys.exit(1)
    base_url, datasource_uid = match.groups()
    return base_url, datasource_uid

def pretty_print_POST(req):
    """
    Pretty-print a prepared HTTP request.
    """
    if args.debug:
        print('{}\n{}\r\n{}\r\n\r\n{}'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
        ), file=sys.stderr)


def rotate_grafana_session(session, base_url, grafana_session):
    """Rotate the Grafana session token."""
    url = f"{base_url}/api/user/auth-tokens/rotate"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,ru;q=0.8",
        "cache-control": "no-cache",
        "origin": base_url,
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": f"{base_url}/connections/datasources/edit/befy4uj2alreof",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    }
    cookies = {"grafana_session": grafana_session}

    # Prepare the request for debugging
    req = Request('POST', url, headers=headers, cookies=cookies)
    prepared = session.prepare_request(req)
    pretty_print_POST(prepared)

    try:
        response = session.send(prepared)
        if args.debug:
            print(f"DEBUG: Rotate session response status code: {response.status_code}", file=sys.stderr)
            print(f"DEBUG: Rotate session response content: {response.text}", file=sys.stderr)

        if response.status_code == 200:
            # Extract new session cookies from the response
            new_cookies = response.cookies
            new_grafana_session = new_cookies.get("grafana_session")
            if not new_grafana_session:
                raise ValueError("Failed to extract new grafana_session from response.")
            return new_grafana_session
        else:
            raise ValueError(f"Session rotation failed: {response.text}")
    except Exception as e:
        print(f"Error rotating session: {e}", file=sys.stderr)
        sys.exit(1)



def update_datasource(session, api_url, grafana_session, version, uid, host, port):
    """Send an update request to the Grafana datasource."""
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,ru;q=0.8",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": api_url,
        "referer": api_url,
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "x-grafana-device-id": "acd5ed00133cb2df091d331bc0e1229e",
        "x-grafana-org-id": "1",
    }
    cookies = {"grafana_session": grafana_session}
    payload = {
        "id": 9,
        "uid": uid,
        "orgId": 1,
        "name": "mssql",
        "type": "mssql",
        "typeLogoUrl": "public/app/plugins/datasource/mssql/img/sql_server_logo.svg",
        "access": "proxy",
        "url": f"{host}:{port}",
        "user": "",
        "database": "",
        "basicAuth": False,
        "basicAuthUser": "",
        "withCredentials": False,
        "isDefault": False,
        "jsonData": {
            "authenticationType": "Windows Authentication",
            "connMaxLifetime": 14400,
            "database": "master",
            "maxIdleConns": 100,
            "maxIdleConnsAuto": True,
            "maxOpenConns": 100,
        },
        "secureJsonFields": {},
#        "version": version,
        "readOnly": False,
        "accessControl": {
            "alert.instances.external:read": True,
            "alert.instances.external:write": True,
            "alert.notifications.external:read": True,
            "alert.notifications.external:write": True,
            "alert.rules.external:read": True,
            "alert.rules.external:write": True,
            "datasources.id:read": True,
            "datasources:delete": True,
            "datasources:query": True,
            "datasources:read": True,
            "datasources:write": True,
        },
        "apiVersion": "",
    }

    # Prepare the request for debugging
    req = Request('PUT', api_url, headers=headers, cookies=cookies, json=payload)
    prepared = session.prepare_request(req)
    pretty_print_POST(prepared)

    try:
        response = session.send(prepared)
        if args.debug:
            print(f"DEBUG: Update response status code: {response.status_code}", file=sys.stderr)
            print(f"DEBUG: Update response content: {response.text}", file=sys.stderr)

        if response.status_code == 200:
            return True, response.json()
        else:
            print(f"Update failed: {response.text}", file=sys.stderr)
            return False, response.text
    except RequestException as e:
        print(f"Update request failed: {e}", file=sys.stderr)
        return False, str(e)

def check_datasource_health(session, api_url, grafana_session, uid, host, port):
    """Send a health check request to the Grafana datasource."""
    url = f"{api_url}/health"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,ru;q=0.8",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": api_url,
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "x-datasource-uid": uid,
        "x-grafana-device-id": "acd5ed00133cb2df091d331bc0e1229e",
        "x-grafana-nocache": "true",
        "x-grafana-org-id": "1",
        "x-plugin-id": "mssql",
    }
    cookies = {"grafana_session": grafana_session}
    start_time = time.time()

    # Prepare the request for debugging
    req = Request('GET', url, headers=headers, cookies=cookies)
    prepared = session.prepare_request(req)
    pretty_print_POST(prepared)

    try:
        response = session.send(prepared, timeout=2)
        elapsed_time = time.time() - start_time
        if args.debug:
            print(f"DEBUG: Health check response status code: {response.status_code}", file=sys.stderr)
            print(f"DEBUG: Health check response content: {response.text}", file=sys.stderr)

        # Analyze the response
        if "invalid packet size" in response.text:
            return "open", response.text
        elif "failed to connect to server" in response.text:
            if elapsed_time < 1:
                return "closed", response.text
            elif elapsed_time >= 2:
                return "filtered", response.text
        else:
            return "unknown", response.text
    except RequestException as e:
        elapsed_time = time.time() - start_time
        if elapsed_time < 1:
            return "closed", str(e)
        elif elapsed_time >= 2:
            return "filtered", str(e)
        else:
            return "unknown", str(e)

def main():
    global args
    parser = argparse.ArgumentParser(description="Check availability of Grafana datasources.", add_help=False)
    parser.add_argument("-t", "--target", required=True, help="Target URL")
    parser.add_argument("-l", "--list", help="File with list of targets")
    parser.add_argument("-H", "--hosts", help="List of IPs/FQDNs in nmap format")
    parser.add_argument("-p", "--ports", required=True, help="List of ports to check")
    parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    parser.add_argument("-s", "--session", required=True, help="Grafana session cookie")
    parser.add_argument("-v", "--version", type=int, default=731, help="Start value of version iterator")
    parser.add_argument("-d", "--debug", type=int, default=0, choices=[0, 1], help="Debug mode")
    parser.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()

    # Parse hosts and ports
    if args.hosts:
        hosts = parse_hosts(args.hosts)
    elif args.list:
        hosts = read_targets(args.list)
    else:
        print("Error: Either --hosts or --list must be provided.", file=sys.stderr)
        sys.exit(1)

    ports = parse_ports(args.ports)

    # Extract base URL and datasource UID
    base_url, datasource_uid = extract_base_url_and_uid(args.target)


    # Construct the API endpoint for updating the datasource
    api_url = f"{base_url}/api/datasources/uid/{datasource_uid}"

    # Open output file
    if args.output == "-":
        output_file = sys.stdout
    else:
        output_file = open(args.output, "w")

    # Initialize session
    session = Session()


    i = 0
    # Iterate over hosts and ports
    version_iterator = args.version
    for port in ports:
        for host in hosts:
            i = i + 1
            if i % 10 == 0:
                args.session = rotate_grafana_session(session, base_url, args.session)
            if args.debug:
                print(f"Checking {host}:{port}", file=sys.stderr)
            success, _ = update_datasource(
                session, api_url, args.session, version_iterator, datasource_uid, host, port
            )
            if success:
                status, response = check_datasource_health(
                    session, api_url, args.session, datasource_uid, host, port
                )
                print(f"{host}:{port}/{status}", file=output_file)
                if args.debug:
                    print(f"Response: {response}", file=sys.stderr)
            else:
                print(f"{host}:{port}/skipped", file=output_file)
            version_iterator += 1
            output_file.flush()

    # Close output file
    if args.output != "-":
        output_file.close()

if __name__ == "__main__":
    main()