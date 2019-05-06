#!/bin/bash


gzip_infrastructure_components() {
   echo "rm -f infrastructure_components.tar.gz"
   rm -f infrastructure_components.tar.gz

   echo "tar -czvf infrastructure_components.tar.gz infrastructure_components"
   tar -czvf infrastructure_components.tar.gz infrastructure_components
}


build_push_directory() {
   directory_name=$1
   tag=$2

   echo "rm -f $1/infrastructure_components.tar.gz "
   rm -f $1/infrastructure_components.tar.gz

   echo "cp infrastructure_components.tar.gz $directory_name/"
   cp infrastructure_components.tar.gz $directory_name

   if [[ "$2" != "" ]]; then
        echo "docker build $directory_name -t $tag/$directory_name:latest"
        docker build $directory_name -t $tag/$directory_name:latest

        echo "docker push $tag/$directory_name:latest"
        docker push $tag/$directory_name:latest
   else
        echo "docker build $directory_name -t $directory_name:latest"
        docker build $directory_name -t $directory_name:latest
   fi

   echo "rm -f $directory_name/infrastructure_components.tar.gz"
   rm -f $directory_name/infrastructure_components.tar.gz
}


create_infrastructure() {
   directory_name=$1
   yaml_file=$2
   tag=$3

   echo "gzip_infrastructure_components"
   gzip_infrastructure_components

   if [[ "$1" == "all" ]]; then
        echo "build_push_directory publisher $tag"
        build_push_directory \
        publisher \
        $tag

        echo "build_push_directory subscriber $tag"
        build_push_directory \
        subscriber \
        $tag

        echo "build_push_directory transformer $tag"
        build_push_directory \
        transformer \
        $tag

        #cho "build_push_directory plotter $tag"
        #build_push_directory \
        #plotter \
        #$tag

        echo "build_push_directory orchestrator $tag"
        build_push_directory \
        orchestrator \
        $tag

        #echo "build_push_directory displayer $tag"
        #build_push_directory \
        #displayer \
        #$tag

        echo "docker-compose -f  docker-stack-common.yml build"
        docker-compose -f docker-stack-common.yml build

        echo "docker-compose -f $2 build"
        docker-compose -f $2 build
    else
        echo "build_push_directory $tag"
        build_push_directory \
        $1 \
        $tag
    fi
}

deploy_infrastructure() {
   yaml_file=$1
   tag=$2

    echo "sysctl_tcp_kernel_optimization"
    sysctl_tcp_kernel_optimization

    echo "chmod go-w plotter/filebeat/filebeat.docker.yml"
    chmod go-w plotter/filebeat/filebeat.docker.yml

    echo "chown root:root plotter/filebeat/filebeat.docker.yml"
    chown root:root plotter/filebeat/filebeat.docker.yml

    if [[ $tag == "" ]]; then
        echo "docker stack deploy --compose-file docker-stack-common.yml -c $1 load_test"
        docker stack deploy --compose-file docker-stack-common.yml  -c $1 load_test
    else
        echo "docker stack deploy --compose-file docker-stack-common.yml -c $1 $tag"
        docker stack deploy --compose-file docker-stack-common.yml  -c $1 $tag
    fi
}

teardown_infrastructure() {
   echo "docker stack rm load_test"
   docker stack rm load_test
}


docker_prune() {
   echo "sudo find /var/lib/docker/containers/ -type f -name \"*.log\" -delete"
   sudo find /var/lib/docker/containers/ -type f -name "*.log" -delete

   echo "sudo docker container prune -f"
   sudo docker container prune -f

   echo "sudo docker image prune -f"
   sudo docker image prune -f
}

sysctl_tcp_kernel_optimization() {

    echo "fs.file-max=2097152 >> /etc/sysctl.conf"
    echo "fs.file-max=2097152" >> /etc/sysctl.conf

    echo "fs.nr_open=2097152  >> /etc/sysctl.conf"
    echo "fs.nr_open=2097152" >> /etc/sysctl.conf

    echo "net.core.somaxconn=32768  >> /etc/sysctl.conf"
    echo "net.core.somaxconn=32768" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_max_syn_backlog=20480  >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_max_syn_backlog=20480" >> /etc/sysctl.conf

    echo "net.core.netdev_max_backlog=16384  >> /etc/sysctl.conf"
    echo "net.core.netdev_max_backlog=16384" >> /etc/sysctl.conf

    echo "net.ipv4.ip_local_port_range=1024 65535  >> /etc/sysctl.conf"
    echo "net.ipv4.ip_local_port_range=1024 65535" >> /etc/sysctl.conf

    echo "net.core.wmem_default=12582912  >> /etc/sysctl.conf"
    echo "net.core.wmem_default=12582912" >> /etc/sysctl.conf

    echo "net.core.wmem_default=12582912  >> /etc/sysctl.conf"
    echo "net.core.wmem_default=12582912" >> /etc/sysctl.conf

    echo "net.core.rmem_max=16777216  >> /etc/sysctl.conf"
    echo "net.core.rmem_max=16777216" >> /etc/sysctl.conf

    echo "net.core.wmem_max=16777216 >> /etc/sysctl.conf"
    echo "net.core.wmem_max=16777216" >> /etc/sysctl.conf

    echo "net.core.optmem_max=16777216 >> /etc/sysctl.conf"
    echo "net.core.optmem_max=16777216" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_rmem=10240 87380 16777216 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_rmem=10240 87380 16777216" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_wmem=10240 87380 16777216 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_wmem=10240 87380 16777216" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_max_tw_buckets=400000 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_max_tw_buckets=400000" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_fin_timeout=15 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_fin_timeout=15" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_mem=8388608 8388608 8388608 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_mem=8388608 8388608 8388608" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_window_scaling=1 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_window_scaling=1" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_tw_reuse=1 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_tw_reuse=1" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_max_tw_buckets=400000 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_max_tw_buckets=400000" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_no_metrics_save=1 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_no_metrics_save=1" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_syn_retries=2 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_syn_retries=2" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_synack_retries=2 >> /etc/sysctl.conf"
    echo "net.ipv4.tcp_synack_retries=2" >> /etc/sysctl.conf

    # Connection tracking to prevent dropped connections (usually issue on LBs)
    echo "net.netfilter.nf_conntrack_max=262144 >> /etc/sysctl.conf"
    echo "net.netfilter.nf_conntrack_max=262144" >> /etc/sysctl.conf

    echo "net.netfilter.nf_conntrack_generic_timeout=120 >> /etc/sysctl.conf"
    echo "net.netfilter.nf_conntrack_generic_timeout=120" >> /etc/sysctl.conf

    echo "net.netfilter.nf_conntrack_tcp_timeout_established=86400 >> /etc/sysctl.conf"
    echo "net.netfilter.nf_conntrack_tcp_timeout_established=86400" >> /etc/sysctl.conf

    # ARP cache settings for a highly loaded docker swarm
    echo "net.ipv4.neigh.default.gc_thresh1=8096 >> /etc/sysctl.conf"
    echo "net.ipv4.neigh.default.gc_thresh1=8096" >> /etc/sysctl.conf

    echo "net.ipv4.neigh.default.gc_thresh2=12288 >> /etc/sysctl.conf"
    echo "net.ipv4.neigh.default.gc_thresh2=12288" >> /etc/sysctl.conf

    echo "net.ipv4.neigh.default.gc_thresh3=16384 >> /etc/sysctl.conf"
    echo "net.ipv4.neigh.default.gc_thresh3=16384" >> /etc/sysctl.conf

    echo "sysctl -p"
    sysctl -p

}

create_deploy_infrastructure() {
   directory_name=$1
   yaml_file=$2
   tag=$3

   echo "create_infrastructure "
   create_infrastructure \
     $directory_name \
     $yaml_file \
     $tag

   echo "deploy_infrastructure"
   deploy_infrastructure \
      $yaml_file
      $tag
}

case "$1" in
  build) create_infrastructure $2 $3 $4 ;;
  deploy) deploy_infrastructure $2 $3;;
  build_and_deploy) create_deploy_infrastructure $2 $3 $4 ;;
  stop) teardown_infrastructure  ;;
  prune) docker_prune ;;
  *) echo "usage: $0"
      echo "<build <all|directory_name> <yaml file> <tag -- optional> > |"
      echo "<deploy <yaml file> > |"
      echo "<build_and_deploy <all|directory_name> <yaml file> <tag --optional>> | "
      echo "stop"
      echo "prune"
     exit 1
     ;;
esac
