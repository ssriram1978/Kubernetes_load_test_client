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

   echo "docker build $directory_name -t $tag/$directory_name:latest"
   docker build $directory_name -t $tag/$directory_name:latest
   
   echo "rm -f $directory_name/infrastructure_components.tar.gz"
   rm -f $directory_name/infrastructure_components.tar.gz
  
   echo "docker push $tag/$directory_name:latest"
   docker push $tag/$directory_name:latest

}


create_infrastructure() {
   $tag =$1

   echo "gzip_infrastructure_components"
   gzip_infrastructure_components
   
   echo "build_push_directory publisher $tag"
   build_push_directory \
      publisher \
      $tag

   echo "build_push_directory subscriber $tag"
   build_push_directory \
      subscriber \
      $tag
}

deploy_infrastructure() {
   echo "docker-compose up -d"
   docker-compose up -d
}

teardown_infrastructure() {
   echo "docker-compose down"
   docker-compose down
}

create_deploy_infrastructure() {
   tag=$1

   echo "create_infrastructure "
   create_infrastructure \
     $tag
   echo "deploy_infrastructure"
   deploy_infrastructure
}

case "$1" in
  build) create_infrastructure ;;
  deploy) deploy_infrastructure $2 ;;
  build_and_deploy) create_deploy_infrastructure $2 ;;
  stop) teardown_infrastructure ;;
  *) echo "usage: $0 build|deploy <tag> |build_and_deploy <tag> |stop"
     exit 1
     ;;
esac
