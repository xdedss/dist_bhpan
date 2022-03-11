

from . import api, rsa_utils

import time


class ApiManagerException(Exception):
    pass

class WrongPasswordException(ApiManagerException):
    pass

class InvalidRootException(ApiManagerException):
    pass

class NeedReviewException(ApiManagerException):
    pass

class MoveToChildDirectoryException(ApiManagerException):
    pass

class FileMetaData():

    size: int=0
    docid: str=None 
    rev: str=None           # 文件版本ID
    modified: int=0         # 文件版本上传时间，UTC时间，此为上传版本时的服务器时间
    client_mtime: int=0     # 由客户端设置的文件本地修改时间
    name: str=None          # 文件版本上传时文件名称
    editor: str=None        # 文件版本上传编辑者名称
    site: str=None
    tags: list=None

    def __str__(self) -> str:
        res = ''
        for k in ['size', 'docid', 'rev', 'modified', 'client_mtime', 'name', 'editor', 'site', 'tags']:
            res += f'{k}: {getattr(self, k)}\n'
        return res[:-1]


class ResourceInfoData():

    size: int=0
    docid: str=None
    name: str=None
    rev: str=None           # 文件版本ID
    client_mtime: int=0     # 由客户端设置的文件本地修改时间
    modified: int=0         # 文件版本上传时间，UTC时间，此为上传版本时的服务器时间

    def __str__(self) -> str:
        res = ''
        for k in ['size', 'docid', 'rev', 'modified', 'client_mtime', 'name']:
            res += f'{k}: {getattr(self, k)}\n'
        return res[:-1]


class LinkInfoData():

    link: str = None
    password: str = None
    perm: int = None
    endtime: int = None
    limittimes: int = None
    
    def __str__(self) -> str:
        res = ''
        for k in ['link', 'password', 'perm', 'endtime', 'limittimes']:
            res += f'{k}: {getattr(self, k)}\n'
        return res[:-1]



class ApiManager():

    _tokenid = ''
    _expires = 0

    def __init__(self, host, username, password, pubkey, encrypted=None):
        self.base_url = f'https://{host}:443/api/v1'
        self.host = host
        self._pubkey = pubkey
        self._password = password
        self._username = username
        self._encrypted = encrypted
        assert (password is not None and pubkey is not None) or encrypted is not None
        
        self._check_token()
    
    def _update_token(self):
        # print('update')
        encrypted = self._encrypted
        if (encrypted is None):
            encrypted = rsa_utils.encrypt(self._password, self._pubkey)
            self._encrypted = encrypted
        try:
            r = api.post_json(self._make_url('/auth1/getnew'), {
                "account": self._username,
                "password": encrypted,
            })
        except api.ApiException as e:
            if (e.err is not None and e.err['errcode'] == 401003):
                raise WrongPasswordException(e)
            else:
                raise
        self._tokenid = r['tokenid']
        self._userid = r['userid']
        self._expires = r['expires'] + time.time()

    def _check_token(self):
        if (time.time() > (self._expires - 60)):
            self._update_token()

    # dir/file
    def get_resource_id(self, path: str):
        '''returns None if path does not exist'''
        self._check_token()
        if (path is None or path == ''):
            return None
        try:
            r = api.post_json(self._make_url('/file/getinfobypath'), {
                'namepath': path,
            }, tokenid=self._tokenid)
        except api.ApiException as e:
            if (e.err is not None and (e.err['errcode'] in [404006, 403024])):
                return None
            else:
                raise
        return r['docid']
    
    def get_resource_info_by_path(self, path: str):
        '''returns None if path does not exist'''
        self._check_token()
        if (path is None or path == ''):
            return None
        try:
            r = api.post_json(self._make_url('/file/getinfobypath'), {
                'namepath': path,
            }, tokenid=self._tokenid)
        except api.ApiException as e:
            if (e.err is not None and (e.err['errcode'] in [404006, 403024])):
                return None
            else:
                raise
        res = ResourceInfoData()
        for k in ['size', 'docid', 'rev', 'modified', 'client_mtime', 'name']:
            setattr(res, k, r[k])
        return res

    def get_resource_path(self, docid: str):
        self._check_token()
        r = api.post_json(self._make_url('/file/convertpath'), {
            'docid': docid
        }, tokenid=self._tokenid)
        return r['namepath']

    def get_entrydoc(self):
        self._check_token()
        r = api.post_json(self._make_url('/entrydoc2/get'), {
            "doctype": 1,
        }, tokenid=self._tokenid)
        return r['docinfos']

    def resource_is_file(self, docid: str):
        self._check_token()
        try:
            meta = self.get_file_meta(docid)
        except api.ApiException as e:
            if (e.err is not None and e.err['errcode'] == 403015):
                return False # is directory
            else:
                raise
        return True

    # file attr
    def set_file_attr(self, file_id: str, attr: list):
        self._check_token()
        r = api.post_json(self._make_url('/file/setfilecustomattribute'), {
            "docid": file_id,
            "attribute": attr,
        }, tokenid=self._tokenid)
    
    def get_file_attr(self, file_id: str):
        self._check_token()
        r = api.post_json(self._make_url('/file/getfilecustomattribute'), {
            'docid': file_id,
        }, tokenid=self._tokenid)
        return r
    
    # file tag
    def add_file_tag(self, file_id: str, tag: str):
        self._check_token()
        r = api.post_json(self._make_url('/file/addtag'), {
            'docid': file_id,
            'tag': tag,
        }, tokenid=self._tokenid)
    
    def add_file_tags(self, file_id: str, tags: list):
        self._check_token()
        r = api.post_json(self._make_url('/file/addtags'), {
            'docid': file_id,
            'tags': tags,
        }, tokenid=self._tokenid)
    
    def delete_file_tag(self, file_id: str, tag: str):
        self._check_token()
        r = api.post_json(self._make_url('/file/deletetag'), {
            'docid': file_id,
            'tag': tag,
        }, tokenid=self._tokenid)

    def get_file_tags(self, file_id: str):
        self._check_token()
        r = api.post_json(self._make_url('/file/attribute'), {
            'docid': file_id,
        }, tokenid=self._tokenid)
        return r['tags']

    # file 
    def get_file_meta(self, file_id: str):
        self._check_token()
        r = api.post_json(self._make_url('/file/metadata'), {
            "docid": file_id,
        }, tokenid=self._tokenid)
        
        res = FileMetaData()
        for k in ['size', 'docid', 'rev', 'modified', 'client_mtime', 'name', 'editor', 'site', 'tags']:
            setattr(res, k, r[k])
        return res

    def delete_file(self, file_id: str):
        self._check_token()
        r = api.post_json(self._make_url('/file/delete'), {
            'docid': file_id,
        }, tokenid=self._tokenid)
    
    def upload_file(self, parent_dir_id: str, name: str, content: bytes, check_existence: bool=True, stream_len=None) -> str:
        '''
            upload small files < 5GB, return docid
            pass content=filestream and stream_len=<len> to enable stream upload mode
        '''
        self._check_token()

        if (check_existence):
            parent_dir = self.get_resource_path(parent_dir_id)
            existing_file_id = self.get_resource_id(parent_dir + '/' + name)
            edit_mode = existing_file_id is not None
        else:
            edit_mode = False

        # start upload
        r = api.post_json(self._make_url('/file/osbeginupload'), {
            'docid': existing_file_id if edit_mode else parent_dir_id,
            'length': stream_len if stream_len is not None else len(content),
            'name': None if edit_mode else name,
            'reqmethod': 'PUT',
        }, tokenid=self._tokenid)
        #print(r)

        # put
        headers = dict()
        for header_str in r['authrequest'][2:]:
            sp = header_str.split(': ')
            if (len(sp) == 2):
                headers[sp[0]] = sp[1]
        api.put_file(r['authrequest'][1], headers, content)

        # finish
        r_finish = api.post_json(self._make_url('/file/osendupload'), {
            'docid': r['docid'],
            'rev': r['rev'],
        }, tokenid=self._tokenid)
        #print(r_finish)
        return r['docid']
    
    def download_file(self, file_id: str, stream=False):
        '''
            download as bytes
            if stream=True, return request object, use r.iter_content(block_size) to iterate
        '''
        self._check_token()
        r = api.post_json(self._make_url('/file/osdownload'), {
            'docid': file_id,
            'authtype': 'QUERY_STRING',
        }, tokenid=self._tokenid)
        url = r['authrequest'][1]
        if (stream):
            return api.get_file_stream(url)
        else:
            return api.get_file(url)

    def rename_file(self, file_id: str, new_name: str, rename_on_dup=False) -> str:
        ''' returns new name if rename_on_dup '''
        self._check_token()
        r = api.post_json(self._make_url('/file/rename'), {
            'docid': file_id,
            'name': new_name,
            'ondup': 2 if rename_on_dup else 1,
        }, tokenid=self._tokenid)
        if (rename_on_dup):
            return r['name']
        else:
            return None

    def move_file(self, file_id: str, dest_dir_id: str, rename_on_dup=False, overwrite_on_dup=False) -> str:
        ''' returns new docid. returns (docid, name) if rename_on_dup '''
        self._check_token()
        ondup = 1
        if (rename_on_dup):
            ondup = 2
        elif (overwrite_on_dup):
            ondup = 3
        try:
            r = api.post_json(self._make_url('/file/move'), {
                'docid': file_id,
                'destparent': dest_dir_id,
                'ondup': ondup,
            }, tokenid=self._tokenid)
        except api.ApiException as e:
            if (e.err is not None and (e.err['errcode'] in [403019])):
                raise MoveToChildDirectoryException()
            else:
                raise
        if (ondup == 2):
            return r['docid'], r['name']
        else:
            return r['docid']
    
    def copy_file(self, file_id: str, dest_dir_id: str, rename_on_dup=False, overwrite_on_dup=False) -> str:
        ''' returns new docid. returns (docid, name) if rename_on_dup '''
        self._check_token()
        ondup = 1
        if (rename_on_dup):
            ondup = 2
        elif (overwrite_on_dup):
            ondup = 3
        try:
            r = api.post_json(self._make_url('/file/copy'), {
                'docid': file_id,
                'destparent': dest_dir_id,
                'ondup': ondup,
            }, tokenid=self._tokenid)
        except api.ApiException as e:
            if (e.err is not None and (e.err['errcode'] in [403019])):
                raise MoveToChildDirectoryException()
            else:
                raise
        if (ondup == 2):
            return r['docid'], r['name']
        else:
            return r['docid']

    # dir
    def create_dir(self, parent_dir_id: str, name: str) -> str:
        '''returns docid'''
        self._check_token()
        r = api.post_json(self._make_url('/dir/create'), {
            'docid': parent_dir_id,
            'name': name,
        }, tokenid=self._tokenid)
        return r['docid']
    
    def create_dirs(self, parent_dir_id: str, dirs: str) -> str:
        '''returns docid'''
        self._check_token()
        r = api.post_json(self._make_url('/dir/createmultileveldir'), {
            'docid': parent_dir_id,
            'path': dirs,
        }, tokenid=self._tokenid)
        return r['docid']
    
    def create_dirs_by_path(self, dirs: str) -> str:
        '''use create_dirs to create multilevel dir'''
        self._check_token()
        sp = dirs.strip('/').split('/')
        root_dir_id = self.get_resource_id(sp[0])
        if (root_dir_id is None):
            raise InvalidRootException('root dir does not exist')
        if (len(sp) == 1):
            return root_dir_id
        return self.create_dirs(root_dir_id, '/'.join(sp[1:]))
    
    def delete_dir(self, dir_id: str):
        self._check_token()
        r = api.post_json(self._make_url('/dir/delete'), {
            'docid': dir_id,
        }, tokenid=self._tokenid)
    
    def list_dir(self, dir_id: str, by: str=None, sort: str=None, with_attr: bool=False):
        '''
        by: name/size/time (default:docid)
        
        sort: asc/desc (default:asc)

        return dirs, files
        [
            {
                "docid": "gns://xxx",
                "name": "file1",
                "rev": "F245E03387174B568D4666218555AB2D",
                "size": 32563,
                "modified": 1380502294452719,
                'create_time': 1645363786968509
            }, ...
        ]
        '''
        # ([], 
        # [{
        # 'client_mtime': 1645363797561821, 
        # 'create_time': 1645363786968509, 
        # 'creator': '刘卓然_18376268', 
        # 'csflevel': 5, 
        # 'docid': 'gns://E7CF5FB1AE8447CF85E6CFCBC12717EB/C9215A0A4D6243878FA8CDB1CFC02989/669D9B87BF964B3381000FC9C7566776', 
        # 'duedate': -1, 
        # 'editor': '刘卓然_18376268', 
        # 'modified': 1645363797561821, 
        # 'name': 'test2.txt', 
        # 'rev': '5D545BB6CBB04EC88EC31A3EE6A93550', 
        # 'size': 4
        # }]
        # )
        self._check_token()
        d = {
            'docid': dir_id,
            'attr': 'true' if with_attr else 'false',
        }
        if (by is not None):
            d['by'] = by
        if (sort is not None):
            d['sort'] = sort
        r = api.post_json(self._make_url('/dir/list'), d, tokenid=self._tokenid)
        return r['dirs'], r['files']


    # share
    def get_link(self, docid: str) -> LinkInfoData:
        '''returns None if no opened link'''
        self._check_token()
        r = api.post_json(self._make_url('/link/getdetail'), {
            'docid': docid,
        }, tokenid=self._tokenid)
        if (r['link'] == ''):
            return None
        res = LinkInfoData()
        res.link = r['link']
        res.password = r['password']
        res.endtime = r['endtime']
        res.perm = r['perm']
        res.limittimes = r['limittimes']
        return res

    def create_link(self, docid: str, end_time: int=None, limit_times: int=-1,  
        enable_pass=False, allow_view=True, allow_download=True, allow_upload=False) -> LinkInfoData:
        if (allow_download):
            allow_view = True
        perm_int = 1 * allow_view + 2 * allow_download + 4 * allow_upload
        
        self._check_token()
        d = {
            'docid': docid,
            'open': enable_pass,
            'limittimes': limit_times,
            'perm': perm_int,
        }
        if (end_time is not None):
            d['endtime'] = end_time
        r = api.post_json(self._make_url('/link/open'), d, tokenid=self._tokenid)
        if (r['result'] == 0):
            res = LinkInfoData()
            res.link = r['link']
            res.password = r['password']
            res.endtime = r['endtime']
            res.perm = r['perm']
            res.limittimes = r['limittimes']
            return res
        else:
            raise NeedReviewException()
        
    def modify_link(self, docid: str, end_time: int, limit_times: int=-1, 
        enable_pass=False, allow_view=True, allow_download=True, allow_upload=False) -> LinkInfoData:
        if (allow_download):
            allow_view = True
        perm_int = 1 * allow_view + 2 * allow_download + 4 * allow_upload
        
        self._check_token()
        r = api.post_json(self._make_url('/link/set'), {
            'docid': docid,
            'open': enable_pass,
            'limittimes': limit_times,
            'endtime': end_time,
            'perm': perm_int,
        }, tokenid=self._tokenid)
        if (r['result'] == 0):
            res = LinkInfoData()
            res.link = r['link']
            res.password = r['password']
            res.endtime = r['endtime']
            res.perm = r['perm']
            res.limittimes = r['limittimes']
            return res
        else:
            raise NeedReviewException()
    
    def delete_link(self, docid: str):
        self._check_token()
        r = api.post_json(self._make_url('/link/close'), {
            'docid': docid,
        }, tokenid=self._tokenid)







    def _make_url(self, dir: str):
        if (not dir.startswith('/')):
            dir = '/' + dir
        return self.base_url + dir







class ApiLinkManager():

    name: str = None
    size: int = None
    docid: str = None
    link_info: LinkInfoData = None

    def __init__(self, host: str, link_id: str, password: str=None):
        self.base_url = f'https://{host}:443/api/v1'
        self.host = host
        self.link_info = LinkInfoData()
        self.link_info.link = link_id
        self.link_info.password = password
        
        # get link info
        r = api.post_json(self._make_url('/link/get'), {
            'link': self.link_info.link,
            'password': self.link_info.password,
        })
        self.name = r['name']
        self.size = r['size']
        self.docid = r['docid']
        self.link_info.perm = r['perm']
        self.link_info.endtime = r['endtime']
    
    def list_dir(self, dir_id: str=None, by: str=None, sort: str=None, with_attr: bool=False):
        '''
        by: name/size/time (default:docid)
        
        sort: asc/desc (default:asc)
        '''
        if (dir_id is None):
            dir_id = self.docid
        d = {
            'link': self.link_info.link,
            'password': self.link_info.password,
            'docid': dir_id,
        }
        if (by is not None):
            d['by'] = by
        if (sort is not None):
            d['sort'] = sort
        r = api.post_json(self._make_url('/link/listdir'), d)
        return r['dirs'], r['files']






    
    def _make_url(self, dir: str):
        if (not dir.startswith('/')):
            dir = '/' + dir
        return self.base_url + dir


