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

uninstall_docker_ce() {
   echo "sudo apt-get purge docker-ce"
   sudo apt-get purge docker-ce

   echo "sudo rm -rf /var/lib/docker"
   sudo rm -rf /var/lib/docker

   echo "sudo apt-get remove docker docker-engine docker.io containerd runc"
   sudo apt-get remove docker docker-engine docker.io containerd runc
}

install_kubernetes() {
  echo "sudo apt-get update && apt-get install -y apt-transport-https curl"
  sudo apt-get update && sudo apt-get install -y apt-transport-https curl

  echo "curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -"
  sudo curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

  echo "sudo apt-add-repository \"deb http://apt.kubernetes.io/ kubernetes-xenial main\""
  sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main"

  echo "sudo apt-get update"
  sudo apt-get update

  echo "apt-get install -y kubelet kubeadm kubectl"
  sudo apt-get install -y kubelet kubeadm kubectl

  echo "apt-mark hold kubelet kubeadm kubectl"
  sudo apt-mark hold kubelet kubeadm kubectl

  echo "sudo systemctl daemon-reload"
  sudo systemctl daemon-reload

  echo "sudo systemctl restart kubelet"
  sudo systemctl restart kubelet

  echo "sudo swapoff -a"
  sudo swapoff -a

  echo "sudo kubeadm init"
  sudo kubeadm init

  echo "mkdir -p $HOME/.kube"
  mkdir -p $HOME/.kube

  echo "sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config"
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config

  echo "sudo chown \$(id -u):\$(id -g) \$HOME/.kube/config"
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

  echo "sudo kubectl taint nodes --all node-role.kubernetes.io/master-"
  sudo sudo kubectl taint nodes --all node-role.kubernetes.io/master-

}

uninstall_kubernetes() {
  echo "sudo kubeadm reset"
  sudo kubeadm reset

  echo "sudo apt-get -y purge kubeadm kubectl kubelet kubernetes-cni kube*"
  sudo apt-get purge kubeadm kubectl kubelet kubernetes-cni kube*

  echo "sudo apt-get -y autoremove"
  sudo apt-get autoremove

  echo "sudo rm -rf ~/.kube"
  sudo rm -rf ~/.kube

}

case "$1" in
	install_docker) install_docker_ce ;;
	uninstall_docker) uninstall_docker_ce ;;
	install_kubernetes) install_kubernetes ;;
	uninstall_kubernetes) uninstall_kubernetes ;;
	*) echo "usage: $0"
	   echo "install_docker"
	   echo "uninstall_docker"
	   echo "install_kubernetes"
	   echo "uninstall_kubernetes"
	   exit 1
	   ;;
esac

