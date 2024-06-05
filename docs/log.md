## Mac Setup

```
brew install colima
colima start --profile ahh --vm-type=vz --vz-rosetta --arch arm64 --cpu 8 --memory 8 --disk 50 --network-address --mount /code:w -e
```

- I used proper hypervisor, `vz`, which is essential for a usable (fast-ish) system.
- I used native architecture. It's possible to use `amd64`, but the VM is kinda slow.
- `/code` is my host mount point for case-sensitive Volume. I check out git repos there.
- I provisioned the VM well: CPU, RAM and SSD.
- `-e` allows to tweak configuration before VM is created. I've set `dns: [8.8.8.8]`.
- `-profile <abc>` is just a name for your VM.

The command returns the VM is started, shell into it with:

```
colima x -p ahh
```

## Linux Setup

```
sudo apt update
sudo apt install snapd
sudo snap install lxd
sudo usermod -a -G lxd ${USER}
newgrp lxd
sudo lxd init  # with tweaks
sudo snap install rockcraft --classic
sudo iptables -I DOCKER-USER -o lxdbr0 -j ACCEPT
sudo iptables -I DOCKER-USER -i lxdbr0 -j ACCEPT

cd /code/hexanator
rockcraft pack
```

## LXD Config

`sudo lxd init` somehow couldn't guess a usable address range, even though my routes were just fine.

- clustering? no (default)
- storage pool? yes (default)
- storage pool name? "default" (default)
- storage pool backend? `dir` ⚠️
- maas? no (default)
- create bridge? yes (default)
- bridge name? "lxdbr0" (default)
- IPv4 address? `10.0.3.1/24` ⚠️
- IPv4 NAT? yes (default)
- IPv6 address? "auto" (default)
- LXD server on network? no (default)
- Update cached images? yes (default)
- Show YAML? yes (see below)

The configuration that was applied is below:

```
config: {}
networks:
- config:
    ipv4.address: 10.0.3.1/24
    ipv4.nat: "true"
    ipv6.address: auto
  description: ""
  name: lxdbr0
  type: ""
  project: default
storage_pools:
- config: {}
  description: ""
  name: default
  driver: dir
storage_volumes: []
profiles:
- config: {}
  description: ""
  devices:
    eth0:
      name: eth0
      network: lxdbr0
      type: nic
    root:
      path: /
      pool: default
      type: disk
  name: default
projects: []
cluster: null
```

## Versions

- `colima 0.6.9`
- `Ubuntu 24.04`
- `snap 2.63`
- `lxd 5.21/stable`
- `rockcraft 1.3.2`
