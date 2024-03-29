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

        echo "docker-compose -f  docker_stack_yml_files/docker-stack-common.yml build"
        docker-compose -f docker_stack_yml_files/docker-stack-common.yml build

        echo "docker-compose -f $2 build"
        docker-compose -f $2 build

        echo "docker push ssriram1978/logstash:latest"
        docker push $tag/logstash:latest
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
        yaml_file="docker_stack_yml_filesdocker-stack-infrastructure.yml"
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

docker_compose_elk_infrastructure() {
   start_stop=$1
   yaml_file=$2
   stack_tag=$3

    if [[ -z $2 ]]; then
        yaml_file="docker_stack_yml_filesdocker-stack-infrastructure.yml"
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

       echo "docker-compose -f $yaml_file up -d"
       docker-compose -f $yaml_file up -d
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

   echo "docker stack deploy --compose-file docker_stack_yml_filesdocker-stack-common.yml -c $yaml_file $tag"
   docker stack deploy --compose-file docker_stack_yml_filesdocker-stack-common.yml  -c $yaml_file $tag
}

optimize_host() {
   echo "sudo docker container prune -f"
   sudo docker container prune -f

   echo "sysctl_tcp_kernel_optimization"
   sysctl_tcp_kernel_optimization

   echo "chmod go-w plotter/filebeat/filebeat.docker.yml"
   sudo chmod go-w plotter/filebeat/filebeat.docker.yml

   echo "chown root:root plotter/filebeat/filebeat.docker.yml"
   sudo chown root:root plotter/filebeat/filebeat.docker.yml

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

   echo "sudo swapoff -a"
   sudo swapoff -a

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
   -e DD_API_KEY= your_key \
   datadog/agent:latest"

   docker run -d --name dd-agent \
   -v /var/run/docker.sock:/var/run/docker.sock:ro \
   -v /proc/:/host/proc/:ro \
   -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
   -e DD_API_KEY=your_key \
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

deploy_elk() {
   #echo "docker-compose -f  docker-stack-infrastructure.yml  build"
   #docker-compose -f  docker-stack-infrastructure.yml  build

   echo "kubectl apply -f kubernetes_yaml_files/elk_components/"
   kubectl apply -f kubernetes_yaml_files/elk_components/


}

build_deploy_logstash() {
  echo "docker-compose -f  docker-stack-infrastructure.yml  build"
  docker-compose -f  docker-stack-infrastructure.yml  build

  echo "docker push ssriram1978/logstash:latest"
  docker push ssriram1978/logstash:latest
}

undeploy_elk() {
   echo "curl \'localhost:30011/_cat/indices?v\'"
   curl 'localhost:30011/_cat/indices?v'

   echo "curl -XDELETE 'localhost:30011/*"
   curl -XDELETE 'localhost:30011/*'

   echo "kubectl delete -f kubernetes_yaml_files/elk_components/"
   kubectl delete -f kubernetes_yaml_files/elk_components/
}

delete_logstash_index() {
   echo "curl \'localhost:30011/_cat/indices?v\'"
   curl 'localhost:30011/_cat/indices?v'

   echo "curl -XDELETE 'localhost:30011/*"
   curl -XDELETE 'localhost:30011/*'
}


deploy_infrastructure() {
   echo "kubectl apply -f kubernetes_yaml_files/common_components/"
   kubectl apply -f kubernetes_yaml_files/common_components/
}

undeploy_infrastructure() {
   echo "kubectl delete -f kubernetes_yaml_files/common_components/"
   kubectl delete -f kubernetes_yaml_files/common_components/
}

deploy_core() {
   component=$1

   if [[ "$component" == "rabbitmq" ]]; then
      echo "kubectl apply -f kubernetes_yaml_files/core_components/rabbitmq"
      kubectl apply -f kubernetes_yaml_files/core_components/rabbitmq
   elif [[ "$component" == "confluent-kafka" ]]; then
      echo "kubectl apply -f kubernetes_yaml_files/core_components/kafka/confluent"
      kubectl apply -f kubernetes_yaml_files/core_components/kafka/confluent
   elif [[ "$component" == "apache-kafka" ]]; then
      echo "kubectl apply -f kubernetes_yaml_files/core_components/kafka/apache"
      kubectl apply -f kubernetes_yaml_files/core_components/kafka/apache
   elif [[ "$component" == "emq" ]]; then
      echo "kubectl apply -f kubernetes_yaml_files/core_components/emq"
      kubectl apply -f kubernetes_yaml_files/core_components/emq
   elif [[ "$component" == "zeromq" ]]; then
      echo "kubectl apply -f kubernetes_yaml_files/core_components/zeromq"
      kubectl apply -f kubernetes_yaml_files/core_components/zeromq
   elif [[ "$component" == "nats" ]]; then
      echo "kubectl apply -f kubernetes_yaml_files/core_components/nats"
      kubectl apply -f kubernetes_yaml_files/core_components/nats
   elif [[ "$component" == "pulsar" ]]; then
      echo "kubectl apply -f kubernetes_yaml_files/core_components/pulsar"
      kubectl apply -f kubernetes_yaml_files/core_components/pulsar
   fi
}


undeploy_core() {
   component=$1
   if [[ "$component" == "rabbitmq" ]]; then
      echo "kubectl delete -f kubernetes_yaml_files/core_components/rabbitmq"
      kubectl delete -f kubernetes_yaml_files/core_components/rabbitmq
   elif [[ "$component" == "confluent-kafka" ]]; then
      echo "kubectl delete -f kubernetes_yaml_files/core_components/kafka/confluent"
      kubectl delete -f kubernetes_yaml_files/core_components/kafka/confluent
   elif [[ "$component" == "apache-kafka" ]]; then
      echo "kubectl delete -f kubernetes_yaml_files/core_components/kafka/apache"
      kubectl delete -f kubernetes_yaml_files/core_components/kafka/apache
   elif [[ "$component" == "emq" ]]; then
      echo "kubectl delete -f kubernetes_yaml_files/core_components/emq"
      kubectl delete -f kubernetes_yaml_files/core_components/emq
   elif [[ "$component" == "zeromq" ]]; then
      echo "kubectl delete -f kubernetes_yaml_files/core_components/zeromq"
      kubectl delete -f kubernetes_yaml_files/core_components/zeromq
   elif [[ "$component" == "nats" ]]; then
      echo "kubectl delete -f kubernetes_yaml_files/core_components/nats"
      kubectl delete -f kubernetes_yaml_files/core_components/nats
   elif [[ "$component" == "pulsar" ]]; then
      echo "kubectl delete -f kubernetes_yaml_files/core_components/pulsar"
      kubectl delete -f kubernetes_yaml_files/core_components/pulsar
   fi
}

bootup_vm() {

  echo "cd \$HOME/git/IOT_load_test_client/"
  cd $HOME/git/IOT_load_test_client

  echo "git checkout ."
  git checkout .

  echo "git pull"
  git pull

  echo "optimize_host"
  optimize_host

  echo "docker_prune"
  docker_prune

  #echo "deploy_cpu_ram_monitor"
  #deploy_cpu_ram_monitor

  #echo "build_logstash"
  #build_logstash

  #echo "tag_nodes"
  #tag_nodes

  #echo "deploy_infrastructure"
  #deploy_infrastructure

}

connect_to_mec() {
   echo "setting port forwarding rules for your local web browser to connect to MEC"
   echo "master:10.10.75.17"
   echo "common-infra:10.10.75.36"
   echo "publisher:10.10.75.32"
   echo "subscriber:10.10.75.6"
   echo "broker:10.10.75.14"
   echo "transformer:10.10.75.25"
   echo "elk:10.10.75.21"

   echo "ps aux | grep id_rsa_mec |  awk '{print $2}' | xargs kill -9"
   ps aux | grep id_rsa_mec |  awk '{print $2}' | xargs kill -9

   echo "kubernetes dashboard: http://localhost:30783"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 30783:10.10.75.17:30783 &

   echo "Redis: http://localhost:32622"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 32622:10.10.75.17:32622 &

   echo "EMQX broker: http://localhost:32333"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 32333:10.10.75.17:32333 &

   echo "RabbitMQ broker: http://localhost:31672"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 31672:10.10.75.17:31672 &

   echo "Confluent KAFKA broker: http://localhost:9021"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname  -NL 9021:10.10.75.14:9021 &

   echo "Kibana elk: http://localhost:30010"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 30010:10.10.75.17:30010 &

   echo "Elasticsearch elk: http://localhost:30011"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname  -NL 30011:10.10.75.17:30011 &

   echo "Logstash elk: http://localhost:30012"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 30012:10.10.75.17:30012 &

   echo "grafana elk: http://localhost:30580"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 30580:10.10.75.17:30580 &

   echo "prometheus elk: http://localhost:31905"
   ssh -i ~/.ssh/id_rsa_mec -p221 user@hostname -NL 31905:10.10.75.17:31905 &


}

deploy_prometheus_grafana() {
   echo "kubectl apply \
  --filename infrastructure_components/prometheus/manifests-all.yaml"
  kubectl apply \
  --filename infrastructure_components/prometheus/manifests-all.yaml

  #echo "ps aux | grep grafana |  awk '{print $2}' | xargs kill -9"
  #ps aux | grep grafana |  awk '{print $2}' | xargs kill -9

  #echo "kubectl port-forward --namespace monitoring service/grafana 3000:3000 &"
  #kubectl port-forward --namespace monitoring service/grafana 3000:3000 &


}

undeploy_prometheus_grafana() {
   echo "kubectl delete namespace monitoring"
   kubectl delete namespace monitoring

   #echo "ps aux | grep grafana |  awk '{print $2}' | xargs kill -9"
   #ps aux | grep grafana |  awk '{print $2}' | xargs kill -9

}


tag_nodes() {
   echo "kubectl label nodes loadtest1 vmname=loadtest1"
   kubectl label nodes loadtest1 vmname=loadtest1

   echo "kubectl label nodes loadtest2 vmname=loadtest2"
   kubectl label nodes loadtest2 vmname=loadtest2

   echo "kubectl label nodes loadtest3 vmname=loadtest3"
   kubectl label nodes loadtest3 vmname=loadtest3

   echo "kubectl label nodes loadtest4 vmname=loadtest4"
   kubectl label nodes loadtest4 vmname=loadtest4
}

change_kafka_partition() {
   topic_name=$1
   partition_count=$2

   echo "Before:"
   echo "kubectl exec kafka-0 -n common-infrastructure -it -- /bin/bash ./opt/kafka_2.11-0.10.2.1/bin/kafka-topics.sh --describe --topic $topic_name --zookeeper zookeeper.common-infrastructure.svc.cluster.local:2181"
   kubectl exec kafka-0 -n common-infrastructure -it -- /bin/bash ./opt/kafka_2.12-2.2.1/bin/kafka-topics.sh --describe --topic $topic_name --zookeeper zookeeper.common-infrastructure.svc.cluster.local:2181

   echo "kubectl exec kafka-0 -n common-infrastructure -it -- /bin/bash ./opt/kafka_2.11-0.10.2.1/bin/kafka-topics.sh --alter --partitions $partition_count  --topic $topic_name --zookeeper zookeeper.common-infrastructure.svc.cluster.local:2181"
   kubectl exec kafka-0 -n common-infrastructure -it -- /bin/bash ./opt/kafka_2.12-2.2.1/bin/kafka-topics.sh --alter --partitions $partition_count  --topic $topic_name --zookeeper zookeeper.common-infrastructure.svc.cluster.local:2181

   echo "After:"
   echo "kubectl exec kafka-0 -n common-infrastructure -it -- /bin/bash ./opt/kafka_2.11-0.10.2.1/bin/kafka-topics.sh --describe --topic $topic_name --zookeeper zookeeper.common-infrastructure.svc.cluster.local:2181"
   kubectl exec kafka-0 -n common-infrastructure -it -- /bin/bash ./opt/kafka_2.12-2.2.1/bin/kafka-topics.sh --describe --topic $topic_name --zookeeper zookeeper.common-infrastructure.svc.cluster.local:2181
}

deploy_routing_manager() {
   echo "kubectl apply -f kubernetes_yaml_files/routing_manager"
   kubectl apply -f kubernetes_yaml_files/routing_manager
}

undeploy_routing_manager() {
   echo "kubectl delete -f kubernetes_yaml_files/routing_manager"
   kubectl delete -f kubernetes_yaml_files/routing_manager
}

change_kafka_topic_partition_docker() {
  topic_name=$1
  partition_count=$2
  kafka_broker_ip=$3

  echo "Before:"
  echo "docker exec -it zookeeper usr/bin/kafka-topics --describe  --topic $topic_name --zookeeper $kafka_broker_ip "
  docker exec -it zookeeper usr/bin/kafka-topics --describe  --topic $topic_name --zookeeper $kafka_broker_ip

  echo "docker exec -it zookeeper usr/bin/kafka-topics --alter --partitions $partition_count  --topic $topic_name --zookeeper $kafka_broker_ip "
  docker exec -it zookeeper usr/bin/kafka-topics --alter --partitions $partition_count  --topic $topic_name --zookeeper $kafka_broker_ip

  echo "After:"
  echo "docker exec -it zookeeper usr/bin/kafka-topics --describe  --topic $topic_name --zookeeper $kafka_broker_ip "
  docker exec -it zookeeper usr/bin/kafka-topics --describe  --topic $topic_name --zookeeper $kafka_broker_ip

}

build_publish_go_directory() {
	directory=$1
	docker_tag=$2

	echo "docker build $directory -t $docker_tag"
	docker build $directory -t $docker_tag

	echo "docker push  $docker_tag"
	docker push  $docker_tag
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
  deploy_elk) deploy_elk ;;
  undeploy_elk) undeploy_elk ;;
  deploy_core) deploy_core $2 ;;
  undeploy_core) undeploy_core $2 ;;
  deploy_infrastructure) deploy_infrastructure ;;
  undeploy_infrastructure) undeploy_infrastructure ;;
  build_logstash) build_deploy_logstash ;;
  bootup_vm) bootup_vm ;;
  tag_nodes) tag_nodes ;;
  docker_elk) docker_compose_elk_infrastructure $2 ;;
  deploy_prometheus_grafana) deploy_prometheus_grafana ;;
  undeploy_prometheus_grafana) undeploy_prometheus_grafana ;;
  delete_logstash_index)   delete_logstash_index ;;
  change_kafka_partition) change_kafka_partition $2 $3 ;;
  deploy_routing_manager) deploy_routing_manager ;;
  undeploy_routing_manager) undeploy_routing_manager ;;
  change_kafka_topic_partition_docker) change_kafka_topic_partition_docker $2 $3 $4 ;;
  build_publish_go_directory) build_publish_go_directory $2 $3 ;;
  *) echo "usage: $0"
      echo "build <all|directory_name> <yaml file> <tag -- optional>"
      echo "deploy <yaml file>"
      echo "build_and_deploy <all|directory_name> <yaml file> <tag --optional>"
      echo "stop"
      echo "prune"
      echo "deploy_cpu_ram_monitor"
      echo "monitor start|stop"
      echo "connect_to_mec"
      echo "optimize_host"
      echo "deploy_elk"
      echo "undeploy_elk"
      echo "deploy_core <apache-kafka|confluent-kafka|rabbitmq|nats|pulsar|emq|zeromq>"
      echo "undeploy_core <apache-kafka|confluent-kafka|rabbitmq|nats|pulsar|emq|zeromq>"
      echo "deploy_infrastructure"
      echo "undeploy_infrastructure"
      echo "build_logstash"
      echo "bootup_vm"
      echo "tag_nodes"
      echo "docker_elk start|stop"
      echo "deploy_prometheus_grafana"
      echo "undeploy_prometheus_grafana"
      echo "delete_logstash_index"
      echo "change_kafka_partition <topic_name> <partition_count>"
      echo "deploy_routing_manager"
      echo "undeploy_routing_manager"
      echo "change_kafka_topic_partition_docker  <topic_name> <partition_count> <kafka_broker_ip>"
      echo "build_publish_go_directory <directory>  <docker_tag>" 
     exit 1
     ;;
esac
