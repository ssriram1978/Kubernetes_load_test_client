#!/bin/bash

install_docker_ce() {
	echo "sudo apt-get update"
	sudo apt-get update

        echo "sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common"
	sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common

	echo "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -"
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

	echo "sudo add-apt-repository \
   \"deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable\""

	sudo add-apt-repository \
   \"deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable\"

	echo "sudo apt-get update"
	sudo apt-get update

	echo "sudo apt-get install -y docker-ce docker-ce-cli containerd.io"
	sudo apt-get install -y docker-ce docker-ce-cli containerd.io

	echo "sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose"
	sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

	echo "sudo chmod +x /usr/local/bin/docker-compose"
	sudo chmod +x /usr/local/bin/docker-compose

	echo "sudo groupadd docker"
	sudo groupadd docker

	echo "sudo usermod -aG docker $USER"
	sudo usermod -aG docker $USER

	echo "sudo systemctl enable docker"
	sudo systemctl enable docker

}

case "$1" in
	install_docker) install_docker_ce ;;
	*) echo "usage: $0"
	   echo "install_docker"
	   exit 1
	   ;;
esac

