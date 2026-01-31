# Add SSH Public Key to Remote Server

## Your Public Key
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAII63jBfZAERGo/a051CypVtEhUXwVqm/+DCUXs0txIjV odoo-migration-20251118
```

## Method 1: Using the Script (Interactive)
Run the script and enter your SSH password when prompted:
```bash
./add_ssh_key_to_remote.sh
```

## Method 2: Manual Command
Run this command (will prompt for SSH password):
```bash
ssh as@103.101.59.102 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo "$(cat ~/.ssh/id_ed25519_odoo.pub)" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo "SSH key added successfully!"'
```

## Method 3: Copy-Paste Method
1. Copy your public key:
   ```bash
   cat ~/.ssh/id_ed25519_odoo.pub
   ```

2. SSH to the remote server:
   ```bash
   ssh as@103.101.59.102
   ```

3. On the remote server, run:
   ```bash
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   nano ~/.ssh/authorized_keys
   # Paste your public key, save and exit
   chmod 600 ~/.ssh/authorized_keys
   ```

## Verify Key is Added
After adding the key, test the connection:
```bash
ssh -i ~/.ssh/id_ed25519_odoo as@103.101.59.102 "echo 'Connection successful!'"
```

If it works without asking for a password, the key is properly configured!

