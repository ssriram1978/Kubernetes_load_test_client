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

   echo "rm -f $directory_name/infrastructure_components.tar.gz "
   rm -f $directory_name/infrastructure_components.tar.gz

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


monitor_infrastructure() {
   start_stop=$1
   yaml_file=$2
   stack_tag=$3

    if [[ -z $2 ]]; then
        yaml_file="docker-stack-infrastructure.yml"
    fi

    if [[ -z $3 ]]; then
        stack_tag="infrastructure"
    fi

  if [[ "$1" == "stop" ]]; then
       echo "docker stack rm $stack_tag"
       docker stack rm ${stack_tag}

       echo "curl -XDELETE 'http://172.17.0.1:9200/*"
       curl -XDELETE 'http://172.17.0.1:9200/*'
  elif [[ "$1" == "start" ]]; then
        echo "sysctl_tcp_kernel_optimization"
        sysctl_tcp_kernel_optimization

       echo "docker-compose -f $yaml_file build"
       docker-compose -f ${yaml_file} build

       echo "docker stack deploy -c $yaml_file $stack_tag"
       docker stack deploy -c ${yaml_file} ${stack_tag}
   fi
}

deploy_infrastructure() {
   yaml_file=$1
   tag=$2

  if [[ $2 == "" ]]; then
       tag="load_test"
   fi

   echo "sysctl_tcp_kernel_optimization"
   sysctl_tcp_kernel_optimization

  echo "chmod go-w plotter/filebeat/filebeat.docker.yml"
  sudo chmod go-w plotter/filebeat/filebeat.docker.yml

   echo "chown root:root plotter/filebeat/filebeat.docker.yml"
   sudo chown root:root plotter/filebeat/filebeat.docker.yml

   echo "docker stack deploy --compose-file docker-stack-common.yml -c $yaml_file $tag"
   docker stack deploy --compose-file docker-stack-common.yml  -c $yaml_file $tag
}

optimize_host() {
   echo "sudo docker container prune -f"
   sudo docker container prune -f

   echo "sysctl_tcp_kernel_optimization"
   sysctl_tcp_kernel_optimization
}

teardown_infrastructure() {
   echo "docker stack rm load_test"
   docker stack rm load_test
}

docker_prune() {
   echo "docker system prune --all --force --volumes"
   sudo docker system prune --all --force --volumes

   echo "sudo find /var/lib/docker/containers/ -type f -name \"*.log\" -delete"
   sudo find /var/lib/docker/containers/ -type f -name "*.log" -delete

   echo "sudo docker container prune -f"
   sudo docker container prune -f

   echo "sudo docker image prune -f"
   sudo docker image prune -f
}

sysctl_tcp_kernel_optimization() {

    echo "fs.file-max=2097152 >> /etc/sysctl.conf"
    sudo echo "fs.file-max=2097152" >> /etc/sysctl.conf

    echo "fs.nr_open=2097152  >> /etc/sysctl.conf"
    sudo echo "fs.nr_open=2097152" >> /etc/sysctl.conf

    echo "net.ipv4.conf.default.rp_filter=0 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.conf.default.rp_filter=0" >> /etc/sysctl.conf

    echo "net.core.somaxconn=32768  >> /etc/sysctl.conf"
    sudo echo "net.core.somaxconn=32768" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_max_syn_backlog=20480  >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_max_syn_backlog=20480" >> /etc/sysctl.conf

    echo "net.core.netdev_max_backlog=16384  >> /etc/sysctl.conf"
    sudo echo "net.core.netdev_max_backlog=16384" >> /etc/sysctl.conf

    echo "net.ipv4.ip_local_port_range=1024 65535  >> /etc/sysctl.conf"
    sudo echo "net.ipv4.ip_local_port_range=1024 65535" >> /etc/sysctl.conf

    echo "net.core.wmem_default=12582912  >> /etc/sysctl.conf"
    sudo echo "net.core.wmem_default=12582912" >> /etc/sysctl.conf

    echo "net.core.wmem_default=12582912  >> /etc/sysctl.conf"
    sudo echo "net.core.wmem_default=12582912" >> /etc/sysctl.conf

    echo "net.core.rmem_max=16777216  >> /etc/sysctl.conf"
    sudo echo "net.core.rmem_max=16777216" >> /etc/sysctl.conf

    echo "net.core.wmem_max=16777216 >> /etc/sysctl.conf"
    sudo echo "net.core.wmem_max=16777216" >> /etc/sysctl.conf

    echo "net.core.optmem_max=16777216 >> /etc/sysctl.conf"
    sudo echo "net.core.optmem_max=16777216" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_rmem=10240 87380 16777216 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_rmem=10240 87380 16777216" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_wmem=10240 87380 16777216 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_wmem=10240 87380 16777216" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_max_tw_buckets=400000 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_max_tw_buckets=400000" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_fin_timeout=15 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_fin_timeout=15" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_keepalive_time=30 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_keepalive_time=30" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_keepalive_intvl=15 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_keepalive_intvl=15" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_keepalive_probes=4 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_keepalive_probes=4" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_mem=8388608 8388608 8388608 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_mem=8388608 8388608 8388608" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_window_scaling=1 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_window_scaling=1" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_tw_reuse=1 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_tw_reuse=1" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_max_tw_buckets=400000 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_max_tw_buckets=400000" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_no_metrics_save=1 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_no_metrics_save=1" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_syn_retries=2 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_syn_retries=2" >> /etc/sysctl.conf

    echo "net.ipv4.tcp_synack_retries=2 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.tcp_synack_retries=2" >> /etc/sysctl.conf

    # Connection tracking to prevent dropped connections (usually issue on LBs)
    echo "net.netfilter.nf_conntrack_max=262144 >> /etc/sysctl.conf"
    sudo echo "net.netfilter.nf_conntrack_max=262144" >> /etc/sysctl.conf

    echo "net.netfilter.nf_conntrack_generic_timeout=120 >> /etc/sysctl.conf"
    sudo echo "net.netfilter.nf_conntrack_generic_timeout=120" >> /etc/sysctl.conf

    echo "net.netfilter.nf_conntrack_tcp_timeout_established=86400 >> /etc/sysctl.conf"
    sudo echo "net.netfilter.nf_conntrack_tcp_timeout_established=86400" >> /etc/sysctl.conf

    # ARP cache settings for a highly loaded docker swarm
    echo "net.ipv4.neigh.default.gc_thresh1=8096 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.neigh.default.gc_thresh1=8096" >> /etc/sysctl.conf

    echo "net.ipv4.neigh.default.gc_thresh2=12288 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.neigh.default.gc_thresh2=12288" >> /etc/sysctl.conf

    echo "net.ipv4.neigh.default.gc_thresh3=16384 >> /etc/sysctl.conf"
    sudo echo "net.ipv4.neigh.default.gc_thresh3=16384" >> /etc/sysctl.conf

    echo "sysctl -p"
    sudo sysctl -p

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
      $yaml_file \
      $tag
}

deploy_cpu_ram_monitor() {

   echo "docker run -d   -p 19999:19999  \
    -v /proc:/host/proc:ro   -v /sys:/host/sys:ro  \
     -v /var/run/docker.sock:/var/run/docker.sock:ro  \
      --cap-add SYS_PTRACE   \
      --security-opt apparmor=unconfined   \
      netdata/netdata"

    docker run -d  -p 19999:19999   \
    -v /proc:/host/proc:ro   \
    -v /sys:/host/sys:ro   \
    -v /var/run/docker.sock:/var/run/docker.sock:ro   \
    --cap-add SYS_PTRACE   \
    --security-opt apparmor=unconfined   \
    netdata/netdata

   echo "docker run -d --name dd-agent \
   -v /var/run/docker.sock:/var/run/docker.sock:ro \
   -v /proc/:/host/proc/:ro \
   -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
   -e DD_API_KEY=34f093cb0b22208d56cd241028a632b8 \
   datadog/agent:latest"

   docker run -d --name dd-agent \
   -v /var/run/docker.sock:/var/run/docker.sock:ro \
   -v /proc/:/host/proc/:ro \
   -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
   -e DD_API_KEY=34f093cb0b22208d56cd241028a632b8 \
   datadog/agent:latest

#   echo "docker run -d \
#  --name=filebeat \
#  --user=root \
#  --volume=\"\$(pwd)/filebeat.docker.yml:/usr/share/filebeat/filebeat.yml:ro\" \
#  --volume=\"/var/lib/docker/containers:/var/lib/docker/containers:ro\" \
#  --volume=\"/var/run/docker.sock:/var/run/docker.sock:ro\" \
#  --volume=\"/etc/timezone:/etc/timezone:ro\" \
#  --volume=\"/etc/localtime:/etc/localtime:ro\" \
#  docker.elastic.co/beats/filebeat:7.1.0 filebeat -e -strict.perms=false \
#  -E output.elasticsearch.hosts=[\"elasticsearch:9200\"]"


#docker run -d \
#  --name=filebeat \
#  --user=root \
#  --volume="$(pwd)/plotter/filebeat/filebeat.docker.yml:/usr/share/filebeat/filebeat.yml:ro" \
#  --volume="/var/lib/docker/containers:/var/lib/docker/containers:ro" \
#  --volume="/var/run/docker.sock:/var/run/docker.sock:ro" \
#  --volume="/etc/timezone:/etc/timezone:ro" \
#  --volume="/etc/localtime:/etc/localtime:ro" \
#  docker.elastic.co/beats/filebeat:6.5.4 filebeat -e -strict.perms=false \
#  -E output.elasticsearch.hosts=[\"elasticsearch:9200\"]

}

connect_to_mec() {
   echo "setting port forwarding rules for your local web browser to connect to MEC"
   echo "loadtest3:10.10.75.12"
   echo "loadtest4:10.10.75.14"
   echo "loadtest1:10.10.75.10"
   echo "loadtest2:10.10.75.25"

   echo "kubernetes dashboard: http://localhost:30703"
   ssh -i ~/.ssh/id_rsa_mec -p221 charles.d@bastionr-vm.mec-poc.aws.oath.cloud -NL 30783:10.10.75.12:30783 &

   echo "Redis: http://localhost:32622"
   ssh -i ~/.ssh/id_rsa_mec -p221 charles.d@bastionr-vm.mec-poc.aws.oath.cloud -NL 32622:10.10.75.12:32622 &

   echo "netdata Master loadtest3: http://localhost:19999"
   ssh -i ~/.ssh/id_rsa_mec -p221 charles.d@bastionr-vm.mec-poc.aws.oath.cloud -NL 19999:10.10.75.12:19999 &

   echo "netdata loadtest4: http://localhost:20000"
   ssh -i ~/.ssh/id_rsa_mec -p221 charles.d@bastionr-vm.mec-poc.aws.oath.cloud -NL 20000:10.10.75.14:19999 &

   echo "netdata loadtest1: http://localhost:20001"
   ssh -i ~/.ssh/id_rsa_mec -p221 charles.d@bastionr-vm.mec-poc.aws.oath.cloud -NL 20001:10.10.75.10:19999 &

   echo "netdata loadtest2: http://localhost:20002"
   ssh -i ~/.ssh/id_rsa_mec -p221 charles.d@bastionr-vm.mec-poc.aws.oath.cloud -NL 20002:10.10.75.25:19999 &


}

case "$1" in
  build) create_infrastructure $2 $3 $4 ;;
  deploy) deploy_infrastructure $2 $3;;
  build_and_deploy) create_deploy_infrastructure $2 $3 $4 ;;
  stop) teardown_infrastructure  ;;
  prune) docker_prune ;;
  monitor) monitor_infrastructure $2 $3 $4;;
  deploy_cpu_ram_monitor) deploy_cpu_ram_monitor ;;
  connect_to_mec) connect_to_mec ;;
  optimize_host) optimize_host ;;
  *) echo "usage: $0"
      echo "<build <all|directory_name> <yaml file> <tag -- optional> > |"
      echo "<deploy <yaml file> > |"
      echo "<build_and_deploy <all|directory_name> <yaml file> <tag --optional>> | "
      echo "stop"
      echo "prune"
      echo "deploy_cpu_ram_monitor"
      echo "monitor start|stop"
      echo "connect_to_mec"
      echo "optimize_host"
     exit 1
     ;;
esac
