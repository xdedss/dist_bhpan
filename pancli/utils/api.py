

import requests
import json

class ApiException(Exception):

    def __init__(self, err, *args: object) -> None:
        super().__init__(*args)
        self.err = err


def post_json(url: str, json_obj, tokenid: str=None):
    j = json.dumps(json_obj)
    headers = {
        'Content-Type': 'application/json',
    }
    if (tokenid is not None):
        headers['Authorization'] = 'Bearer ' + tokenid
    for retry in range(10):
        r = requests.post(url, headers=headers, data=j)
        if (r.status_code != 503):
            break
        else:
            print('503 server busy, retry:', retry+1)
    if (r.status_code != 200):
        j = None
        try:
            j = r.json()
        except:
            pass
        raise ApiException(j, 'api returned HTTP %s\n%s' % (r.status_code, r.text))
    if (r.text == ''):
        return None
    res = r.json()
    return res


def put_file(url: str, headers: dict, content: bytes):
    r = requests.put(url, headers=headers, data=content)

def put_file_stream(url: str, headers: dict, content_stream):
    r = requests.put(url, headers=headers, data=content_stream)


def get_file(url: str):
    r = requests.get(url)
    return r.content

def get_file_stream(url: str):
    r = requests.get(url, stream=True)
    return r

