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

	sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

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

	echo "docker swarm init"
	sudo docker swarm init

}

uninstall_docker_ce() {
   echo "sudo docker swarm leave --force"
   sudo docker swarm leave --force

   echo "sudo apt-get purge docker-ce"
   sudo apt-get purge docker-ce

   echo "sudo rm -rf /var/lib/docker"
   sudo rm -rf /var/lib/docker

   echo "sudo apt-get remove docker docker-engine docker.io containerd runc"
   sudo apt-get remove docker docker-engine docker.io containerd runc
}

install_kubernetes() {
  master_or_worker=$1
  address=$2
  token=$3
  hash=$4

  echo "sudo apt-get update && apt-get install -y apt-transport-https curl"
  sudo apt-get update && sudo apt-get install -y apt-transport-https curl

  echo "curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -"
  sudo curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

  echo "sudo apt-add-repository \"deb https://apt.kubernetes.io/ kubernetes-xenial main\""
  sudo apt-add-repository "deb https://apt.kubernetes.io/ kubernetes-xenial main"

  echo "sudo apt-get update"
  sudo apt-get update

  echo "apt-get install -y kubelet kubeadm kubectl"
  sudo apt-get install -y kubelet kubeadm kubectl

  echo "sudo systemctl daemon-reload"
  sudo systemctl daemon-reload

  echo "sudo systemctl restart kubelet"
  sudo systemctl restart kubelet

  echo "sudo swapoff -a"
  sudo swapoff -a

  echo "systemctl enable kubelet"
  sudo systemctl enable kubelet

  if [[ $1 == "" ]]; then
       master_or_worker="master"
  fi

  if [[ $master_or_worker == "master" ]]; then

     echo "apt-mark hold kubelet kubeadm kubectl"
     sudo apt-mark hold kubelet kubeadm kubectl

     echo "sudo kubeadm init  --ignore-preflight-errors=all"
     sudo kubeadm init  --ignore-preflight-errors=all

     echo "mkdir -p $HOME/.kube"
     mkdir -p $HOME/.kube

     echo "sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config"
     sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config

     echo "sudo chown \$(id -u):\$(id -g) \$HOME/.kube/config"
     sudo chown $(id -u):$(id -g) $HOME/.kube/config

     echo "sudo kubectl taint nodes --all node-role.kubernetes.io/master-"
     sudo kubectl taint nodes --all node-role.kubernetes.io/master-

     #echo "sudo kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml"
     #sudo kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

     echo "export kubever=$(kubectl version | base64 | tr -d '\n')"
     export kubever=$(kubectl version | base64 | tr -d '\n')

     echo "kubectl apply -f \"https://cloud.weave.works/k8s/net?k8s-version=\$kubever\""
     sudo kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$kubever"

     #echo "kubeadm token create --print-join-command"
     sudo kubeadm token create --print-join-command

     #echo "kubectl create -f https://raw.githubusercontent.com/kubernetes/dashboard/master/aio/deploy/recommended/kubernetes-dashboard.yaml"
     #sudo kubectl create -f https://raw.githubusercontent.com/kubernetes/dashboard/master/aio/deploy/recommended/kubernetes-dashboard.yaml

     #echo "kubectl create serviceaccount cluster-admin-dashboard-sa"
     #sudo kubectl create serviceaccount cluster-admin-dashboard-sa

     #echo "kubectl create clusterrolebinding cluster-admin-dashboard-sa \
     #      --clusterrole=cluster-admin \
     #      --serviceaccount=default:cluster-admin-dashboard-sa"
     #sudo kubectl create clusterrolebinding cluster-admin-dashboard-sa \
     #        --clusterrole=cluster-admin \
     #        --serviceaccount=default:cluster-admin-dashboard-sa

     #sudo "kubectl describe secret $(kubectl get secret | grep cluster-admin-dashboard-sa | awk '{print $1}')"
     #sudo kubectl describe secret $(sudo kubectl get secret | grep cluster-admin-dashboard-sa | awk '{print $1}')

     #echo "kubectl apply -f https://gist.githubusercontent.com/initcron/32ff89394c881414ea7ef7f4d3a1d499/raw/baffda78ffdcaf8ece87a76fb2bb3fd767820a3f/kube-dashboard.yaml"
     #kubectl apply -f https://gist.githubusercontent.com/initcron/32ff89394c881414ea7ef7f4d3a1d499/raw/baffda78ffdcaf8ece87a76fb2bb3fd767820a3f/kube-dashboard.yaml

     #echo "kubectl -n kube-system get service kubernetes-dashboard"
     #sudo kubectl -n kube-system get service kubernetes-dashboard

  fi

   echo "kubectl apply -f \"https://cloud.weave.works/k8s/net?k8s-version=\$kubever\""
   sudo kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$kubever"

  if [[ $master_or_worker == "worker" ]]; then
     echo "sudo kubeadm join --token $token --discovery-token-ca-cert-hash $hash"
     sudo kubeadm join $address --token $token --discovery-token-ca-cert-hash $hash
  fi

}

uninstall_kubernetes() {
  echo "sudo kubeadm reset -f"
  sudo kubeadm reset -f

  echo "sudo apt-get -y purge kubeadm kubectl kubelet kubernetes-cni kube*"
  sudo apt-get purge -y kubeadm kubectl kubelet kubernetes-cni kube*

  echo "sudo apt-get -y autoremove"
  sudo apt-get -y autoremove

  echo "sudo rm -rf ~/.kube"
  sudo rm -rf ~/.kube

}

install_kompose() {
   echo "curl -L https://github.com/kubernetes/kompose/releases/download/v1.17.0/kompose-linux-amd64 -o kompose"
   curl -L https://github.com/kubernetes/kompose/releases/download/v1.17.0/kompose-linux-amd64 -o kompose

   echo "chmod +x kompose"
   chmod +x kompose

   echo "sudo mv ./kompose /usr/local/bin/kompose"
   sudo mv ./kompose /usr/local/bin/kompose
}

kompose_convert() {
   yml_file=$1

   echo "kompose convert -f $yml_file --volumes hostPath"
   kompose convert -f $yml_file --volumes hostPath
}


case "$1" in
	install_docker) install_docker_ce ;;
	uninstall_docker) uninstall_docker_ce ;;
	install_kubernetes) install_kubernetes $2 $3 $4;;
	uninstall_kubernetes) uninstall_kubernetes ;;
	install_kompose) install_kompose ;;
	kompose_convert) kompose_convert $2 ;;
	*) echo "usage: $0"
	   echo "install_docker"
	   echo "uninstall_docker"
	   echo "install_kubernetes"
	   echo "uninstall_kubernetes"
	   echo "install_kompose"
	   echo "kompose_convert"
	   exit 1
	   ;;
esac

