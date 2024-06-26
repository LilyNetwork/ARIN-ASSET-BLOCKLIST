import requests
import json
import yaml
import ipaddress
import sys
import os
from pathlib import Path
import subprocess
import copy
import xmltodict

as_set_dst = os.environ["AS_SET_DST"]
apikey = os.environ["ARIN_APIKEY"]
blockfile = os.environ["BLOCKLIST_FILE"]

dst_cache_file = Path("cache/dst_cache.json")

dst_url = f"https://reg.arin.net/rest/irr/as-set/{as_set_dst}?apikey={apikey}"

headers = {
  'Content-Type': 'application/xml',
  'Accept': 'application/xml'
}

def extract_member(base_json):
    #自原始JSON中取出AS-SET成員
    base_json = base_json['asSet']['members']['member']
    for i in range(len(base_json)):
        base_json[i] = base_json[i]['@name']
    return sorted(list(base_json))
def getblocked_member(filename):
    #從json文件取得已經被阻擋的AS
    with open(filename, "r") as f:
        blocked_member = json.load(f)
        f.close()
    blocked_members = [None] * len(blocked_member)
    for i in range(len(blocked_member)):
        blocked_members[i] = "AS" + str(blocked_member[i]['AS'])
    return sorted(list(blocked_members))
def turn2xml(strin):
    strout = {}
    strout['@name'] = strin
    return strout
def pack_member(base_json,member_list):
    #覆蓋AS-SET成員
    base_json['asSet']['members']['member'] = list(map(turn2xml,sorted(set(member_list))))
    return base_json

#SRC AS BLOCK LIST 取得
src_as = getblocked_member(blockfile)

#DST AS-SET 取得
if dst_cache_file.is_file():
    print("Previous dst_cache_file found")
    dst_json = json.loads(open(dst_cache_file).read())
else:
    print("Previous dst_cache_file not found, download from " + dst_url)
    dst_json = xmltodict.parse(requests.request("GET", dst_url, headers=headers).text)
dst_asset = extract_member(dst_json)


new_member_add = list(set(src_as) - set(dst_asset))
new_member_remove = list(set(dst_asset) - set(src_as))

if dst_asset != src_as:
    payload = xmltodict.unparse(pack_member(dst_json,src_as)).replace("\n","")
    response = requests.request("PUT", dst_url, headers=headers, data=payload)
    response.raise_for_status()
    dst_json_new = xmltodict.parse(response.text)
    print("updated:",as_set_dst)
    print("old members:",dst_asset)
    print("new members added:",new_member_add)
    print("old members removed:",new_member_remove)
else:
    dst_json_new = dst_json
    print("same, no update:",as_set_dst)

open(dst_cache_file,"w").write(json.dumps(dst_json_new))