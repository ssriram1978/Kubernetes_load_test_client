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

        echo "build_push_directory plotter $tag"
        build_push_directory \
        plotter \
        $tag

        echo "build_push_directory orchestrator $tag"
        build_push_directory \
        orchestrator \
        $tag

        echo "build_push_directory displayer $tag"
        build_push_directory \
        displayer \
        $tag

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

   echo "docker stack deploy --compose-file docker-stack-common.yml -c $1 load_test"
   docker stack deploy -c $1 load_test
}

teardown_infrastructure() {
   echo "docker stack rm load_test"
   docker stack rm load_test
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
}

case "$1" in
  build) create_infrastructure $2 $3 $4 ;;
  deploy) deploy_infrastructure $2 ;;
  build_and_deploy) create_deploy_infrastructure $2 $3 $4 ;;
  stop) teardown_infrastructure  ;;
  *) echo "usage: $0"
      echo "<build <all|directory_name> <yaml file> <tag -- optional> > |"
      echo "<deploy <yaml file> > |"
      echo "<build_and_deploy <all|directory_name> <yaml file> <tag --optional>> | "
      echo "stop"
     exit 1
     ;;
esac
