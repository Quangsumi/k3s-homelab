Put laptop.pub here: copy your existing Windows SSH PUBLIC key (.pub).
This directory ignores .pub files in Git. Never put a private key here.
Additional keys can be listed in inventory/group_vars/all/main.yml.
Use state: absent to revoke a particular public key. Other keys are preserved.
