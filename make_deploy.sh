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

   if [ "$2" != "" ]; then
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
   tag=$2

   echo "gzip_infrastructure_components"
   gzip_infrastructure_components

   if [ "$1" == "all" ]; then
    echo "build_push_directory publisher $tag"
    build_push_directory \
      publisher \
      $tag
    echo "build_push_directory subscriber $tag"
    build_push_directory \
      subscriber \
      $tag
    echo "build_push_directory subscriber $tag"
    build_push_directory \
      plotter \
      $tag
    echo "build_push_directory subscriber $tag"
    build_push_directory \
        plotter/logstash \
        $tag
    else
      echo "build_push_directory publisher $tag"
      build_push_directory \
        $1 \
        $tag
    fi
}

deploy_infrastructure() {
   echo "docker stack deploy -c docker-compose.yml load_test"
   docker stack deploy -c docker-stack.yml load_test
}

teardown_infrastructure() {
   echo "docker stack rm load_test"
   docker stack rm load_test
}

create_deploy_infrastructure() {
   directory_name=$1
   tag=$2

   echo "create_infrastructure "
   create_infrastructure \
     $directory_name \
     $tag

   echo "deploy_infrastructure"
   deploy_infrastructure
}

case "$1" in
  build) create_infrastructure $2 $3 ;;
  deploy) deploy_infrastructure ;;
  build_and_deploy) create_deploy_infrastructure $2 $3 ;;
  stop) teardown_infrastructure ;;
  *) echo "usage: $0 <build <all|directory_name> <tag>> | <deploy> | <build_and_deploy <all|directory_name> <tag>> |stop"
     exit 1
     ;;
esac
