Place only the verified public SSH **user CA** key here as `ssh_user_ca_key.pub`.
Compare `ssh-keygen -lf` with the fingerprint recorded at CA initialization.
Never place a private CA key, an X.509 root certificate, or a laptop public key here.
The public key is deliberately absent until you initialize your own CA.
