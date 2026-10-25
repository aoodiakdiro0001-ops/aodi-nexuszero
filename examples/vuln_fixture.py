# Aodı-NexusZero — sentinel fixture with PLANTED vulnerabilities.
# Expected: 10 findings across rules NZ-X01..X10 (used by tests + live demo).
import pickle, subprocess, hashlib, os, random, yaml
import urllib3
API_KEY = "AKIAJ7XAMPLE456ABCD"
password = "hunter2supersecret"


def run(cmd):
    os.system(cmd)                      # NZ-X06
    subprocess.Popen(cmd, shell=True)   # NZ-X05


def deserialize(blob):
    return pickle.loads(blob)           # NZ-X03


def weak_hash(data):
    return hashlib.md5(data).hexdigest()   # NZ-X07


def unsafe_yaml(doc):
    return yaml.load(doc)               # NZ-X04


def fetch(url):
    import requests
    return requests.get(url, verify=False)   # NZ-X08


def query(user):
    sql = f"SELECT * FROM users WHERE name = '{user}'"   # NZ-X09
    return sql


class DebugServer:
    debug = True                        # NZ-X10


def token():
    return random.random()              # NZ-X11


def boom(x):
    return eval("x * 2")               # NZ-X02
