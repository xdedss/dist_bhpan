

from . import utils
from .utils.api_manager import ApiManager
from .utils.api import ApiException
from .utils.local_storage import StoredObject

import argparse

import getpass, sys, os, time

import tqdm, tqdm.utils, prettytable




def process_remote_home(manager: ApiManager, path: str):
    home_alias = 'home'
    if (path == home_alias or path.startswith(home_alias + '/')):
        # replace alias with home folder
        entrydoc = manager.get_entrydoc()
        if (len(entrydoc) < 1):
            print('Unexpected entry doc: ', entrydoc)
        else:
            path = entrydoc[0]['name'] + path[len(home_alias):]
    return path

# def process_remote_home(manager: ApiManager, path: str):
#     if (path.startswith('/')):
#         path = path[1:]
#     else:
#         entrydoc = manager.get_entrydoc()
#         if (len(entrydoc) < 1):
#             print('Unexpected entry doc: ', entrydoc)
#         path = entrydoc[0]['name'] + '/' + path
#     return path

def sizeof_fmt(num, suffix=""):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"




# upload entry point
def upload_file(manager: ApiManager, local_path, remote_dir, rename=None, sleep_interval=0.5, allow_recurse=False):
    remote_dir = remote_dir.strip('/')
    local_path = os.path.normpath(local_path)
    remote_name = rename if rename is not None else os.path.split(os.path.abspath(local_path))[1]
    #print(local_path, '->', remote_dir, 'as', remote_name)
    if (not os.path.exists(local_path)):
        print('no such file ', local_path)
        return
    if (os.path.isfile(local_path)):
        # simply upload it
        print(f'{local_path}: ', end='')
        use_stream = False
        file_size = os.path.getsize(local_path)
        print(f'{file_size}({sizeof_fmt(file_size)})')

        if (file_size > (1024 * 1024)):
            use_stream = True
        
        dir_id = manager.create_dirs_by_path(remote_dir)

        if (use_stream):
            with open(local_path, 'rb') as f:
                with tqdm.tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                    wrapped_file = tqdm.utils.CallbackIOWrapper(t.update, f, "read")
                    manager.upload_file(dir_id, remote_name, wrapped_file, stream_len=file_size)
        else:
            with open(local_path, 'rb') as f:
                f_bytes = f.read()
            print('uploading...')
            manager.upload_file(dir_id, remote_name, f_bytes)
    else:
        # dir, recurse
        if (allow_recurse):
            ls = os.listdir(local_path)
            full_path_remote = remote_dir + '/' + remote_name
            for p in ls:
                full_path = os.path.join(local_path, p)
                time.sleep(sleep_interval) # slower
                upload_file(manager, full_path, full_path_remote, sleep_interval=sleep_interval, allow_recurse=allow_recurse)
            if (len(ls) == 0):
                # empty dir
                manager.create_dirs_by_path(full_path_remote)
        else:
            print(f'{local_path} is a directory, use -r for recursion')


def upload_file_single(manager: ApiManager, local_path, remote_dir, rename=None):

    if (not os.path.exists(local_path)):
        print('no such file ', local_path)
        return
    if (not os.path.isfile(local_path)):
        print('can not upload directory ')
        return

    print('checking file size: ', end='')
    use_stream = False
    file_size = os.path.getsize(local_path)
    print(f'{file_size}({sizeof_fmt(file_size)})')

    if (file_size > (1024 * 1024)):
        print('large file, using stream')
        use_stream = True
    
    print('creating remote dir: ', end='')
    dir_id = manager.create_dirs_by_path(remote_dir)
    print(dir_id)

    remote_file_name = rename if rename is not None else os.path.split(local_path)[1]
    if (use_stream):
        with open(local_path, 'rb') as f:
            with tqdm.tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                wrapped_file = tqdm.utils.CallbackIOWrapper(t.update, f, "read")
                manager.upload_file(dir_id, remote_file_name, wrapped_file, stream_len=file_size)
    else:
        print('reading file')
        with open(local_path, 'rb') as f:
            f_bytes = f.read()
        print('uploading...')
        manager.upload_file(dir_id, remote_file_name, f_bytes)
    print('done')



# download entry point
def download_file(manager: ApiManager, remote_path, local_dir, rename=None, sleep_interval=0.5, allow_recurse=False):
    remote_path = remote_path.strip('/')
    local_name = rename if rename is not None else os.path.split(remote_path)[1]

    file_info = manager.get_resource_info_by_path(remote_path)
    if (file_info is None):
        print('no such file ', remote_path)
        return
    elif (file_info.size != -1):
        # file, download it
        print(f'{remote_path}: {file_info.size}({sizeof_fmt(file_info.size)})')
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, local_name), 'wb') as f:
            with tqdm.tqdm(total=file_info.size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                download_iter = manager.download_file(file_info.docid, stream=True)
                for data in download_iter.iter_content(1024):
                    t.update(len(data))
                    f.write(data)
    else:
        # dir, recurse
        if (allow_recurse):
            dirs, files = manager.list_dir(file_info.docid, by='name')
            full_path_local = os.path.join(local_dir, local_name)
            for d in dirs:
                time.sleep(sleep_interval)
                download_file(manager, remote_path + '/' + d['name'], full_path_local, 
                    sleep_interval=sleep_interval, allow_recurse=allow_recurse)
            for d in files:
                time.sleep(sleep_interval)
                download_file(manager, remote_path + '/' + d['name'], full_path_local, 
                    sleep_interval=sleep_interval, allow_recurse=allow_recurse)
        else:
            print(f'{remote_path} is a directory, use -r for recursion')
            return



def download_file_single(manager: ApiManager, remote_path, local_dir, rename=None):

    print('checking remote file')
    file_id = manager.get_resource_id(remote_path)
    if (file_id is None):
        print('no such file: ', remote_path)
        return
    try:
        file_meta = manager.get_file_meta(file_id)
        print('file size: ', file_meta.size)
    except ApiException as e:
        if (e.err is not None and e.err['errcode'] == 403015):
            # is dir
            print('can not download directory (yet)')
        else:
            raise

    else:
        print('creating local dir', local_dir)
        os.makedirs(local_dir, exist_ok=True)

        local_file_name = rename if rename is not None else os.path.split(remote_path)[-1]
        with open(os.path.join(local_dir, local_file_name), 'wb') as f:
            with tqdm.tqdm(total=file_meta.size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                download_iter = manager.download_file(file_id, stream=True)
                for data in download_iter.iter_content(1024):
                    t.update(len(data))
                    f.write(data)
        print('done')




def show_file_info(manager: ApiManager, remote_path, readable=False):

    file_info = manager.get_resource_info_by_path(remote_path)
    if (file_info is None):
        print('no such file', remote_path)
        return
    elif (file_info.size != -1):
        meta = manager.get_file_meta(file_info.docid)
        print(remote_path)
        print('  size:    ', sizeof_fmt(meta.size) if readable else meta.size)
        print('  docid:   ', meta.docid)
        print('  rev:     ', meta.rev)
        print('  editor:  ', meta.editor)
        print('  modified:', time.strftime("%Y%m%d %H:%M:%S", time.localtime(meta.modified / 1000000)))
        print('  tags:    ', meta.tags)
    else:
        # is dir?
        print('it\'s a directory')

# ls entry point
def list_dir(manager: ApiManager, remote_dir, readable=False):

    print('checking', remote_dir)
    
    dir_info = manager.get_resource_info_by_path(remote_dir)
    if (dir_info is None):
        print('no such directory or file', remote_dir)
        return False
    elif (dir_info.size == -1):
        # is dir
        dirs, files = manager.list_dir(dir_info.docid, by='name')
        table = prettytable.PrettyTable(['Creator', 'Size', 'Modified', 'Name'])
        table.border = False
        table.align['Name'] = 'l'
        table.align['Size'] = 'r'
        table.align['Creator'] = 'l'
        table.add_row(['', '', 
            time.strftime("%Y%m%d %H:%M:%S", time.localtime(dir_info.modified / 1000000)), '.'])
        for d in dirs:
            table.add_row([d['creator'], '(dir)', 
                time.strftime("%Y%m%d %H:%M:%S", time.localtime(d['modified'] / 1000000)), d['name']])
        for d in files:
            table.add_row([d['creator'], sizeof_fmt(d['size']) if readable else d['size'], 
                time.strftime("%Y%m%d %H:%M:%S", time.localtime(d['modified'] / 1000000)), d['name']])
        
        print('dir content:')
        print(table)
    else:
        # is file
        print('file detail:')
        show_file_info(manager, remote_dir, readable)


# rm entrypoint
def delete_path(manager: ApiManager, remote_path: str, allow_recurse=False):

    print('removing', remote_path)
    
    file_info = manager.get_resource_info_by_path(remote_path)
    if (file_info is None):
        print('no such file/directory', remote_path)
        return False
    elif (file_info.size != -1):
        # file
        manager.delete_file(file_info.docid)
        return True
    else:
        # dir
        if (allow_recurse):
            manager.delete_dir(file_info.docid)
            return True
        else:
            print(f'{remote_path} is a directory, use -r for recursion')
            return False
    

# mkdir entrypoint
def makedirs(manager: ApiManager, remote_path: str):
    try:
        res = manager.create_dirs_by_path(remote_path)
        print('done, docid:', res)
        return True
    except utils.api_manager.InvalidRootException:
        print('invalid root dir')
        return False


# cat entrypoint
def cat(manager: ApiManager, remote_path: str):
    file_info = manager.get_resource_info_by_path(remote_path)
    if (file_info is None):
        print('no such file ', remote_path)
        return False
    elif (file_info.size != -1):
        if (sys.platform == 'linux'):
            from signal import signal, SIGPIPE, SIG_DFL
            signal(SIGPIPE, SIG_DFL)
        download_iter = manager.download_file(file_info.docid, stream=True)
        try:
            for data in download_iter.iter_content(1024):
                sys.stdout.buffer.write(data)
        except BrokenPipeError:
            pass
        download_iter.close()
        #sys.stderr.close()
        return True
    else:
        print(f'{remote_path} is a directory')
        return False





# link enterpoint
def link_actions(manager: ApiManager, action: str, remote_path: str, expires: int, use_pass, allow_upload, no_download):
    file_info = manager.get_resource_info_by_path(remote_path)
    if (file_info is None):
        print('no such file ', remote_path)
        return False
    # get link info
    link_info = manager.get_link(file_info.docid)
    if (action == 'show'):
        if (link_info is None):
            print(f'{remote_path} does not have an enabled link')
        else:
            print(remote_path)
            print(f'https://{manager.host}/link/{link_info.link}')
            if (link_info.password != ''):
                print(f'password: {link_info.password}')
            perm_list = []
            if (link_info.perm & 1):
                perm_list.append('preview')
            if (link_info.perm & 2):
                perm_list.append('download')
            if (link_info.perm & 4):
                perm_list.append('upload')
            print(f'perm:     ' + ', '.join(perm_list))
            print(f'endtime:  ' + time.strftime("%Y%m%d %H:%M:%S", time.localtime(link_info.endtime / 1000000)) )
            print(f'limittimes: {link_info.limittimes}')
        return True
    elif (action == 'create'):
        if (expires is None):
            expires = 30
        expire_time = int(time.time() + 86400 * expires)
        if (no_download):
            allow_upload = True # must allow at least 1 perm
        allow_view = not no_download
        allow_down = not no_download
        if (link_info is None):
            link_info = manager.create_link(file_info.docid, expire_time * 1000000, -1, 
                use_pass, allow_view, allow_down, allow_upload)
        else:
            link_info = manager.modify_link(file_info.docid, expire_time * 1000000, -1, 
                use_pass, allow_view, allow_down, allow_upload)
        print(f'https://{manager.host}/link/{link_info.link}')
        return True
    elif (action == 'delete'):
        if (link_info is None):
            print('no link')
            return False
        else:
            manager.delete_link(file_info.docid)
            return True
    else:
        raise 'wtf'



# mv enterpoint
def move_file(manager: ApiManager, src: str, dst: str, overwrite=False, copy=False):

    
    src_split = src.strip('/').split('/')
    src_name = src_split[-1]
    src_parent = '/'.join(src_split[:-1])
    dst_split = dst.strip('/').split('/')
    dst_name = dst_split[-1]
    dst_parent = '/'.join(dst_split[:-1])
    
    if (src_split == dst_split):
        print('invlid src == dst')
        return False

    #      \ src |                 |
    #     dst\   |    dir          |     file
    #    ---------------------------------------------
    #       x    | src into parent | src into parent
    #            | rename     (1)  | rename     (2)
    #    ---------------------------------------------
    #      dir   | src into dir    | src into dir
    #            |            (3)  |            (4)
    #    ---------------------------------------------
    #      file  |  no way         | delete dst  (6)
    #            |            (5)  | src into parent & rename
    #    ---------------------------------------------
    
    src_info = manager.get_resource_info_by_path(src)
    if (src_info is None):
        print('no such file/dir ', src)
        return False
    
    dst_info = manager.get_resource_info_by_path(dst)
    # case (3) (4)
    if (dst_info is not None and dst_info.size == -1):
        # src into dir
        if (src_split[:-1] == dst_split):
            print('nothing happens')
            return True
        elif (src_split == dst_split[:len(src_split)]):
            print('can not move to child directory')
            return False
        else:
            if (copy):
                print(f'copying {src} into {dst}')
                manager.copy_file(src_info.docid, dst_info.docid, overwrite_on_dup=overwrite)
            else:
                print(f'moving {src} into {dst}')
                manager.move_file(src_info.docid, dst_info.docid, overwrite_on_dup=overwrite)
            return True

    # case (1) (2)
    if (dst_info is None):
        # src into parent + rename
        if (src_parent == dst_parent):
            # only rename
            if (copy):
                print(f'copying {src} to {dst}')
                dst_parent_info = manager.get_resource_info_by_path(dst_parent)
                new_src_id, new_src_name = manager.copy_file(src_info.docid, dst_parent_info.docid, rename_on_dup=True)
                manager.rename_file(new_src_id, dst_name)
            else:
                print(f'renaming {src} to {dst}')
                manager.rename_file(src_info.docid, dst_name)
            return True
        elif (src_split == dst_split[:len(src_split)]):
            print('can not move to child directory')
            return False
        else:
            # move and rename
            dst_parent_info = manager.get_resource_info_by_path(dst_parent)
            if (dst_parent_info is None):
                print('invalid destination')
                return False
            if (copy):
                print(f'copying and renaming {src} to {dst}')
                new_src_id, new_src_name = manager.copy_file(src_info.docid, dst_parent_info.docid, rename_on_dup=True)
            else:
                print(f'moving and renaming {src} to {dst}')
                new_src_id, new_src_name = manager.move_file(src_info.docid, dst_parent_info.docid, rename_on_dup=True)
            if (new_src_name != dst_name):
                manager.rename_file(new_src_id, dst_name)
            return True

    # case (5)
    if (src_info.size == -1):
        print('can not move folder into a file')
        return False
    
    # case (6)
    if (overwrite):
        if (src_parent == dst_parent):
            # only delete + rename
            print(f'overwriting {src} to {dst}')
            manager.delete_file(dst_info.docid)
            if (copy):
                dst_parent_info = manager.get_resource_info_by_path(dst_parent)
                new_src_id, new_src_name = manager.copy_file(src_info.docid, dst_parent_info.docid, rename_on_dup=True)
                manager.rename_file(new_src_id, dst_name)
            else:
                manager.rename_file(src_info.docid, dst_name)
            return True
        else:
            # delete + move + rename
            print(f'renaming and overwriting {src} to {dst}')
            dst_parent_info = manager.get_resource_info_by_path(dst_parent)
            # impossible for dest_parent to be None 
            assert dst_parent_info is not None
            manager.delete_file(dst_info.docid)
            if (copy):
                new_src_id, new_src_name = manager.copy_file(src_info.docid, dst_parent_info.docid, rename_on_dup=True)
            else:
                new_src_id, new_src_name = manager.move_file(src_info.docid, dst_parent_info.docid, rename_on_dup=True)
            if (new_src_name != dst_name):
                manager.rename_file(new_src_id, dst_name)
            return True
    else:
        print(f'{dst} already exists, use -f to overwrite')
        return False

    




def test(manager: ApiManager):
    try:


        ...
        # print(manager.list_root())

        # dir_id = manager.get_resource_id(process_remote_home(manager, '~/automated'))
        # r = manager.get_file_meta(dir_id)
        # print(r)

        # from .utils.api_manager import ApiLinkManager
        # link = ApiLinkManager('bhpan.buaa.edu.cn', '99062F532C7BC00E32B6FA3F36619F5C')
        # print(link.docid)
        # print(link.name)
        # print(bin(link.link_info.perm))
        # print(link.list_dir())

        # doc_info = manager.get_resource_info_by_path(('/刘卓然_SY2215207/temp'))
        # # doc_info = manager.get_resource_info_by_path(process_remote_home(manager, '~/temp/dist_bhpan/dist'))
        # link_info = manager.delete_link(doc_info.docid)
        # print(link_info)

    except Exception as e:
        import traceback
        print('exception in test')
        traceback.print_exc()



def main():
    # bhpan host
    host = 'bhpan.buaa.edu.cn'
    # bhpan public key
    # pubkey = '''-----BEGIN PUBLIC KEY-----
    # MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC7JL0DcaMUHumSdhxXTxqiABBC
    # DERhRJIsAPB++zx1INgSEKPGbexDt1ojcNAc0fI+G/yTuQcgH1EW8posgUni0mcT
    # E6CnjkVbv8ILgCuhy+4eu+2lApDwQPD9Tr6J8k21Ruu2sWV5Z1VRuQFqGm/c5vaT
    # OQE5VFOIXPVTaa25mQIDAQAB
    # -----END PUBLIC KEY-----
    # '''
    pubkey = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4E+eiWRwffhRIPQYvlXU
jf0b3HqCmosiCxbFCYI/gdfDBhrTUzbt3fL3o/gRQQBEPf69vhJMFH2ZMtaJM6oh
E3yQef331liPVM0YvqMOgvoID+zDa1NIZFObSsjOKhvZtv9esO0REeiVEPKNc+Dp
6il3x7TV9VKGEv0+iriNjqv7TGAexo2jVtLm50iVKTju2qmCDG83SnVHzsiNj70M
iviqiLpgz72IxjF+xN4bRw8I5dD0GwwO8kDoJUGWgTds+VckCwdtZA65oui9Osk5
t1a4pg6Xu9+HFcEuqwJTDxATvGAz1/YW0oUisjM0ObKTRDVSfnTYeaBsN6L+M+8g
CwIDAQAB
-----END PUBLIC KEY-----'''  # changed since v7 (2023.08)

    parser = argparse.ArgumentParser('bhpan api tools')
    parser.add_argument('-u', '--username', default=None, help='login as another user')

    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('upload', add_help=False)
    subparser.add_argument('localfile', help='local file path')
    subparser.add_argument('remotedir', help='remote directory')
    subparser.add_argument('--rename', default=None, help='rename uploaded file')
    subparser.add_argument('-r', action='store_true', dest='recurse', help='upload entire directory')
    subparser.set_defaults(func=lambda:upload_file(m, args.localfile, process_remote_home(m, args.remotedir), 
        rename=args.rename, allow_recurse=args.recurse))
    
    subparser = subparsers.add_parser('download', add_help=False)
    subparser.add_argument('remotefile', help='remote file path')
    subparser.add_argument('localdir', help='local directory')
    subparser.add_argument('--rename', default=None, help='rename downloaded file')
    subparser.add_argument('-r', action='store_true', dest='recurse', help='download entire directory')
    subparser.set_defaults(func=lambda:download_file(m, process_remote_home(m, args.remotefile), args.localdir, 
        rename=args.rename, allow_recurse=args.recurse))
    
    subparser = subparsers.add_parser('ls', add_help=False)
    subparser.add_argument('remotedir', help='remote directory')
    subparser.add_argument('-h', action='store_true', dest='readable', help='readable file size')
    subparser.set_defaults(func=lambda:list_dir(m, process_remote_home(m, args.remotedir), readable=args.readable))
    
    subparser = subparsers.add_parser('rm', add_help=False)
    subparser.add_argument('remotepath', help='remote path to delete')
    subparser.add_argument('-r', action='store_true', dest='recurse', help='delete entire directory')
    subparser.set_defaults(func=lambda:delete_path(m, process_remote_home(m, args.remotepath), allow_recurse=args.recurse))

    subparser = subparsers.add_parser('mkdir', add_help=False)
    subparser.add_argument('remotepath', help='remote path to create')
    subparser.set_defaults(func=lambda:makedirs(m, process_remote_home(m, args.remotepath)))
    
    subparser = subparsers.add_parser('mv', add_help=False)
    subparser.add_argument('src', help='remote file path')
    subparser.add_argument('dst', help='remote destination directory')
    subparser.add_argument('-f', action='store_true', dest='overwrite', help='overwrite existing files')
    subparser.set_defaults(func=lambda:move_file(m, process_remote_home(m, args.src), process_remote_home(m, args.dst), 
        args.overwrite))
        
    subparser = subparsers.add_parser('cp', add_help=False)
    subparser.add_argument('src', help='remote file path')
    subparser.add_argument('dst', help='remote destination directory')
    subparser.add_argument('-f', action='store_true', dest='overwrite', help='overwrite existing files')
    subparser.set_defaults(func=lambda:move_file(m, process_remote_home(m, args.src), process_remote_home(m, args.dst), 
        args.overwrite, copy=True))

    subparser = subparsers.add_parser('cat', add_help=False)
    subparser.add_argument('remotepath')
    subparser.set_defaults(func=lambda:cat(m, process_remote_home(m, args.remotepath)))

    subparser = subparsers.add_parser('link', add_help=False)
    subparser.add_argument('link_action', choices=['show', 'create', 'delete'])
    subparser.add_argument('remotepath', help='remote file or dir')
    subparser.add_argument('-e', '--expires', type=int, default=None, help='days before expire')
    subparser.add_argument('-p', action='store_true', dest='use_pass', help='enable password')
    subparser.add_argument('--allow-upload', action='store_true', dest='allow_upload', help='enable upload')
    subparser.add_argument('--no-download', action='store_true', dest='no_download', help='disable download and preview')
    subparser.set_defaults(func=lambda:link_actions(m, args.link_action, process_remote_home(m, args.remotepath),
                                            args.expires, args.use_pass, args.allow_upload, args.no_download))
    
    subparser = subparsers.add_parser('test')
    subparser.set_defaults(func=lambda:test(m))

    args = parser.parse_args()
    if (not hasattr(args, 'func')):
        parser.print_help()
        return

    # read stored config
    config = StoredObject('bhpan', 'config.json')

    # handle config versions
    updated_keys = [
        (2, ['encrypted']),
    ]
    config_rivision = config.get_by_path('revision', default_val=0)
    current_rivision = 2
    if (config_rivision != current_rivision):
        print(f'updating config from {config_rivision} to {current_rivision}')
        for rev, keys in updated_keys:
            if (rev > config_rivision):
                for key in keys:
                    config.remove_by_path(key)
        config.set_by_path('revision', current_rivision)
        config.save()

    # default
    config.set_by_path('store_password', True, override=False)
    config.save()

    
            
    # get username
    if (args.username is None):
        # use stored username
        username = config.get_by_path('username')
        if (username is None):
            username = input('Username: ')
            config.set_by_path('username', username)
    else:
        username = args.username
        #print(f'Username: {username}')
    
    # get secret
    store_password = config.get_by_path('store_password') and args.username is None
    password = None
    encrypted = None
    if (store_password):
        encrypted = config.get_by_path('encrypted')
        if (encrypted is None):
            password = getpass.getpass()
            config.set_by_path('encrypted', utils.rsa_utils.encrypt(password, pubkey))
    else:
        password = getpass.getpass()

    # try login
    login_ok = False
    for retry in range(3):
        try:
            m = ApiManager(
                host, username, password, pubkey, encrypted=encrypted,
                cached_token=config.get_by_path('cached_token/token'),
                cached_expire=config.get_by_path('cached_token/expires'))
            login_ok = True
            break
        except utils.api_manager.WrongPasswordException as e:
            time.sleep(1)
            print('wrong username/pass, try', retry)

    if (login_ok):
        config.save()
        args.func()
        if (m._expires > 0):
            config.set_by_path('cached_token/token', m._tokenid)
            config.set_by_path('cached_token/expires', m._expires)
            config.save()
    else:
        config.remove_by_path('username')
        config.remove_by_path('encrypted')
        config.save()






if __name__ == '__main__':
    main()




