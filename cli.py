import requests, json, sys, os
from collections import defaultdict
from argparse import ArgumentParser

def send_request(filename, account_id, region):
  with open(filename, "rb") as fd:
    payload = {"plan": fd.read()}
    if account_id:
      payload["account_id"] = account_id
    if region:
      payload["region"] = region
    response = requests.post("https://api.semdiff.io/analyze/perms/direct", files = payload)
    if response.status_code != 200:
      print("Error: invalid response from api.semdiff.io:", response.status_code, file = sys.stderr)
      sys.exit(-1)
    return json.loads(response.content)

def collect_diff_items(diff_items):
  collected = defaultdict(lambda: defaultdict(list))
  for item in diff_items:
    principal = item["principal"]
    resource_arn = item["resource_arn"]
    collected[principal][resource_arn] += [item["action"]]
  return collected

def print_diff(diff):
  for user in diff.keys():
    yield " principal: " + user
    all_resources = diff[user].keys()
    for resource_arn in all_resources:
      yield "   resource: " + resource_arn
      for action in diff[user][resource_arn]:
        yield "      " + action

def response_to_md(response):
  granted = collect_diff_items(response["granted"])
  revoked = collect_diff_items(response["revoked"])
  lines = []
  if (len(granted.keys()) == 0 and len(revoked.keys()) == 0):
    lines.append("This PR doesn't change any permissions")
  else:
    if (len(granted.keys()) > 0):
      lines.append("This PR grants the following NEW permissions:")
      lines.extend(print_diff(granted))
    if (len(revoked.keys()) > 0):
      lines.append("This PR revokes the following permissions:")
      lines.extend(print_diff(revoked))
  return os.linesep.join(lines)

if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("-f", "--format", default = "text", choices = ["text", "json"], help = "Output format, default: text")
  parser.add_argument("-a", "--account_id", help = "AWS account id (e.g. 123456789012). Used to generate ARNs if they are missing from the plan file")
  parser.add_argument("-r", "--region", help = "AWS region (e.g. eu-west-2). Used to generate ARNs if they are missing from the plan file")
  parser.add_argument("filename", help = "The terraform plan file in json format. Can be generated with \"terraform show -json\"")
  args = parser.parse_args()
  response = send_request(args.filename, args.account_id, args.region)
  if args.format == "json":
    print(json.dumps(response, indent = 2))
  else:
    print(response_to_md(response))
