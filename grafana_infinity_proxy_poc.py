import argparse
import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

# Command-line argument parsing
parser = argparse.ArgumentParser(description="Grafana Infinity Datasource Proxy")
parser.add_argument("--grafana-url", required=True, help="URL of the Grafana instance")
parser.add_argument("--token", required=True, help="Bearer token for Grafana API")
parser.add_argument("--proxy-host", default="localhost", help="Proxy host (default: localhost)")
parser.add_argument("--proxy-port", type=int, default=8080, help="Proxy port (default: 8080)")
args = parser.parse_args()

# Constants
GRAFANA_URL = args.grafana_url.rstrip("/")
BEARER_TOKEN = args.token
PROXY_HOST = args.proxy_host
PROXY_PORT = args.proxy_port
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}", "Content-Type": "application/json"}

# Function to check if the Infinity datasource exists
def check_infinity_datasource():
    try:
        response = requests.get(f"{GRAFANA_URL}/api/datasources", headers=HEADERS)
        response.raise_for_status()
        datasources = response.json()
        for ds in datasources:
            if ds["type"] == "yesoreyeram-infinity-datasource" and ds["name"] == 'prxoyds':
                print(ds)
                return ds["uid"], ds["id"]
        raise ValueError("Infinity datasource not found in Grafana.")
    except Exception as e:
        print(f"Error checking Infinity datasource: {e}")
        exit(1)

# Get Infinity datasource UID and ID
DATASOURCE_UID, DATASOURCE_ID = check_infinity_datasource()

# Function to update the Infinity datasource
def update_infinity_datasource(url, params):
    try:
        # Fetch the current datasource settings
        response = requests.get(f"{GRAFANA_URL}/api/datasources/uid/{DATASOURCE_UID}", headers=HEADERS)
        response.raise_for_status()
        datasource = response.json()

        # Update the URL and parameters
        datasource["url"] = url
        datasource["jsonData"]["customHealthCheckEnabled"] = True
        datasource["jsonData"]["customHealthCheckUrl"] = url
        datasource["jsonData"]["params"] = params

        # Send the updated datasource back to Grafana
        update_response = requests.put(
            f"{GRAFANA_URL}/api/datasources/{DATASOURCE_ID}",
            headers=HEADERS,
            json=datasource
        )
        update_response.raise_for_status()
        print("Infinity datasource updated successfully.")
    except Exception as e:
        print(f"Error updating Infinity datasource: {e}")

# Function to query the Infinity datasource
def query_infinity_datasource():
    try:

        # Construct the query payload with all required fields
        query_payload = {
            "queries": [
                {
                    "refId": "A",
                    "datasource": {
                        "type": "yesoreyeram-infinity-datasource",
                        "uid": DATASOURCE_UID
                    },
                    "type": "html",
                    "source": "url",
                    "format": "table",
                    "url": "",
                    "url_options": {
                        "method": "GET",
                        "data": "",
                        "body_type": "",
                        "body_content_type": "",
                        "body_graphql_query": "",
                        "body_graphql_variables": ""
                    },
                    "root_selector": "",
                    "columns": [],
                    "filters": [],
                    "global_query_id": "",
                    "datasourceId": DATASOURCE_ID,
                    "intervalMs": 5000,
                    "maxDataPoints": 568
                }
            ],
            "from": "now-6h",
            "to": "now"
        }


        # Query the datasource using the Grafana API
        response = requests.post(
            f"{GRAFANA_URL}/api/ds/query",
            headers=HEADERS,
            json=query_payload
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error querying Infinity datasource: {e}")
        return {"error": str(e)}

# Proxy server handler
class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse the incoming request (e.g., extract URL and parameters)
            url = self.path[0:]  # Remove leading '/'
            params = dict(param.split("=") for param in url.split("&") if "=" in param)

            print(url)

            # Update the Infinity datasource
            update_infinity_datasource(url, params)

            # Query the updated datasource
            grafana_response = query_infinity_datasource()

            print(grafana_response)

            grafana_response=grafana_response["results"]["A"]["frames"][0]["schema"]["meta"]["custom"]["data"]


            print(grafana_response)


            # Send the response back to the client
            self.send_response(200)
#            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(str.encode(grafana_response))
        except Exception as e:
            self.send_response(500)
#            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

# Start the proxy server
def run_proxy_server():
    server_address = (PROXY_HOST, PROXY_PORT)
    httpd = HTTPServer(server_address, ProxyHandler)
    print(f"Starting proxy server on {PROXY_HOST}:{PROXY_PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Proxy server stopped.")

if __name__ == "__main__":
    run_proxy_server()