
本项目提供了上传、下载、管理北航网盘文件的命令行工具，适合在无GUI的服务器上使用

# Anyshare API 参考 https://developers.aishutech.com/openDoc/product/2/version/3/doc/15

# 安装
python setup.py install



# 第一次运行会提示登录
# 凭据存储路径   windows: AppData/Roaming/bhpan   linux: ~/.local/share/bhpan
# 存储的是用北航网盘提供的公钥加密的密码，如果不想存储登录凭据，每次手动输入，那么请在凭据存储路径下的config.json中把"store_password"改为false


# ls
bhpan ls [远程文件/文件夹]
#（可用home表示文档根目录）
bhpan ls home -h



# upload
bhpan upload [本地文件/文件夹] [远程文件夹]



# download
bhpan download [远程文件/文件夹] [本地文件夹]



# rm
bhpan rm [远程文件/文件夹]



# cat
bhpan cat [远程文件]
# 可pipe
bhpan cat home/xxx.txt | tail



# mv rm 和linux下类似
# 重命名
bhpan mv home/test.png home/test2.png
# 移动（home/dir2/dir3必须存在）
bhpan mv home/dir1/test.png home/dir2/dir3
# 移动并重命名
bhpan mv home/dir1/test.png home/dir2/dir3/test2.png
# -f 覆盖


# mkdir可直接创建多级路径
bhpan mkdir home/test/1/2/3



# link 外链分享

# 查看文件上的外链
bhpan link show [远程文件/文件夹]

# 开启/修改
# 启用密码 -p 
# 允许上传 --allow-upload 
# 禁止预览 --no-download
# --expires [过期天数]
bhpan link create [远程文件/文件夹]

# 停止分享
bhpan link delete [远程文件/文件夹]

