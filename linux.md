sudo mkdir -p /etc/rancher/k3s/certs 
sudo cp auth-lab-root-ca.crt /etc/rancher/k3s/certs/  
sudo chmod 644 /etc/rancher/k3s/certs/auth-lab-root-ca.crt  

## Permission
```
ls -l file.txt    # show user group by name
ls -ln file.txt   # show uid gid
ls -ld myfolder
ls -la .

stat file.txt     # very details

shows permissions for every folder leading to the file
namei -l /etc/rancher/k3s/certs
```
```
-rw-r--r-- 1 root root 1200 Jul 27 10:00 file.txt
                    ^    ^
                   user group
- | rw- | r-- | r--
   owner group others

First character:
-: regular file
d: directory
l: symbolic link

The 1 is the hard-link count. For directories, often see higher numbers "drwxr-xr-x 2 root root myfolder"
```
```
read    r = 4               execute x = 1
write   w = 2               missing - = 0

Owner:  rw- = 4 + 2 + 0 = 6
Group:  r-- = 4 + 0 + 0 = 4
Others: r-- = 4 + 0 + 0 = 4

600 = rw-------  owner reads/writes; nobody else
644 = rw-r--r--  normal non-executable file
700 = rwx------  private executable/directory
750 = rwxr-x---  owner full; group reads/enters
755 = rwxr-xr-x  common script or public directory
777 = rwxrwxrwx  everyone full access; usually avoid
```

## User UID & Group GID
```
command: id valkyrie
returns: uid=1000(valkyrie) gid=1000(valkyrie) groups=1000(valkyrie),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),100(users),101(lxd)

| UID | Typical use |
|---:|---|
| `0` | `root`, unlimited administrator |
| `1-999` | System and service accounts |
| `1000+` | Normal human users |
| `65534` | Usually `nobody`, an intentionally unprivileged account |

chown UID:GID file
sudo chown postgres:postgres file.txt
sudo chown 101:103 file.txt
```
```
chmod 644        controls what the owner/group/others may do
chown 101:103    controls who the owner and group are
```