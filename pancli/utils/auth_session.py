
import requests
from .api import post_json, missing_cert
import base64, urllib.parse, re


def follow_redir_until_anyshare(url, session=None, verbose=False, **kwargs):
    if (session is None):
        session = requests
    while True:
        response = session.get(url, allow_redirects=False, **kwargs)
        if response.status_code in (301, 302, 303, 307, 308):
            new_url = response.headers.get('Location')
            
            if (verbose):
                print('redirect', response.status_code, new_url)
            if 'anyshare://' in new_url:
                return response
            url = new_url
        else:
            return response


def extract_login_challenge(html_string):
    challenge_value = re.search(r'"challenge":"(.*?)"', html_string).group(1)
    csrftoken_value = re.search(r'"csrftoken":"(.*?)"', html_string).group(1)
    return challenge_value, csrftoken_value

def extract_code_from_anyshare_url(url):
    pattern = r'code=([^&]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None

# def extract_login_challenge(input_string):
#     pattern = r'login_challenge=([^"]+)'
#     match = re.search(pattern, input_string)
    
#     if match:
#         return match.group(1)
#     else:
#         return None

def get_access_token(base_url: str, username: str, password: str, *, verbose=False):
    '''
    base_url: https://bhpan.buaa.edu.cn:443/
    username: xxxxxxx
    password: rsa encrypted password
    '''

    def verbose_print(*args):
        if (verbose):
            print('[get_access_token]', *args)

    base_url = base_url.strip("/")
    
    session = requests.Session()

    state = urllib.parse.quote(base64.b64encode(b'{"windowId":3}')) # magic
    redir = True


    verbose_print('sending /oauth2/auth')
    verbose_print('')
    r = session.get(f'{base_url}/oauth2/auth?audience=&client_id=0f4bc444-d39a-4945-84a3-023d1f439148&redirect_uri=anyshare%3A%2F%2Foauth2%2Flogin%2Fcallback&response_type=code&state={state}&scope=offline+openid+all&lang=zh-cn&udids=00-50-56-C0-00-01', verify=missing_cert, allow_redirects=redir)

    challenge, csrf_token = extract_login_challenge(r.text)

    verbose_print('challenge', challenge, 'csrf', csrf_token)
    verbose_print('sending /oauth2/signin')

    r = post_json(f'{base_url}/oauth2/signin', {
        "_csrf": csrf_token,
        "challenge": challenge,
        "account": username,
        "password": password,
        "vcode": {
            "id": "",
            "content": ""
        },
        "dualfactorauthinfo": {
            "validcode": {
                "vcode": ""
            },
            "OTP": {
                "OTP": ""
            }
        },
        "remember": False,
        "device": {
            "name": "RichClient",
            "description": "RichClient for windows",
            "client_type": "windows",
            "udids": [
                "00-50-56-C0-00-01"
            ]
        }
    }, session=session)

    verbose_print('following redirect from', r['redirect'])

    r = follow_redir_until_anyshare(r['redirect'], session, verbose=verbose)

    location = r.headers.get('Location')
    verbose_print('got anyshare location:', location)
    code = extract_code_from_anyshare_url(location)
    verbose_print('extracted code:', code)


    
    headers = {
        "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundarywPAfbB36kbRTzgzy",  # Set the content type
        "Authorization": "Basic MGY0YmM0NDQtZDM5YS00OTQ1LTg0YTMtMDIzZDFmNDM5MTQ4OnVOaVU0V0ZUd1FEfjE4T2JHMkU1M2dqN3ot",
    }
    data = (
        "------WebKitFormBoundarywPAfbB36kbRTzgzy\r\n"
        'Content-Disposition: form-data; name="grant_type"\r\n\r\n'
        "authorization_code\r\n"
        "------WebKitFormBoundarywPAfbB36kbRTzgzy\r\n"
        'Content-Disposition: form-data; name="code"\r\n\r\n'
        f"{code}\r\n"
        "------WebKitFormBoundarywPAfbB36kbRTzgzy\r\n"
        'Content-Disposition: form-data; name="redirect_uri"\r\n\r\n'
        "anyshare://oauth2/login/callback\r\n"
        "------WebKitFormBoundarywPAfbB36kbRTzgzy--"
    )
    r = session.post(f'{base_url}/oauth2/token', headers=headers, data=data)
    r_json = r.json()
    verbose_print(r_json)
    return r_json['access_token']
